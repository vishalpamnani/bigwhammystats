import streamlit as st

from config import LEAGUE_ID
from services.awards import wildcard_wizard_table
from services.fpl_service import fetch_bootstrap_static
from utils import add_logo_fixed

st.set_page_config(page_title="Wildcard Wizard", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("🃏 Wildcard Wizard")
st.caption("Highest points scored in any gameweek where a Wildcard was used.")

bs = fetch_bootstrap_static()
events = bs.get("events", []) or []
latest_completed_gw = max((event.get("id", 0) for event in events if event.get("finished")), default=0)

if latest_completed_gw < 1:
    st.info("No completed gameweeks yet.")
    st.stop()

if latest_completed_gw < 38:
    st.info(f"Provisional standings through GW{latest_completed_gw}. Final winner is decided after GW38.")
else:
    st.success("Final standings after GW38.")

with st.spinner("Scanning Wildcard gameweeks…"):
    df = wildcard_wizard_table(LEAGUE_ID, latest_completed_gw)

if df.empty:
    st.info("No Wildcard gameweeks found yet.")
    st.stop()

top_score = int(df.iloc[0]["Points"])
top_count = int((df["Points"] == top_score).sum())
if top_count > 1:
    st.warning(f"{top_count} managers are tied for first. Prize pot is split if this remains final.")

st.dataframe(
    df[
        [
            "Position",
            "Manager",
            "Team",
            "Gameweek",
            "Points",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    """
**Rule:** Highest points in any GW where the manager used a Wildcard wins.  
**Tie Rule:** If multiple managers finish with the same winning score, the prize pot is split.
"""
)
