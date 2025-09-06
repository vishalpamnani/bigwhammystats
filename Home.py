import streamlit as st
import pandas as pd
from services.fpl_service import fetch_all_league_standings
from utils import add_logo_fixed

st.set_page_config(page_title="Big Whammy - Home", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151

st.title("🏡 Welcome to The Big Whammy!")

# Intro text
st.markdown("""  
Track your weekly awards 🏆, eliminations ❌, and overall table 📊 all in one place.
""")

# League summary
with st.spinner("Fetching league summary…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

st.subheader("📊 League Summary")
st.write(f"**Total Managers:** {len(standings)}")
st.write(f"**Current Leader:** {standings[0]['player_name']} ({standings[0]['entry_name']})")
st.write(f"**Leader Points:** {standings[0]['total']}")

# Navigation buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏅 Gameweek Slammers"):
        st.switch_page("pages/2_Gameweek_Slammers.py")
with col2:
    if st.button("📊 Standings"):
        st.switch_page("pages/1_Big_Whammy_Table.py")
with col3:
    if st.button("💀 Last Person Standing"):
        st.switch_page("pages/3_Last_Person_Standing.py")
