import streamlit as st
from astroquery.jplhorizons import Horizons
from astropy.time import Time
import astropy.units as u
import numpy as np
from datetime import datetime, timedelta
# 1. Setup Page Title and Introduction
mylat = 35.03
mylong = -80.72


st.set_page_config(page_title="Weddington Space Tracker", page_icon=":material/planet:" )
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
    "Neptune": "899", "Pluto": "999", "Io": "501", "Europa": "502", "Ganymede": "503", "Callisto": "504",
    "Titan": "606", "Titania": "703", "Oberon": "704", "Triton": "801"
}

OBJECT_DESCRIPTIONS = {
    "Sun": "Radius: 432,300 miles, Surface Temperature: 10000°F",
    "Mercury": "Radius: 1,516 miles, Surface Temperature: 332°F (Day: 800°F / Night: -290°F)",
    "Venus": "Radius: 3,760 miles, Surface Temperature: 867°F",
    "Moon": "Radius: 1,079 miles, Surface Temperature: -4°F (Day: 260°F / Night: -280°F)",
    "Mars": "Radius: 2,106 miles, Surface Temperature: -85°F",
    "Jupiter": "Radius: 43,441 miles, Surface Temperature: -166°F",
    "Saturn": "Radius: 36,184 miles, Surface Temperature: -220°F",
    "Uranus": "Radius: 15,759 miles, Surface Temperature: -320°F",
    "Neptune": "Radius: 15,299 miles, Surface Temperature: -330°F",
    "Pluto": "Radius: 738 miles, Surface Temperature: -373°F",
    "Io": "Radius: 1,131 miles, Surface Temperature: -225°F",
    "Europa": "Radius: 970 miles, Surface Temperature: -256°F",
    "Ganymede": "Radius: 1,637 miles, Surface Temperature: -261°F",
    "Callisto": "Radius: 1,498 miles, Surface Temperature: -218°F",
    "Titan": "Radius: 1,600 miles, Surface Temperature: -290°F",
    "Titania": "Radius: 490 miles, Surface Temperature: -333°F",
    "Oberon": "Radius: 473 miles, Surface Temperature: -333°F",
    "Triton": "Radius: 841 miles, Surface Temperature: -391°F"
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
        ang_width = float(eph['ang_width'])

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
            st.metric(label= "Angular Width", value=f"{ang_width:.2f}\"")
            st.metric(label="Phase Angle", value=f"{phaseang:.2f}")
    
        if target_name != "Sun":
            st.markdown("---")
            st.subheader("Next Opposition Countdown")
            try:
                # 1. Ask JPL for a daily table of the object over the next 365 days
                future_scan = Horizons(
                    id=obj_id, 
                    location={'lon': mylong, 'lat': mylat, 'elevation': 0}, 
                    epochs={
                        'start': current_ut.iso[:10], 
                        'stop': (Time.now() + 450*u.day).iso[:10], 
                        'step': '1d'
                    }
                )
                scan_table = future_scan.ephemerides()
                    
                # 2. Extract Phase Angle (alpha). An eclipse happens when phase angle hits ~0
                earthdistance = list(scan_table['delta'])
                dates_list = list(scan_table['datetime_str'])
                    
                # Find the day where the angle is closest to absolute zero alignment
                min_angle_index = earthdistance.index(min(earthdistance))
                raw_julian_date = float(scan_table['datetime_jd'][min_angle_index])
                # 3. Process the live countdown clock
                eclipse_date = Time(raw_julian_date, format='jd').to_datetime()
                time_remaining = eclipse_date - datetime.utcnow()
                dist_oppau = min(earthdistance)
                if time_remaining.total_seconds() > 0:
                    days = time_remaining.days
                    hours, remainder = divmod(time_remaining.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                        
                    clean_display_date = eclipse_date.strftime("%Y-%b-%d")


                    # 4. Display the direct metric cards
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Countdown", f"{days}d {hours}h")
                    c2.metric("Opposition Date", clean_display_date)
                    if show_million_miles:
                        dist_oppmi = dist_oppau * 92955807.3 / 1_000_000
                        c3.metric("Minimum Distance", f"{dist_oppmi:.1f} M miles")
                    else:
                        c3.metric("Minimum Distance (AU)", f"{dist_oppau:.2f} AU")
                    st.caption("An opposition is the point at which the object is closest to the Earth.")
                else:
                    st.info("Calculating alignment window...")
            except Exception as a:
                    st.warning(f"Unable to stream ephemerides. Error: {a}")
            
        if target_name != "Sun":  
            try:
                st.markdown("---")
                st.subheader("Next Conjunction Countdown")
                # Find the day where the angle is closest to absolute zero alignment
                max_angle_index = earthdistance.index(max(earthdistance))
                raw_julian_date = float(scan_table['datetime_jd'][max_angle_index])
                # 3. Process the live countdown clock
                eclipse_date = Time(raw_julian_date, format='jd').to_datetime()
                time_remaining = eclipse_date - datetime.utcnow()
                dist_conjau = max(earthdistance)
                if time_remaining.total_seconds() > 0:
                    days = time_remaining.days
                    hours, remainder = divmod(time_remaining.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                        
                    clean_display_date = eclipse_date.strftime("%Y-%b-%d")


                    # 4. Display the direct metric cards
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Countdown", f"{days}d {hours}h")
                    c2.metric("Conjunction Date", clean_display_date)
                    if show_million_miles:
                        dist_conjmi = dist_conjau * 92955807.3 / 1_000_000
                        c3.metric("Maximum Distance", f"{dist_conjmi:.1f} M miles")
                    else:
                        c3.metric("Maximum Distance (AU)", f"{dist_conjau:.2f} AU")
                    st.caption("A conjunction is the point at which the object is farthest from the Earth.")
                else:
                    st.info("Calculating alignment window...")
                            
            except Exception as a:
                st.warning(f"Unable to stream ephemerides. Error: {a}")
        else:
            pass



        object_desc = OBJECT_DESCRIPTIONS.get(target_name, "Physical data unavailable.")
        st.markdown(f"**Physical Profile:** {object_desc}")
        st.caption("v1.2.0", False, text_alignment="right")
        st.markdown("""
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        </style>
        """, unsafe_allow_html=True)
    except Exception as e:
            st.error(f"Could not fetch data from NASA JPL. Error detail: {e}")

render_live_dashboard()

