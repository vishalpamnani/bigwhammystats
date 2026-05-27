import pandas as pd
import streamlit as st

from config import LEAGUE_ID
from services.awards import knockout_cup_rows
from services.fpl_service import fetch_league_cup_status
from utils import add_logo_fixed

st.set_page_config(page_title="Knockout Cup", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("🏆 Knockout Cup")
st.caption("Mirrors the official FPL Knockout Cup results for The Big Whammy.")

cup_status = fetch_league_cup_status(LEAGUE_ID)
cup_name = cup_status.get("name", "The Big Whammy Cup")
cup_league_id = cup_status.get("league")

st.write(f"**Cup:** {cup_name}")
if cup_league_id:
    st.write(f"**Official FPL Cup League ID:** {cup_league_id}")

with st.spinner("Loading official FPL cup results…"):
    rows = knockout_cup_rows(LEAGUE_ID)

if not rows:
    st.info("Knockout Cup results are not available yet from FPL.")
    st.stop()

df = pd.DataFrame(rows)

st.dataframe(
    df[["Award", "Manager", "Team", "Gameweek", "Points"]],
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    """
**Rule:** Results are pulled directly from the official FPL Knockout Cup.  
**Second and Third Runner-up:** Losing semi-finalists are ranked by their semi-final points.
"""
)

# redeploy trigger