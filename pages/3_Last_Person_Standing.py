# pages/3_Last_Person_Standing.py
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Set, Tuple

from services.fpl_service import (
    fetch_all_league_standings,
    fetch_entry_event_picks,
    compute_net_points,
)
from services.lps import elimination_schedule, coin_toss_seeded
from utils import add_logo_fixed

# ---------- CONFIG ----------
st.set_page_config(page_title="Last Person Standing", layout="wide")

# Logo (optional, safe import)
try:
    add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)
except Exception:
    pass

LEAGUE_ID = 1124151  # replace with your league ID

st.title("🪓 Last Person Standing")

# Gameweek selector
selected_gw = st.selectbox("Select Gameweek", options=list(range(1, 39)), index=0)

# Fetch standings
with st.spinner("Loading league standings…"):
    standings = fetch_all_league_standings(LEAGUE_ID)
    idx_by_entry: Dict[int, Dict[str, Any]] = {int(r["entry"]): r for r in standings}

initial_survivors: Set[int] = set(idx_by_entry.keys())


@st.cache_data(ttl=600, show_spinner=False)
def gw_snapshot_from_entries(
    league_id: int, gw: int, entries_tuple: Tuple[int, ...]
) -> pd.DataFrame:
    """
    Snapshot for given GW & entries: returns DataFrame with Raw, Minus, Net points
    plus overall rank/points from standings.
    """
    rows: List[Dict[str, Any]] = []
    for entry_id in entries_tuple:
        try:
            picks = fetch_entry_event_picks(entry_id, gw)
            pts = compute_net_points(picks)
            s = idx_by_entry.get(int(entry_id), {})
            rows.append({
                "entry": int(entry_id),
                "Manager": s.get("player_name", ""),
                "Team": s.get("entry_name", ""),
                "OverallRank": int(s.get("rank", 10**9)),
                "OverallPoints": int(s.get("total", 0)),
                "RawPoints": int(pts.get("raw_points", 0)),
                "MinusPoints": int(pts.get("minus_points", 0)),
                "NetPoints": int(pts.get("net_points", 0)),
            })
        except Exception:
            s = idx_by_entry.get(int(entry_id), {})
            rows.append({
                "entry": int(entry_id),
                "Manager": s.get("player_name", ""),
                "Team": s.get("entry_name", ""),
                "OverallRank": int(s.get("rank", 10**9)),
                "OverallPoints": int(s.get("total", 0)),
                "RawPoints": 0,
                "MinusPoints": 0,
                "NetPoints": 0,
            })
    return pd.DataFrame(rows)


# ---------- CUMULATIVE ELIMINATIONS ----------
elimination_log: Dict[int, List[Dict[str, Any]]] = {}
survivors: Set[int] = set(initial_survivors)

for gw in range(1, selected_gw + 1):
    n_elim = elimination_schedule(gw)
    if n_elim == 0 or len(survivors) <= 1:
        elimination_log[gw] = []
        continue

    # Snapshot for current survivors
    entries_tuple = tuple(sorted(list(survivors)))
    snapshot_df = gw_snapshot_from_entries(LEAGUE_ID, gw, entries_tuple)

    if snapshot_df is None or snapshot_df.empty:
        elimination_log[gw] = []
        continue

    # Sort for bottom detection
    snapshot_df = snapshot_df.sort_values(
        by=["NetPoints", "OverallRank", "MinusPoints"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    # Determine bottom block
    if n_elim >= len(snapshot_df):
        bottom_block = snapshot_df.copy()
    else:
        threshold = snapshot_df.iloc[n_elim - 1]["NetPoints"]
        bottom_block = snapshot_df[snapshot_df["NetPoints"] <= threshold].copy()

    strict_out = bottom_block[bottom_block["NetPoints"] < bottom_block["NetPoints"].max()].copy()
    remaining_slots = max(0, n_elim - len(strict_out))

    tied_group = bottom_block[bottom_block["NetPoints"] == bottom_block["NetPoints"].max()].copy()

    eliminated_rows: List[pd.Series] = []
    for _, r in strict_out.iterrows():
        eliminated_rows.append(r)

    if remaining_slots > 0 and not tied_group.empty:
        tied_group = tied_group.sort_values(
            by=["OverallRank", "MinusPoints"],
            ascending=[False, False],
        ).reset_index(drop=True)

        if remaining_slots < len(tied_group):
            shuffled = coin_toss_seeded(list(tied_group.to_dict("records")), gw)
            tied_group = pd.DataFrame(shuffled)

        for i in range(min(remaining_slots, len(tied_group))):
            eliminated_rows.append(tied_group.iloc[i])

    # Finalize eliminated entries
    eliminated_entries: List[Dict[str, Any]] = []
    for r in eliminated_rows:
        entry_id = int(r["entry"])
        if entry_id not in survivors:
            continue
        survivors.remove(entry_id)
        eliminated_entries.append({
            "entry": entry_id,
            "Manager": r["Manager"],
            "Team": r["Team"],
            "RawPoints": int(r["RawPoints"]),
            "MinusPoints": int(r["MinusPoints"]),
            "NetPoints": int(r["NetPoints"]),
            "OverallPoints": int(r["OverallPoints"]),
            "OverallRank": int(r["OverallRank"]),
        })

    elimination_log[gw] = eliminated_entries


# ---------- UI ----------
st.subheader(f"Gameweek {selected_gw} — Eliminations")

gw_elims = elimination_log.get(selected_gw, [])
if not gw_elims:
    st.info(f"No eliminations this week (GW {selected_gw}).")
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
        "MinusPoints": "Minus Points",
        "NetPoints": "Net Points",
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
survivor_rows: List[Dict[str, Any]] = []
for e in survivor_entries:
    s = idx_by_entry.get(e, {})
    survivor_rows.append({
        "Manager": s.get("player_name", ""),
        "Team": s.get("entry_name", ""),
        "Overall Rank": s.get("rank", None),
        "Overall Points": s.get("total", None),
    })

survivor_df = pd.DataFrame(survivor_rows)
if not survivor_df.empty:
    survivor_df = survivor_df.sort_values(by=["Overall Rank", "Manager"], ascending=[True, True])

st.write(f"**{len(survivor_df)} managers left after GW {selected_gw}**")
with st.expander("Show survivors list"):
    st.dataframe(survivor_df, use_container_width=True, hide_index=True)
