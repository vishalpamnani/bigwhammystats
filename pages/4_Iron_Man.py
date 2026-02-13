# pages/4_Iron_Man.py
import streamlit as st
import pandas as pd

from services.fpl_service import (
    fetch_all_league_standings,
    fetch_entry_event_picks,
    compute_net_points,
    fetch_bootstrap_static,
)
from utils import add_logo_fixed

LEAGUE_ID = 1124151
GW_START = 19  # Iron Man starts AFTER GW19

st.set_page_config(page_title="Iron Man Award", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("💪 Iron Man Award")
st.caption("Biggest rank climber in the Big Whammy table (GW19 → Current)")

# --------------------------------------------------
# Get latest completed GW
# --------------------------------------------------
bs = fetch_bootstrap_static()
events = bs.get("events", [])
latest_gw = max(e["id"] for e in events if e["finished"])

if latest_gw < GW_START:
    st.warning("Iron Man race begins after Gameweek 19.")
    st.stop()

# --------------------------------------------------
# Fetch league managers
# --------------------------------------------------
with st.spinner("Loading league managers…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

entries = [m["entry"] for m in standings]
base_order = {entry: i for i, entry in enumerate(entries)}

entry_meta = {m["entry"]: m for m in standings}

# --------------------------------------------------
# Helper: build BW leaderboard up to a GW
# --------------------------------------------------
@st.cache_data(ttl=600)
def build_bw_leaderboard_upto_gw(entries, upto_gw):
    totals = {e: 0 for e in entries}

    for gw in range(1, upto_gw + 1):
        for entry in entries:
            picks = fetch_entry_event_picks(entry, gw)
            pts = compute_net_points(picks)
            totals[entry] += pts["net_points"]

    df = pd.DataFrame([
    {
        "entry": e,
        "TotalPoints": totals[e],
        "BaseOrder": base_order[e],   # ← tie-breaker
    }
    for e in entries
])

# ⭐ CRITICAL FIX — stable FPL sorting
    df = df.sort_values(
    ["TotalPoints", "BaseOrder"],
    ascending=[False, True]
).reset_index(drop=True)

    df["Rank"] = df.index + 1

    return dict(zip(df["entry"], df["Rank"]))

# --------------------------------------------------
# Build BOTH snapshots
# --------------------------------------------------
with st.spinner("Building BW rankings after GW19…"):
    rank_after_gw19 = build_bw_leaderboard_upto_gw(entries, GW_START)

with st.spinner("Building current BW rankings…"):
    rank_current = build_bw_leaderboard_upto_gw(entries, latest_gw)

# --------------------------------------------------
# Build Iron Man leaderboard
# --------------------------------------------------
rows = []
for entry in entries:
    start_rank = rank_after_gw19.get(entry)
    current_rank = rank_current.get(entry)

    if not start_rank or not current_rank:
        continue

    gain = start_rank - current_rank

    meta = entry_meta[entry]

    rows.append({
        "Manager": meta["player_name"],
        "Team": meta["entry_name"],
        "Rank After GW19": start_rank,
        "Current Rank": current_rank,
        "Rank Gain": gain,
    })

df = pd.DataFrame(rows).sort_values("Rank Gain", ascending=False).reset_index(drop=True)

# --------------------------------------------------
# Position handling (ties share prize)
# --------------------------------------------------
positions = []
current_pos = 1

for i, row in df.iterrows():
    if i == 0:
        positions.append(1)
        continue

    if row["Rank Gain"] == df.loc[i-1, "Rank Gain"]:
        positions.append(current_pos)
    else:
        current_pos = i + 1
        positions.append(current_pos)

df.insert(0, "Position", positions)

def medal(pos):
    if pos == 1: return "🥇"
    if pos == 2: return "🥈"
    return ""

df.insert(1, "", df["Position"].apply(medal))

# --------------------------------------------------
# UI
# --------------------------------------------------
st.dataframe(
    df[[
        "Position",
        "",
        "Manager",
        "Team",
        "Rank After GW19",
        "Current Rank",
        "Rank Gain",
    ]],
    width="stretch",
    hide_index=True
)

st.markdown(
    """
**Tie Rule:**  
If multiple managers finish 1st or 2nd, the prize money is shared.
"""
)
