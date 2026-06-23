import streamlit as st
from astroquery.jplhorizons import Horizons
from astropy.time import Time, TimeDelta
import astropy.units as u
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import plotly.express as px
import math
# 1. Setup Page Title and Introduction
mylat = 35.03
mylong = -80.72


st.set_page_config(page_title="Weddington Space Tracker", page_icon="🌌" )
st.markdown(
    """
    <style>
    div[data-baseweb="select"] > div:focus-within {
        border-color: #22c55e !important;
        box-shadow: 0 0 0 1px #22c55e !important;
    }
    div[data-baseweb="select"]:focus-within {
        border-color: #22c55e !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Weddington Space Tracker")
st.markdown("""
Welcome to the Space Tracker! This app uses real-time coordinate math to query 
**NASA's JPL Horizons system** for the exact data of celestial bodies relative to your exact location (Location is Weddington, NC by default).
""")

# 2. Define Aliases
ALIASES = {
    "Sun": "10", "Mercury": "199", "Venus": "299", "Moon": "301", 
    "Mars": "499", "Jupiter": "599", "Saturn": "699", "Uranus": "799", 
    "Neptune": "899", "Io": "501", "Europa": "502", "Ganymede": "503", "Callisto": "504",
    "Titan": "606", "Titania": "703", "Oberon": "704", "Triton": "801", "Ceres": "1;", "Pluto": "999", "Haumea": "136108",
    "Makemake": "136472", "Eris": "136199", "Sedna": "90377"
}


# 3. Create Sidebar for Controls (Replaces the terminal loops)
st.sidebar.header(" Observation Settings")
use_custom_location = st.sidebar.checkbox("Manually override coordinates?", value=False)

if use_custom_location:
    mylat = st.sidebar.number_input("Latitude", value=35.03, format="%.2f")
    mylong = st.sidebar.number_input("Longitude", value=-80.72, format="%.2f")

st.sidebar.write(f"**Location (Lat, Long):** {mylat:.2f}, {mylong:.2f}")
lat = 35.03
lon = -80.72

st.sidebar.write('')
st.sidebar.write('')

# User picks the celestial body from a dropdown menu
target_name = st.sidebar.selectbox(
    "Choose a celestial object:",
    list(ALIASES.keys())
)
obj_id = ALIASES[target_name]

show_million_miles = st.sidebar.checkbox(
    "Display distances in miles",
    value=False
)
# Fetch current UTC time automatically
current_ut = Time.now()


@st.fragment(run_every="15s")
def render_live_dashboard():
    # Fetch current UTC time automatically *inside* the fragment so it updates
    current_ut = Time.now()
    # 4. Fetch NASA Data
    try:
        obj = Horizons(id=obj_id, location={'lon': mylong, 'lat': mylat, 'elevation': 0}, epochs={current_ut.iso})
        # Extract data rows
        eph = obj.ephemerides()
        obj_real_name = target_name

            # Extract specific values
        el = float(eph['EL'])
        vmag = float(eph['V'])
        dist_sun = float(eph['r'])
        dist_earth = float(eph['delta'])
        illumination = float(eph['illumination'])
        phaseang = float(eph['alpha'])
        angwidth = float(eph['ang_width'])
        if math.isnan(angwidth):
            angwidth = str(angwidth)
            angwidth = '<0.01'

        # 5. Build the Interactive Dashboard
        st.header(f"Real-Time Data for {obj_real_name}")
        st.caption(f"Last Updated: {current_ut.iso} UTC")

            # Visual Anchor: Visibility Status Card
        if el > 0:
            st.success(f"**Visible Right Now!** It is {el:.2f}° above the horizon.")
        else:
            st.error(f"**Not Visible.** It is currently {abs(el):.2f}° below the horizon.")

            # Display Metrics cleanly in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            if show_million_miles:
                dist_sunmi = dist_sun * 92955807.3 / 1_000_000
                dist_earthmi = dist_earth * 92955807.3 / 1_000_000
                st.metric(label="Distance from Earth", value=f"{dist_earthmi:.1f} M miles")
                st.metric(label="Distance from Sun", value=f"{dist_sunmi:.1f} M miles")
            else:
                st.metric(label="Distance from Earth (AU)", value=f"{dist_earth:.2f} AU")
                st.metric(label="Distance from Sun (AU)", value=f"{dist_sun:.2f} AU")
        with col2:
            st.metric(label="Apparent Magnitude", value=f"{vmag:.2f}")
            st.metric(label="Illumination", value=f"{illumination:.1f}%")
        with col3:
            if angwidth in ['<0.01']:
                st.metric(label= "Angular Width", value="N/A")
            else:
                st.metric(label= "Angular Width", value=f"{angwidth:.2f}\"")
            st.metric(label="Phase Angle", value=f"{phaseang:.2f}°")
    except Exception as a: 
            st.warning(f"Unable to stream ephemerides. Error: {a}")


@st.cache_data(show_spinner = "Calculating...")
def opposition(show_million_miles, obj_id, target_name):
    if target_name in ["Sun", "Io", "Europa", "Ganymede", "Callisto", "Titan", "Titania", "Oberon", "Triton", "Moon", "Mercury", "Venus"]:
        return
    try:
        st.markdown("---")
        scandays = 450
        start_time = Time.now()
        stop_time = start_time + scandays * u.day
        
        # 1. COARSE SCAN (1-day steps) to find the rough neighborhood safely
        coarse_scan = Horizons(
            id=obj_id,
            location='500',
            epochs={'start': start_time.iso[:10], 'stop': stop_time.iso[:10], 'step': '1d'}
        )
        coarse_table = coarse_scan.ephemerides()
        
        # 'alpha' is solar phase angle. For outer planets, opposition minimizes phase angle near 0°.
        coarse_jd = np.array(coarse_table['datetime_jd'])
        coarse_elong = np.array(coarse_table['elong'])
        rough_idx = None
        for i in range(2, len(coarse_elong) - 2):
            if coarse_elong[i] > coarse_elong[i-1] and coarse_elong[i] > coarse_elong[i+1]: #looks for local maximum
                if coarse_elong[i] >= 178.0:
                    eval_date = Time(float(coarse_jd[i]), format='jd').datetime.replace(tzinfo=timezone.utc)
                    if (eval_date - datetime.now(timezone.utc)).total_seconds() > 0:
                        rough_idx = i
                        break
        # Fallback to closest distance check if no phase angle dip is caught
        if rough_idx is None:
            highest_idx = int(np.argmax(coarse_elong))
        # Firewall: Only accept it if it is a real opposition near 180°
            if coarse_elong[highest_idx] >= 130.0:
                rough_idx = highest_idx

        if rough_idx is not None:
    # 2. FINE ZOOM: Extract the specific Julian Date found
            center_jd = float(coarse_jd[rough_idx])
    
    # Create a high-density 48-hour window surrounding that day
            fine_start = Time(center_jd - 1.0, format='jd')
            fine_stop = Time(center_jd + 1.0, format='jd')
            
        # Rescan using 10-minute steps ('10m') for precise time resolution
            fine_scan = Horizons(
                id=obj_id, 
                location='500',
                epochs={'start': fine_start.iso, 'stop': fine_stop.iso, 'step': '10m'})
            
            fine_table = fine_scan.ephemerides()
            
            fine_elong = np.array(fine_table['elong'])
            fine_jd = np.array(fine_table['datetime_jd'])
            fine_delta = np.array(fine_table['delta'])
            exact_idx = int(np.argmax(fine_elong))
            
            # Extract high-accuracy parameters from the mathematical center
            precise_julian_date = float(fine_jd[exact_idx])
            exact_date = Time(precise_julian_date, format='jd').datetime.replace(tzinfo=timezone.utc)
            
            # Now convert the final precise timestamp directly to your local time zone
            local_date = exact_date.astimezone()
            
            # Verify the final localized date is in the future before rendering
            if (local_date - datetime.now(local_date.tzinfo)).total_seconds() > 0:
                clean_display_date = local_date.strftime("%Y-%b-%d")
                bestdistanceopp = fine_delta[exact_idx]
                
                st.header("Next Opposition")
                
                # Streamlit Layout Rendering
                cm1, cm2, cm3 = st.columns(3)
                with cm1:
                    st.metric("Opposition Date", clean_display_date)
                with cm2:
                    bestdistanceoppmi = bestdistanceopp * 92955807.3 / 1_000_000
                    if show_million_miles:
                        st.metric("Distance", f"{bestdistanceoppmi:.2f} M miles")
                    else:
                        st.metric("Distance (AU)", f"{bestdistanceopp:.2f} AU")
                with cm3:
                    st.metric("Phase Angle", f"{fine_table['alpha'][exact_idx]:.2f}°")
            else:
                st.info("The calculated opposition window has already passed.")
        else:
            st.info("Rough_idx == none")
    except Exception as e:
        st.error(f"An error calculating opposition occured. Error: {e}")


@st.cache_data(show_spinner = "Calculating...")
def infconj(show_million_miles, obj_id, target_name, mylat, mylong):
    if target_name not in ["Mercury", "Venus"]:
        return
    try:
        st.markdown("---")
        scandays = 450
        start_time = Time.now()
        stop_time = start_time + scandays * u.day
        
        # scan for target
        target_scan = Horizons(
            id=obj_id,
            location={'lon': mylong, 'lat': mylat, 'elevation': 0},
            epochs={'start': start_time.iso[:10], 'stop': stop_time.iso[:10], 'step': '1d'}
        )
        target_table = target_scan.ephemerides()

        #scan for sun
        sun_scan = Horizons(
            id=10,
            location={'lon': mylong, 'lat': mylat, 'elevation': 0},
            epochs={'start': start_time.iso[:10], 'stop': stop_time.iso[:10], 'step': '1d'}
        )

        #get all required data
        sun_table = sun_scan.ephemerides()
        target_phaseang = np.array(target_table['alpha'])
        target_ED = np.array(target_table['delta'])
        target_ra = np.array(target_table['RA'])
        target_dec = np.array(target_table['DEC'])
        sun_ra = np.array(sun_table['RA'])
        sun_dec = np.array(sun_table['DEC'])
        juliandate = np.array(target_table['datetime_jd'])
        target_ra_rad = np.radians(target_ra)
        target_dec_rad = np.radians(target_dec)
        sun_ra_rad = np.radians(sun_ra)
        sun_dec_rad = np.radians(sun_dec)

        # 2. Apply the spherical law of cosines formula
        cos_separation = (np.sin(target_dec_rad) * np.sin(sun_dec_rad) + 
                        np.cos(target_dec_rad) * np.cos(sun_dec_rad) * np.cos(target_ra_rad - sun_ra_rad))

        # 3. Clip values to exactly [-1.0, 1.0] to prevent floating-point rounding crashes in arccos
        cos_separation = np.clip(cos_separation, -1.0, 1.0)

        # 4. Convert back to degrees to get the final separation array
        apparent_angular_separation = np.degrees(np.arccos(cos_separation))

        transit_idx = None

        for j in range(1, len(apparent_angular_separation) - 1):
            if (apparent_angular_separation[j] < apparent_angular_separation[j-1] and 
                apparent_angular_separation[j] < apparent_angular_separation[j+1]):
                
                transit_date = Time(float(juliandate[j]), format='jd').datetime.replace(tzinfo=timezone.utc)
                
                if (transit_date - datetime.now(timezone.utc)).total_seconds() > 0:
                    # Change your gate constraint to 7.0 to accommodate Venus's wide tilted passes
                    if apparent_angular_separation[j] <= 7.0 and target_ED[j] < 1.0:
                        transit_idx = j
                        break

        if transit_idx is not None:
            st.header("Next Inferior Conjunction")
            transit_date = transit_date + timedelta(hours=6)
            good_display_date = transit_date.strftime("%Y-%b-%d")
            best_phaseang = target_phaseang[transit_idx]
            best_disttoearth = target_ED[transit_idx]
            
            cm1, cm2, cm3 = st.columns(3)
            with cm1:
                st.metric("Inferior Conjunction Date", good_display_date)
            with cm2:
                if show_million_miles:
                     best_disttoearthmi = best_disttoearth * 92955807.3 / 1_000_000
                     st.metric("Distance from Earth (AU)", f"{best_disttoearthmi:.2f} M miles")
                else:
                    st.metric("Distance from Earth (AU)", f"{best_disttoearth:.2f} AU")
            with cm3:
                st.metric("Phase Angle", f"{best_phaseang:.2f}°")
        else:
            st.info(f"No {target_name} inferior conjunction found in the next {scandays} days.")
    except Exception as e:
        st.error(f"A calculation error occured. Error: {e}")


@st.cache_data(show_spinner="Fetching 1-Year Distance Projection...")
def get_one_year_trajectory(obj_id):
    try:
        # Generate start date (Today) and stop date (1 Year from now)
        start_time = Time.now()
        end_time = start_time + TimeDelta(365, format='jd')
        
        # Format strings for the JPL API (YYYY-MM-DD format)
        start_str = start_time.iso.split()[0]

        end_str = end_time.iso.split()[0]
        
        # Query JPL Horizons using 1-day step intervals
        trajectory_query = Horizons(
            id=obj_id,
            location='500',  # Geocentric (Earth Center view) is ideal for pure distance
            epochs={'start': start_str, 'stop': end_str, 'step': '1d'}
        )
        
        table = trajectory_query.ephemerides()
        df = table.to_pandas()
        
        # Format the dataframe cleanly for plotting
        df['Date'] = pd.to_datetime(df['datetime_str'])
        # Extract 'delta' (Distance to Earth) and 'r' (Distance to Sun)
        df_clean = df[['Date', 'V']].copy()
        
        return {"status": "success", "data": df_clean}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 2. LAYOUT RENDERING FUNCTION ---
def display_distance_chart(obj_id, target_name):
    st.markdown("---")
    st.header(f"Apparent Magnitude Projection for {target_name}")
    
    # Trigger the cached calculation 
    result = get_one_year_trajectory(obj_id)
    
    if result["status"] == "success":
        df = result["data"].copy()
        
        # Handle unit conversion toggles cleanly based on user preference
        df['Apparent Magnitude'] = df['V']
        y_col = 'Apparent Magnitude'
        y_label = "Apparent Magnitude (V)"
            
        # Create an interactive, fluid Plotly line chart
        fig = px.line(
            df,
            x='Date',
            y=y_col,
            title=f"{target_name} Apparent Magnitude Timeline",
            labels={y_col: y_label, 'Date': 'Date of Observation'},
            color_discrete_sequence=["#FF4B4B"]  # Streamlit Red styling
        )
        
        # Configure layout styling for deep space scannability
        fig.update_layout(
            hovermode="x unified",
            dragmode=False,
            margin=dict(l=40, r=40, t=40, b=40),
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', fixedrange=True),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', fixedrange=True, autorange="reversed")
        )
        
        # Render the interactive graphic inside your app frame
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
        
    else:
        st.error(f"Could not construct trajectory projection chart. Error: {result['message']}")

def version():
    st.caption("v1.3.0", text_alignment="right")


render_live_dashboard()
opposition(show_million_miles, obj_id, target_name)
infconj(show_million_miles, obj_id, target_name, mylat, mylong)
display_distance_chart(obj_id, target_name)
version()

