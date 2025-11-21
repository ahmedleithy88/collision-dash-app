%%writefile app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="NYC Collision Analytics", layout="wide")

# Load Data
@st.cache_data
def load_data():
    # Try loading the specific file
    path = 'cleaned_collisions_persons.csv'
    try:
        df = pd.read_csv(path)
        # Convert dates immediately for filtering
        df['CRASH DATE'] = pd.to_datetime(df['CRASH DATE'], errors='coerce')
        df['CRASH TIME'] = pd.to_datetime(df['CRASH TIME'], format='%H:%M:%S', errors='coerce')
        df['Hour'] = df['CRASH TIME'].dt.hour
        df['DayOfWeek'] = df['CRASH DATE'].dt.day_name()
        return df
    except FileNotFoundError:
        return None

df = load_data()

# --- 2. HELPER: SEARCH PARSER ---
# This function looks for keywords in the search box and updates the filters
def parse_search_query():
    query = st.session_state.search_input.lower()
    
    if not query:
        return

    # 1. Detect Boroughs
    boroughs = ['BROOKLYN', 'QUEENS', 'MANHATTAN', 'BRONX', 'STATEN ISLAND']
    for b in boroughs:
        if b.lower() in query:
            st.session_state['filter_borough'] = b

    # 2. Detect Years (simple regex-like check for 20xx)
    for word in query.split():
        if word.isdigit() and word.startswith('20') and len(word) == 4:
            st.session_state['filter_year'] = int(word)

    # 3. Detect Person Type / Injury
    if 'pedestrian' in query:
        st.session_state['filter_injury'] = 'PEDESTRIAN'
    elif 'cyclist' in query:
        st.session_state['filter_injury'] = 'CYCLIST'
    elif 'motorist' in query:
        st.session_state['filter_injury'] = 'MOTORIST'

# --- 3. SIDEBAR: SEARCH & FILTERS ---
st.sidebar.title("🔍 Crash Analysis Tool")

# Search Bar
st.sidebar.text_input(
    "Natural Language Search", 
    placeholder="e.g. 'Queens 2022 pedestrian'", 
    key="search_input", 
    on_change=parse_search_query
)

st.sidebar.markdown("---")

# FORM START: This prevents the app from reloading until button is clicked
with st.sidebar.form("filter_form"):
    st.header("Filter Options")
    
    # Default values coming from Session State (if set by search)
    default_borough = st.session_state.get('filter_borough', 'QUEENS')
    default_year = st.session_state.get('filter_year', 2021)
    
    # Dynamic Dropdowns
    if df is not None:
        # Borough Filter
        unique_boroughs = ['All'] + sorted(df['BOROUGH'].dropna().unique().tolist())
        # Handle case where default might not be in list (e.g. 'All')
        idx_b = unique_boroughs.index(default_borough) if default_borough in unique_boroughs else 0
        sel_borough = st.selectbox("Borough", unique_boroughs, index=idx_b, key='filter_borough')

        # Year Filter
        unique_years = sorted(df['YEAR'].dropna().unique().tolist())
        if default_year in unique_years:
            idx_y = unique_years.index(default_year)
        else:
            idx_y = 0
        sel_year = st.selectbox("Year", unique_years, index=idx_y, key='filter_year')

        # Vehicle Type
        top_vehicles = df['VEHICLE TYPE CODE 1'].value_counts().head(10).index.tolist()
        sel_vehicle = st.multiselect("Vehicle Type", top_vehicles, default=top_vehicles[:2])

        # Contributing Factor
        top_factors = df['CONTRIBUTING FACTOR VEHICLE 1'].value_counts().head(10).index.tolist()
        sel_factor = st.multiselect("Contributing Factor", top_factors)
        
        # Submit Button
        generate_btn = st.form_submit_button("📊 Generate Report")

# --- 4. MAIN DASHBOARD LOGIC ---
st.title("🗽 NYC Collision Insights Report")

if df is None:
    st.error("Data file not found. Please ensure 'cleaned_collisions_persons.csv' is in the Colab files.")
else:
    # Apply Filters ONLY when button is clicked or on first load
    filtered_df = df.copy()

    if sel_borough != 'All':
        filtered_df = filtered_df[filtered_df['BOROUGH'] == sel_borough]
    
    filtered_df = filtered_df[filtered_df['YEAR'] == sel_year]
    
    if sel_vehicle:
        filtered_df = filtered_df[filtered_df['VEHICLE TYPE CODE 1'].isin(sel_vehicle)]
        
    if sel_factor:
        filtered_df = filtered_df[filtered_df['CONTRIBUTING FACTOR VEHICLE 1'].isin(sel_factor)]

    # --- DISPLAY STATISTICS ---
    st.markdown(f"### Report for: **{sel_borough} ({sel_year})**")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Crashes", len(filtered_df))
    m2.metric("Persons Injured", int(filtered_df['NUMBER OF PERSONS INJURED'].sum()))
    m3.metric("Pedestrians Injured", int(filtered_df['NUMBER OF PEDESTRIANS INJURED'].sum()))
    m4.metric("Cyclists Injured", int(filtered_df['NUMBER OF CYCLIST INJURED'].sum()))

    st.markdown("---")

    # --- VISUALIZATIONS ---
    
    # ROW 1: Map & Line Chart
    row1_col1, row1_col2 = st.columns([1, 1])
    
    with row1_col1:
        st.subheader("🗺️ Crash Hotspots")
        if not filtered_df.empty:
            fig_map = px.scatter_mapbox(
                filtered_df, 
                lat="LATITUDE", lon="LONGITUDE", 
                color="NUMBER OF PERSONS INJURED",
                size="NUMBER OF PERSONS INJURED",
                color_continuous_scale=px.colors.cyclical.IceFire,
                zoom=10, height=400,
                mapbox_style="carto-positron"
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("No data for map.")

    with row1_col2:
        st.subheader("📈 Crashes Over Time (Monthly)")
        if not filtered_df.empty:
            # Resample by Month
            monthly_counts = filtered_df.set_index('CRASH DATE').resample('M').size().reset_index(name='Count')
            fig_line = px.line(monthly_counts, x='CRASH DATE', y='Count', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("No data for line chart.")

    # ROW 2: Heatmap & Pie Chart
    row2_col1, row2_col2 = st.columns([1, 1])
    
    with row2_col1:
        st.subheader("🔥 Dangerous Times (Heatmap)")
        if not filtered_df.empty:
            # Group by Day of Week and Hour
            heatmap_data = filtered_df.groupby(['DayOfWeek', 'Hour']).size().reset_index(name='Count')
            # Order days correctly
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            fig_heat = px.density_heatmap(
                heatmap_data, 
                x='Hour', 
                y='DayOfWeek', 
                z='Count', 
                nbinsx=24,
                category_orders={"DayOfWeek": days_order},
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    with row2_col2:
        st.subheader("🚗 Vehicle Type Distribution")
        if not filtered_df.empty:
            vehicle_counts = filtered_df['VEHICLE TYPE CODE 1'].value_counts().head(5).reset_index()
            vehicle_counts.columns = ['Vehicle Type', 'Count']
            fig_pie = px.pie(vehicle_counts, names='Vehicle Type', values='Count', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
