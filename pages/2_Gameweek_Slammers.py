# pages/2_Gameweek_Slammers.py
import streamlit as st
import pandas as pd

from services.fpl_service import fetch_all_league_standings, fetch_entry_event_picks, compute_net_points
from utils import add_logo_fixed

st.set_page_config(page_title="Awards", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151  # <-- your league ID

st.title("🏆 Gameweek Slammers")

gw = st.selectbox("Select Gameweek", list(range(1, 39)), index=0)

with st.spinner("Loading managers…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

rows = []
with st.spinner(f"Fetching Gameweek {gw} points…"):
    for m in standings:
        entry_id = m["entry"]
        picks = fetch_entry_event_picks(entry_id, gw)
        pts = compute_net_points(picks)  # dict: net_points, raw_points, minus_points

        rows.append({
            "Manager": m["player_name"],
            "Team": m["entry_name"],
            "GW Points": pts["net_points"],   # ✅ keep net points
            "Total Points": m["total"],
        })

# Sort by GW Points desc, then Total Points desc
df = pd.DataFrame(rows).sort_values(
    by=["GW Points", "Total Points"], ascending=[False, False]
).reset_index(drop=True)

# Identify ties and assign medals
medals = [""] * len(df)

i = 0
rank = 1
while i < len(df) and rank <= 3:
    # Find group of tied managers (same GW Points)
    tied_group = [i]
    j = i + 1
    while j < len(df) and df.loc[j, "GW Points"] == df.loc[i, "GW Points"]:
        tied_group.append(j)
        j += 1

    # Assign medals based on tie position
    if rank == 1:
        for idx in tied_group:
            medals[idx] = "🥇"
        if len(tied_group) > 1 and rank + len(tied_group) == 3:
            # Tie for 1st, next rank is 3rd → bronze
            pass
    elif rank == 2:
        for idx in tied_group:
            medals[idx] = "🥈"
    elif rank == 3:
        for idx in tied_group:
            medals[idx] = "🥉"

    # Move to next group
    rank += len(tied_group)
    i = j

df.insert(0, "Medal", medals)
df.index = df.index + 1
df.index.name = "Rank"

st.dataframe(df[["Medal", "Manager", "Team", "GW Points"]], use_container_width=True)

# Legend for medal rules
st.markdown(
    """
    **🏅 Medal Rules with Ties**
    - Normal: 1 → 🥇, 2 → 🥈, 3 → 🥉  
    - Tie for 1st: all tied get 🥇, silver skipped, next rank → 🥉  
    - Tie for 2nd: 1 → 🥇, all tied get 🥈, bronze skipped  
    - Tie for 3rd: all tied get 🥉
    """
)
