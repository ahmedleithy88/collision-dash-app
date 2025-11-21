import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

# ======================
# Load data
# ======================
df = pd.read_csv("cleaned_collisions_persons.csv", parse_dates=["CRASH_DATETIME"])

# ======================
# Vehicle category cleaner
# ======================
def normalize_vehicle(v):
    if pd.isna(v):
        return "UNKNOWN"
    s = str(v).upper()

    # Ambulance variants
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
    if (
        "SEDAN" in s
        or "4 DOOR" in s
        or "4-DOOR" in s
        or "2 DOOR" in s
        or "2-DOOR" in s
    ):
        return "CAR"

    return "OTHER"

# Clean data
df["VEHICLE_CATEGORY"] = df["VEHICLE TYPE CODE 1"].apply(normalize_vehicle)

# Dropdown options
borough_options = [{"label": b.title(), "value": b} for b in sorted(df["BOROUGH"].dropna().unique())]
year_options = [{"label": str(int(y)), "value": int(y)} for y in sorted(df["YEAR"].dropna().unique())]
vehicle_options = [{"label": v, "value": v} for v in sorted(df["VEHICLE_CATEGORY"].dropna().unique())]
factor_options = [{"label": f.title(), "value": f} for f in sorted(df["CONTRIBUTING FACTOR VEHICLE 1"].dropna().unique())]
injury_type_options = [{"label": i.title(), "value": i} for i in sorted(df["INJURY_TYPE"].dropna().unique())]

# ======================
# Build Dash app
# ======================
app = Dash(__name__)
server = app.server     # <-- VERY IMPORTANT FOR DEPLOYMENT

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "20px"},
    children=[
        html.H1("NYC Motor Vehicle Collisions – Interactive Dashboard"),

        html.Div(
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
            children=[
                dcc.Dropdown(id="filter-borough", options=borough_options, placeholder="Select Borough", multi=True, style={"width": "200px"}),
                dcc.Dropdown(id="filter-year", options=year_options, placeholder="Select Year", multi=True, style={"width": "150px"}),
                dcc.Dropdown(id="filter-vehicle", options=vehicle_options, placeholder="Vehicle Type", multi=True, style={"width": "200px"}),
                dcc.Dropdown(id="filter-factor", options=factor_options, placeholder="Contributing Factor", multi=True, style={"width": "250px"}),
                dcc.Dropdown(id="filter-injury", options=injury_type_options, placeholder="Injury Type", multi=True, style={"width": "220px"}),
            ],
        ),

        html.Br(),

        html.Div(
            style={"display": "flex", "gap": "10px"},
            children=[
                dcc.Input(id="search-box", type="text", placeholder="Search (e.g. 'Brooklyn 2022 pedestrian crashes')", style={"width": "400px"}),
                html.Button("Generate Report", id="btn-generate", n_clicks=0, style={"padding": "10px 20px", "fontWeight": "bold"}),
            ],
        ),

        html.Br(),
        html.Div(id="results-area")
    ],
)

# ======================
# Callbacks
# ======================
@app.callback(
    Output("results-area", "children"),
    Input("btn-generate", "n_clicks"),
    State("filter-borough", "value"),
    State("filter-year", "value"),
    State("filter-vehicle", "value"),
    State("filter-factor", "value"),
    State("filter-injury", "value"),
    State("search-box", "value"),
)
def generate_report(n, boroughs, years, vehicles, factors, injuries, search):
    if n == 0:
        return ""

    d = df.copy()

    if boroughs:
        d = d[d["BOROUGH"].isin(boroughs)]
    if years:
        d = d[d["YEAR"].isin(years)]
    if vehicles:
        d = d[d["VEHICLE_CATEGORY"].isin(vehicles)]
    if factors:
        d = d[d["CONTRIBUTING FACTOR VEHICLE 1"].isin(factors)]
    if injuries:
        d = d[d["INJURY_TYPE"].isin(injuries)]

    # If search used:
    if search and len(search.strip()) > 0:
        s = search.lower()
        d = d[
            d["BOROUGH"].str.lower().str.contains(s)
            | d["VEHICLE_CATEGORY"].str.lower().str.contains(s)
            | d["CONTRIBUTING FACTOR VEHICLE 1"].str.lower().str.contains(s)
            | d["INJURY_TYPE"].str.lower().str.contains(s)
        ]

    if d.empty:
        return html.H3("No results match your filters.", style={"color": "red"})

    fig = px.histogram(
        d,
        x="CRASH_DATETIME",
        nbins=40,
        title="Collisions Over Time",
    )

    return html.Div([
        html.H3(f"Found {len(d)} collisions matching criteria."),
        dcc.Graph(figure=fig),
    ])


# ======================
# Main entry point (Railway)
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
