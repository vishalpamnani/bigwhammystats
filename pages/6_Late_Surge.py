import streamlit as st

from config import LEAGUE_ID
from services.awards import LATE_SURGE_GWS, late_surge_table
from services.fpl_service import fetch_bootstrap_static
from utils import add_logo_fixed

st.set_page_config(page_title="Late Surge Award", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("🚀 Late Surge Award")
st.caption("Biggest combined net-points haul across GW34-GW38.")

bs = fetch_bootstrap_static()
events = bs.get("events", []) or []
latest_completed_gw = max((event.get("id", 0) for event in events if event.get("finished")), default=0)
completed_late_gws = [gw for gw in LATE_SURGE_GWS if gw <= latest_completed_gw]

if not completed_late_gws:
    st.info("Late Surge starts from GW34.")
    st.stop()

if latest_completed_gw < 38:
    st.info(
        f"Provisional standings using completed late-surge gameweeks: "
        f"{', '.join(f'GW{gw}' for gw in completed_late_gws)}."
    )
else:
    st.success("Final standings after GW38.")

with st.spinner("Calculating Late Surge standings…"):
    df = late_surge_table(LEAGUE_ID, latest_completed_gw)

if df.empty:
    st.info("No Late Surge data available yet.")
    st.stop()

top = df.iloc[0]
tied_after_tiebreak = df[
    (df["Total Points"] == top["Total Points"])
    & (df["Highest Single GW"] == top["Highest Single GW"])
]
if len(tied_after_tiebreak) > 1:
    st.warning(f"{len(tied_after_tiebreak)} managers are still tied after the tie-breaker. Prize pot is split.")

columns = [
    "Position",
    "Manager",
    "Team",
    "Total Points",
    "Highest Single GW",
    *[f"GW{gw}" for gw in LATE_SURGE_GWS],
]

st.dataframe(
    df[columns],
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    """
**Rule:** Highest combined net points from GW34 to GW38 wins.  
**Tie-breaker:** Highest single GW net score within GW34-GW38 wins.  
**If still tied:** Prize pot is split.
"""
)
