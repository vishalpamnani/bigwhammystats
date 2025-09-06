# pages/awards.py  (replace your managers-fetch with this)
import streamlit as st
import pandas as pd
import requests

from services.fpl_service import fetch_all_league_standings, fetch_entry_event_picks, compute_net_points
from utils import add_logo_fixed

st.set_page_config(page_title="Awards", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151  # <-- your league ID

st.title("🏆 Gameweek Standings")

gw = st.selectbox("Select Gameweek", list(range(1, 39)), index=0)

with st.spinner("Loading managers…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

rows = []
with st.spinner(f"Fetching Gameweek {gw} points…"):
    for m in standings:
        entry_id = m["entry"]
        picks = fetch_entry_event_picks(entry_id, gw)
        pts = compute_net_points(picks)  # returns dict

        rows.append({
            "Manager": m["player_name"],
            "Team": m["entry_name"],
            "GW Points": pts["net_points"],   # ✅ correct numeric value
            "Total Points": m["total"],
})


df = pd.DataFrame(rows).sort_values(by=["GW Points", "Total Points"], ascending=[False, False]).reset_index(drop=True)
df.index = df.index + 1
df.index.name = "Rank"

def medal(i): return "🥇" if i==1 else ("🥈" if i==2 else ("🥉" if i==3 else ""))
df.insert(0, "Medal", [medal(i) for i in df.index])

st.dataframe(df[["Medal", "Manager", "Team", "GW Points"]], width='stretch')
