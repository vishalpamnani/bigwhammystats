# pages/last_person_standing.py
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Set

from services.fpl_service import (
    fetch_all_league_standings,
    fetch_entry_event_picks,
    compute_net_points,
)
from services.lps import elimination_schedule, coin_toss_seeded
from utils import add_logo_fixed


# --- CONFIG ---

st.set_page_config(page_title="Last Person Standing", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151  # <-- replace with your league ID

st.title("🪓 Last Person Standing")

# Gameweek selector (dropdown)
selected_gw = st.selectbox("Select Gameweek", options=list(range(1, 39)), index=0)

# Fetch full standings (all pages)
with st.spinner("Loading league standings…"):
    standings = fetch_all_league_standings(LEAGUE_ID)
    idx_by_entry = {row["entry"]: row for row in standings}

# Initial survivor set = everyone present in standings
initial_survivors: Set[int] = set(idx_by_entry.keys())


@st.cache_data(ttl=600, show_spinner=False)
def gw_snapshot(
    league_id: int, gw: int, entries: List[int], idx_map: Dict[int, Dict[str, Any]]
) -> pd.DataFrame:
    rows = []
    for entry_id in entries:
        try:
            picks = fetch_entry_event_picks(entry_id, gw)
            pts = compute_net_points(picks)
            s = idx_map.get(entry_id, {})  # overall snapshot

            rows.append({
                "entry": entry_id,
                "Manager": s.get("player_name", ""),
                "Team": s.get("entry_name", ""),
                "OverallRank": int(s.get("rank", 10**9)),
                "OverallPoints": int(s.get("total", 0)),
                "RawPoints": pts["raw_points"],       
                "MinusPoints": pts["minus_points"],   
                "NetPoints": pts["net_points"],       
            })
        except Exception as e:
            # Prevent one bad entry from killing everything
            print(f"⚠️ Error for entry {entry_id}, GW {gw}: {e}")

    if not rows:
        return pd.DataFrame(columns=[
            "entry", "Manager", "Team", "OverallRank", 
            "OverallPoints", "RawPoints", "MinusPoints", "NetPoints"
        ])

    return pd.DataFrame(rows)

# Run cumulative eliminations from GW1 → selected_gw
elimination_log: Dict[int, List[Dict[str, Any]]] = {}
survivors: Set[int] = set(initial_survivors)

for gw in range(1, selected_gw + 1):
    n_elim = elimination_schedule(gw)
    if n_elim == 0 or len(survivors) <= 1:
        elimination_log[gw] = []
        continue

    entries = list(survivors)
    df = gw_snapshot(LEAGUE_ID, gw, entries, idx_by_entry)

    if df is None or df.empty:
        elimination_log[gw] = []
        continue  # skip this GW safely

    # Base sort (who is at the bottom):
    df = df.sort_values(
        by=["NetPoints", "OverallRank", "MinusPoints"],
        ascending=[True, True, False],
).reset_index(drop=True)


    # Determine bottom block including ties on NetPoints threshold
    if n_elim >= len(df):
        bottom_block = df.copy()
    else:
        threshold = df.iloc[n_elim - 1]["NetPoints"]
        bottom_block = df[df["NetPoints"] <= threshold].copy()

    # Strict outs
    strict_out = bottom_block[
        bottom_block["NetPoints"] < bottom_block["NetPoints"].max()
    ].copy()
    remaining_slots = max(0, n_elim - len(strict_out))

    # Tied group
    tied_group = bottom_block[
        bottom_block["NetPoints"] == bottom_block["NetPoints"].max()
    ].copy()

    eliminated_rows: List[pd.Series] = []
    for _, r in strict_out.iterrows():
        eliminated_rows.append(r)

    if remaining_slots > 0 and len(tied_group) > 0:
        tied_group = tied_group.sort_values(
            by=["OverallRank", "MinusPoints"],
            ascending=[False, False],
        ).reset_index(drop=True)

        if remaining_slots < len(tied_group):
            shuffled = coin_toss_seeded(list(tied_group.to_dict("records")), gw)
            tied_group = pd.DataFrame(shuffled)

        eliminated_rows.extend(
            [tied_group.iloc[i] for i in range(min(remaining_slots, len(tied_group)))]
        )

    # Apply eliminations
    eliminated_entries = []
    for r in eliminated_rows:
        entry_id = int(r["entry"])
        if entry_id in survivors:
            survivors.remove(entry_id)
            eliminated_entries.append(
                {
                    "entry": entry_id,
                    "Manager": r["Manager"],
                    "Team": r["Team"],
                    "RawPoints": int(r["RawPoints"]),
                    "NetPoints": int(r["NetPoints"]),
                    "MinusPoints": int(r["MinusPoints"]),
                    "OverallPoints": int(r["OverallPoints"]),
                    "OverallRank": int(r["OverallRank"]),
                }
            )

    elimination_log[gw] = eliminated_entries


# ------- UI for selected GW -------
st.subheader(f"Gameweek {selected_gw} — Eliminations")

gw_elims = elimination_log.get(selected_gw, [])
if not gw_elims:
    st.warning(f"No elimination data available for GW {selected_gw}. ")
else:
    elim_df = pd.DataFrame(gw_elims)
    elim_df.insert(0, "Elim #", range(1, len(elim_df) + 1))

    display_cols = [
        "Elim #",
        "Manager",
        "Team",
        "RawPoints",
        "MinusPoints",
        "NetPoints",
        "OverallPoints",
        "OverallRank",
    ]
    rename_map = {
        "RawPoints": "Points",
        "NetPoints": "Net Points",
        "MinusPoints": "Minus Points",
        "OverallPoints": "Overall Points",
        "OverallRank": "Overall Rank",
    }

    st.dataframe(
        elim_df[display_cols].rename(columns=rename_map),
        use_container_width=True,
        hide_index=True,
    )


# Survivors after selected GW
survivor_entries = list(survivors)
survivor_rows = []
for e in survivor_entries:
    s = idx_by_entry.get(e, {})
    survivor_rows.append(
        {
            "Manager": s.get("player_name", ""),
            "Team": s.get("entry_name", ""),
            "Overall Rank": s.get("rank", None),
            "Overall Points": s.get("total", None),
        }
    )
survivor_df = pd.DataFrame(survivor_rows).sort_values(
    by=["Overall Rank", "Manager"], ascending=[True, True]
)

st.write(f"**Survivors after GW {selected_gw}: {len(survivor_df)}**")
with st.expander("Show survivors list"):
    st.dataframe(survivor_df, use_container_width=True, hide_index=True)
