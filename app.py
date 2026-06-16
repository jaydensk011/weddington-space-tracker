import streamlit as st
from astroquery.jplhorizons import Horizons
from astropy.time import Time
import astropy.units as u
# 1. Setup Page Title and Introduction
st.set_page_config(page_title="Weddington Space Tracker")

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

st.title("Weddington Night Sky Tracker")
st.markdown("""
Welcome to the Weddington Astronomy Tool! This app uses real-time coordinate math to query 
**NASA's JPL Horizons system** for the exact positions of celestial bodies relative to Union County, NC.
""")

# 2. Define Aliases
ALIASES = {
    "Sun": "10", "Mercury": "199", "Venus": "299", "Moon": "301", 
    "Mars": "499", "Jupiter": "599", "Saturn": "699", "Uranus": "799", 
    "Neptune": "899", "Pluto": "999", "Io": "501", "Europa": "502", "Ganymede": "503", "Callisto": "504",
    "Titan": "606", "Titania": "703", "Oberon": "704", "Triton": "801"
}

# 3. Create Sidebar for Controls (Replaces the terminal loops)
st.sidebar.header(" Observation Settings")
st.sidebar.write("**Location:** Weddington, NC")
lat = 35.03
lon = -80.72

# User picks the celestial body from a dropdown menu
target_name = st.sidebar.selectbox("Choose a celestial object:", list(ALIASES.keys()))
obj_id = ALIASES[target_name]

# Fetch current UTC time automatically
current_ut = Time.now()

# 4. Fetch NASA Data
try:
    obj = Horizons(id=obj_id, location={'lon': lon, 'lat': lat, 'elevation': 0}, epochs={current_ut.iso})
    
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
    ang_width = float(eph['ang_width'])


    # 5. Build the Interactive Dashboard
    st.header(f"Real-Time Data for {obj_real_name}")
    st.caption(f"Data accurate as of: {current_ut.iso} UTC")

    # Visual Anchor: Visibility Status Card
    if el > 0:
        st.success(f"**Visible Right Now!** It is {el:.2f}° above the horizon.")
    else:
        st.error(f"**Not Visible.** It is currently below the horizon ({el:.2f}°).")

    # Display Metrics cleanly in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Distance from Earth (AU)", value=f"{dist_earth:.2f} AU")
        st.metric(label="Distance from Sun (AU)", value=f"{dist_sun:.2f} AU")
    with col2:
        st.metric(label="Apparent Magnitude (Brightness)", value=f"{vmag:.2f}")
        st.metric(label="Illumination", value=f"{illumination:.1f}%")
    with col3:
        st.metric(label= "Angular Width", value=f"{ang_width:.2f}\"")
        st.metric(label="Phase Angle", value=f"{phaseang:.2f}")
    st.caption("v1.0.1", False, text_alignment="right")
except Exception:
    st.error("Could not fetch data from NASA JPL. Check your internet connection or object ID.")

