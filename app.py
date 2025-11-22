import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
import logging

# ======================
# Configuration & Logging
# ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================
# Initialize Dash App FIRST
# ======================
app = Dash(__name__)
server = app.server  # CRITICAL FOR DEPLOYMENT

logger.info("Dash app initialized")

# ======================
# Data Loading with Error Handling
# ======================
def load_data():
    """Load and prepare data with comprehensive error handling"""
    try:
        logger.info("Attempting to load CSV file...")
        
        # Try multiple possible file paths
        csv_paths = [
            "cleaned_collisions_persons.csv",
            "./cleaned_collisions_persons.csv",
            "/etc/secrets/cleaned_collisions_persons.csv"
        ]
        
        df = None
        for path in csv_paths:
            try:
                df = pd.read_csv(path, parse_dates=["CRASH_DATETIME"], low_memory=False)
                logger.info(f"Successfully loaded data from {path}: {len(df)} rows")
                break
            except FileNotFoundError:
                logger.warning(f"File not found at {path}, trying next...")
                continue
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                continue
        
        if df is None:
            logger.error("Could not load CSV from any path. Creating empty dataset.")
            return pd.DataFrame()
        
        # Validate required columns
        required_columns = ['BOROUGH', 'YEAR', 'VEHICLE TYPE CODE 1', 'CONTRIBUTING FACTOR VEHICLE 1', 'INJURY_TYPE']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
        
        return df
        
    except Exception as e:
        logger.error(f"Critical error in load_data: {e}")
        return pd.DataFrame()

# Load the data
df = load_data()
logger.info(f"Data preparation complete. Dataset shape: {df.shape}")

# ======================
# Vehicle Category Cleaner
# ======================
def normalize_vehicle(v):
    """Normalize vehicle types with error handling"""
    try:
        if pd.isna(v):
            return "UNKNOWN"
        
        s = str(v).upper()

        # Vehicle type mapping
        if "AMB" in s or "AMBUL" in s:
            return "AMBULANCE"
        if "TAXI" in s:
            return "TAXI"
        if "BUS" in s:
            return "BUS"
        if "MOTORCYCLE" in s or "SCOOTER" in s or "MOTORBIKE" in s:
            return "MOTORCYCLE"
        if "BICYCLE" in s or "BIKE" in s:
            return "BICYCLE"
        if "SUV" in s or "STATION WAGON" in s:
            return "SUV"
        if "PICK" in s or "PICK-UP" in s or "PICKUP" in s:
            return "TRUCK/VAN"
        if "TRUCK" in s or "VAN" in s:
            return "TRUCK/VAN"
        if "SEDAN" in s or "4 DOOR" in s or "4-DOOR" in s or "2 DOOR" in s or "2-DOOR" in s:
            return "CAR"

        return "OTHER"
    except Exception as e:
        logger.warning(f"Error normalizing vehicle '{v}': {e}")
        return "UNKNOWN"

# Apply vehicle categorization safely
if not df.empty and 'VEHICLE TYPE CODE 1' in df.columns:
    df["VEHICLE_CATEGORY"] = df["VEHICLE TYPE CODE 1"].apply(normalize_vehicle)
    logger.info("Vehicle categorization applied")
else:
    df["VEHICLE_CATEGORY"] = "UNKNOWN"
    logger.warning("Vehicle categorization skipped - missing required column")

# ======================
# Dropdown Options with Fallbacks
# ======================
def get_dropdown_options(column, default_label="All"):
    """Safely generate dropdown options with fallbacks"""
    try:
        if df.empty or column not in df.columns:
            return [{"label": default_label, "value": "ALL"}]
        
        unique_values = df[column].dropna().unique()
        if len(unique_values) == 0:
            return [{"label": default_label, "value": "ALL"}]
            
        return [{"label": str(val).title(), "value": val} for val in sorted(unique_values)]
    except Exception as e:
        logger.error(f"Error generating options for {column}: {e}")
        return [{"label": default_label, "value": "ALL"}]

# Generate dropdown options
borough_options = get_dropdown_options("BOROUGH", "Select Borough")
year_options = get_dropdown_options("YEAR", "Select Year") 
vehicle_options = get_dropdown_options("VEHICLE_CATEGORY", "Vehicle Type")
factor_options = get_dropdown_options("CONTRIBUTING FACTOR VEHICLE 1", "Contributing Factor")
injury_type_options = get_dropdown_options("INJURY_TYPE", "Injury Type")

logger.info("Dropdown options generated")

