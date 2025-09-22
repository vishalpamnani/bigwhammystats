# pages/2_Gameweek_Slammers.py
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

from services.fpl_service import (
    fetch_all_league_standings,
    fetch_entry_event_picks,
    compute_net_points,
    fetch_bootstrap_static,
)
from utils import add_logo_fixed

st.set_page_config(page_title="Gameweek Slammers", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151  # <-- your league ID

st.title("🏆 Gameweek Slammers")

# Gameweek selector
gw = st.selectbox("Select Gameweek", list(range(1, 39)), index=0)

# Determine latest completed GW via bootstrap-static
latest_completed_gw = 0
try:
    bs = fetch_bootstrap_static()
    events = bs.get("events", []) or []
    latest_completed_gw = max((e.get("id", 0) for e in events if e.get("finished")), default=0)
except Exception:
    # If bootstrap fails, assume no GWs completed (defensive)
    latest_completed_gw = 0

# If selected GW is in the future, show fun message and skip fetching
if gw > latest_completed_gw:
    st.header(f"Gameweek {gw} — not yet completed")
    st.markdown(
        """
        🚫 Hold on!! You can only view completed gameweeks. Try selecting any GW up to **GW {lcg}**.
        """.replace("{lcg}", str(latest_completed_gw))
    )
    st.info("Tip: come back after the GW is over — the slammers will be ready!")
    # Optional small playful message (customize as you like)
    st.markdown("> _Oi, even Pep doesn’t rotate this early._ ⚽️")
    st.stop()  # stops the rest of the page from executing

# If we reach here, the selected GW is completed — proceed with normal logic
with st.spinner("Loading managers…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

rows: List[Dict[str, Any]] = []
with st.spinner(f"Fetching Gameweek {gw} points…"):
    for m in standings:
        entry_id = int(m["entry"])
        picks = fetch_entry_event_picks(entry_id, gw)
        pts = compute_net_points(picks)  # dict: raw_points, minus_points, net_points

        rows.append({
            "entry": entry_id,
            "Manager": m.get("player_name", ""),
            "Team": m.get("entry_name", ""),
            "GWPoints": int(pts.get("net_points", 0)),   # keep using final (net) points
            "TotalPoints": int(m.get("total", 0)),
        })

# Build DataFrame and sort: primary by GWPoints desc, then TotalPoints desc
df = pd.DataFrame(rows).sort_values(by=["GWPoints", "TotalPoints"], ascending=[False, False]).reset_index(drop=True)

# Build groups of ties by GWPoints value preserving order
groups = []
i = 0
n = len(df)
while i < n:
    val = df.loc[i, "GWPoints"]
    j = i
    indices = []
    while j < n and df.loc[j, "GWPoints"] == val:
        indices.append(j)
        j += 1
    groups.append({"value": val, "indices": indices, "start_pos": i + 1, "size": len(indices)})
    i = j

# Prepare medal column (empty by default)
medal_col = [""] * n

def assign_medal_to_group(group_indices: List[int], emoji: str):
    for idx in group_indices:
        medal_col[idx] = emoji

# Assign medals according to rules (with 3+ tie-at-top handling)
for gi, group in enumerate(groups):
    start = group["start_pos"]
    size = group["size"]

    # Tie for 1st (group starts at 1)
    if start == 1:
        if size == 1:
            assign_medal_to_group(group["indices"], "🥇")
        else:
            # multiple tied for 1st
            # Special rule: if 3 or more tied at 1st -> all get gold, silver & bronze skipped
            if size >= 3:
                assign_medal_to_group(group["indices"], "🥇")
                # skip any further medals entirely
                break
            else:
                # size == 2: both get gold; silver skipped; next group (if present) becomes bronze
                assign_medal_to_group(group["indices"], "🥇")
                if gi + 1 < len(groups):
                    next_group = groups[gi + 1]
                    if next_group["start_pos"] == 3:
                        assign_medal_to_group(next_group["indices"], "🥉")
        continue

    # Tie for 2nd (group starts at 2)
    if start == 2:
        if size == 1:
            assign_medal_to_group(group["indices"], "🥈")
        else:
            # tie for 2nd -> both get silver; bronze skipped
            assign_medal_to_group(group["indices"], "🥈")
        continue

    # Tie for 3rd (group starts at 3)
    if start == 3:
        assign_medal_to_group(group["indices"], "🥉")
        continue

    # groups after position 3 get no medal

# Final display DataFrame
df_display = df.copy()
df_display.index = df_display.index + 1  # 1-based index
df_display.index.name = "Rank"
df_display.insert(0, "Medal", medal_col)

# Show columns
show_cols = ["Medal", "Manager", "Team", "GWPoints", "TotalPoints"]
df_display = df_display[show_cols]

st.dataframe(df_display.rename(columns={"GWPoints": "GW Points", "TotalPoints": "Total Points"}), use_container_width=True)

# Legend for medal rules (updated)
st.markdown(
    """
    **🏅 Medal Rules with Ties**
    - Normal: 1 → 🥇, 2 → 🥈, 3 → 🥉  
    - Tie for **1st** (2 managers): both get 🥇, silver skipped, next rank → 🥉  
    - Tie for **1st** (3 or more managers): **all tied get 🥇**, silver & bronze are skipped.  
    - Tie for **2nd** (two or more): 1 → 🥇, tied group → 🥈, bronze skipped  
    - Tie for **3rd**: all tied at 3rd get 🥉
    """
)