# ======================
# App Layout
# ======================
app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "20px", "backgroundColor": "#f5f5f5", "minHeight": "100vh"},
    children=[
        html.Div(
            style={"backgroundColor": "white", "padding": "30px", "borderRadius": "10px", "boxShadow": "0 2px 10px rgba(0,0,0,0.1)"},
            children=[
                html.H1(
                    "NYC Motor Vehicle Collisions – Interactive Dashboard",
                    style={"textAlign": "center", "color": "#2c3e50", "marginBottom": "30px"}
                ),
                
                # Filters Section
                html.Div([
                    html.H3("Filter Data", style={"marginBottom": "15px", "color": "#34495e"}),
                    
                    # Filters Row
                    html.Div(
                        style={"display": "flex", "gap": "15px", "flexWrap": "wrap", "marginBottom": "20px"},
                        children=[
                            dcc.Dropdown(
                                id="filter-borough",
                                options=borough_options,
                                placeholder="Select Borough",
                                multi=True,
                                style={"minWidth": "200px"},
                            ),
                            dcc.Dropdown(
                                id="filter-year",
                                options=year_options,
                                placeholder="Select Year", 
                                multi=True,
                                style={"minWidth": "150px"},
                            ),
                            dcc.Dropdown(
                                id="filter-vehicle",
                                options=vehicle_options,
                                placeholder="Vehicle Type",
                                multi=True,
                                style={"minWidth": "200px"},
                            ),
                            dcc.Dropdown(
                                id="filter-factor", 
                                options=factor_options,
                                placeholder="Contributing Factor",
                                multi=True,
                                style={"minWidth": "250px"},
                            ),
                            dcc.Dropdown(
                                id="filter-injury",
                                options=injury_type_options,
                                placeholder="Injury Type",
                                multi=True, 
                                style={"minWidth": "220px"},
                            ),
                        ],
                    ),
                    
                    # Search Section
                    html.Div(
                        style={"display": "flex", "gap": "15px", "alignItems": "center", "marginBottom": "25px"},
                        children=[
                            dcc.Input(
                                id="search-box",
                                type="text",
                                placeholder="Try: 'Brooklyn 2022 pedestrian crashes' or 'Queens bicycle'",
                                style={"flex": "1", "padding": "12px", "border": "2px solid #ddd", "borderRadius": "5px"},
                            ),
                            html.Button(
                                "Generate Report",
                                id="btn-generate",
                                n_clicks=0,
                                style={
                                    "padding": "12px 30px", 
                                    "fontWeight": "bold", 
                                    "backgroundColor": "#3498db", 
                                    "color": "white", 
                                    "border": "none", 
                                    "borderRadius": "5px",
                                    "cursor": "pointer"
                                },
                            ),
                        ],
                    ),
                ]),
                
                # Visualizations Section
                html.Div([
                    html.H3("Crash Analysis", style={"marginBottom": "20px", "color": "#34495e"}),
                    
                    dcc.Graph(id="graph-bar-borough", style={"marginBottom": "30px"}),
                    dcc.Graph(id="graph-line-time", style={"marginBottom": "30px"}),
                    dcc.Graph(id="graph-map", style={"marginBottom": "30px"}),
                ]),
                
                # Data Status
                html.Div(
                    id="data-status",
                    style={"marginTop": "20px", "padding": "10px", "backgroundColor": "#ecf0f1", "borderRadius": "5px", "textAlign": "center"},
                    children=[f"Dataset loaded: {len(df)} records" if not df.empty else "No data available - using demo mode"]
                ),
            ]
        )
    ]
)

logger.info("App layout created")

# ======================
# Search Text Logic
# ======================
BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]

def apply_search_text(df_in, text):
    """Apply search text filters safely"""
    try:
        if not text or df_in.empty:
            return df_in, None, None, None

        text_u = text.upper()

        # Find borough
        borough_from_text = next((b for b in BOROUGHS if b in text_u), None)

        # Year extraction
        year_from_text = None
        for token in text_u.split():
            if token.isdigit() and len(token) == 4:
                y = int(token)
                if 2012 <= y <= 2030:
                    year_from_text = y
                    break

        # Injury type
        injury_from_text = None
        if "PEDESTRIAN" in text_u:
            injury_from_text = "PEDESTRIAN"
        elif "CYCLIST" in text_u or "BICYCLE" in text_u:
            injury_from_text = "CYCLIST" 
        elif "MOTORIST" in text_u or "DRIVER" in text_u:
            injury_from_text = "MOTORIST"

        df_out = df_in.copy()
        if borough_from_text and 'BOROUGH' in df_out.columns:
            df_out = df_out[df_out["BOROUGH"] == borough_from_text]
        if year_from_text and 'YEAR' in df_out.columns:
            df_out = df_out[df_out["YEAR"] == year_from_text]
        if injury_from_text and 'INJURY_TYPE' in df_out.columns:
            df_out = df_out[df_out["INJURY_TYPE"] == injury_from_text]

        return df_out, borough_from_text, year_from_text, injury_from_text
        
    except Exception as e:
        logger.error(f"Error in apply_search_text: {e}")
        return df_in, None, None, None

# ======================
# Main Callback with Comprehensive Error Handling
# ======================
@app.callback(
    [
        Output("graph-bar-borough", "figure"),
        Output("graph-line-time", "figure"), 
        Output("graph-map", "figure"),
    ],
    Input("btn-generate", "n_clicks"),
    [
        State("filter-borough", "value"),
        State("filter-year", "value"),
        State("filter-vehicle", "value"),
        State("filter-factor", "value"),
        State("filter-injury", "value"),
        State("search-box", "value"),
    ],
)
def update_report(n_clicks, boroughs, years, vehicles, factors, injuries, search_text):
    """Main callback to update all visualizations"""
    try:
        logger.info(f"Callback triggered - n_clicks: {n_clicks}")
        
        # Start with original data
        dff = df.copy()
        
        if dff.empty:
            logger.warning("No data available - returning empty figures")
            empty_fig = create_empty_figure("No data available")
            return empty_fig, empty_fig, empty_fig

        # Apply dropdown filters safely
        filter_operations = [
            ('BOROUGH', boroughs),
            ('YEAR', years), 
            ('VEHICLE_CATEGORY', vehicles),
            ('CONTRIBUTING FACTOR VEHICLE 1', factors),
            ('INJURY_TYPE', injuries)
        ]
        
        for column, values in filter_operations:
            if values and column in dff.columns:
                dff = dff[dff[column].isin(values)]
                logger.info(f"Applied {column} filter: {len(dff)} records remaining")

        # Apply search text
        dff, _, _, _ = apply_search_text(dff, search_text)

        # Handle empty results
        if dff.empty:
            logger.info("No data matches filters")
            empty_fig = create_empty_figure("No data matches your filters")
            return empty_fig, empty_fig, empty_fig

        logger.info(f"Data after filtering: {len(dff)} records")

        # Create visualizations
        fig_bar = create_bar_chart(dff)
        fig_line = create_line_chart(dff) 
        fig_map = create_map(dff)

        logger.info("All visualizations created successfully")
        return fig_bar, fig_line, fig_map

    except Exception as e:
        logger.error(f"Error in update_report callback: {e}")
        error_fig = create_empty_figure("Error generating report")
        return error_fig, error_fig, error_fig

# ======================
# Visualization Functions
# ======================
def create_empty_figure(message="No data available"):
    """Create a consistent empty figure"""
    return px.scatter(title=message).update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        annotations=[dict(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)]
    )

def create_bar_chart(dff):
    """Create borough bar chart"""
    try:
        if dff.empty or 'BOROUGH' not in dff.columns:
            return create_empty_figure("No borough data available")
            
        bar_df = dff.groupby("BOROUGH").size().reset_index(name="crash_count")
        bar_df = bar_df.sort_values("crash_count", ascending=False)
        
        fig = px.bar(
            bar_df,
            x="BOROUGH",
            y="crash_count",
            title="Crashes by Borough",
            color="crash_count",
            color_continuous_scale="blues"
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis_title="Borough",
            yaxis_title="Number of Crashes"
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating bar chart: {e}")
        return create_empty_figure("Error creating bar chart")

def create_line_chart(dff):
    """Create time series line chart"""
    try:
        if dff.empty or 'YEAR' not in dff.columns:
            return create_empty_figure("No year data available")
            
        time_df = dff.groupby("YEAR").size().reset_index(name="crash_count")
        time_df = time_df.sort_values("YEAR")
        
        fig = px.line(
            time_df,
            x="YEAR",
            y="crash_count",
            markers=True,
            title="Crashes Over Time",
            line_shape="linear"
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis_title="Year",
            yaxis_title="Number of Crashes"
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating line chart: {e}")
        return create_empty_figure("Error creating line chart")

def create_map(dff):
    """Create crash location map"""
    try:
        if dff.empty or 'LATITUDE' not in dff.columns or 'LONGITUDE' not in dff.columns:
            return create_empty_figure("No location data available")
            
        map_df = dff.dropna(subset=["LATITUDE", "LONGITUDE"])
        if map_df.empty:
            return create_empty_figure("No valid location data")
            
        # Sample data for performance
        map_sample = map_df.sample(min(5000, len(map_df)), random_state=42)
        
        fig = px.density_mapbox(
            map_sample,
            lat="LATITUDE",
            lon="LONGITUDE",
            radius=10,
            center={"lat": 40.7128, "lon": -74.0060},
            zoom=9,
            height=500,
            hover_data={
                "BOROUGH": True,
                "CRASH_DATETIME": True,
                "INJURY_TYPE": True,
            },
            title="Crash Density Heatmap",
            color_continuous_scale="hot"
        )
        fig.update_layout(mapbox_style="open-street-map")
        return fig
        
    except Exception as e:
        logger.error(f"Error creating map: {e}")
        return create_empty_figure("Error creating map")

# ======================
# Deployment Configuration
# ======================
