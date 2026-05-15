import streamlit as st
import pandas as pd

from config import IRON_MAN_BASE_GW, LEAGUE_ID
from services.fpl_service import fetch_bootstrap_static
from services.snapshots import get_or_capture_league_rank_snapshot
from utils import add_logo_fixed

st.set_page_config(page_title="Iron Man Award", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("💪 Iron Man Award")
st.caption("Biggest official Big Whammy rank climber from GW19 to the latest completed GW")

bs = fetch_bootstrap_static()
events = bs.get("events", []) or []
latest_gw = max((e.get("id", 0) for e in events if e.get("finished")), default=0)

if latest_gw < IRON_MAN_BASE_GW:
    st.warning("Iron Man race begins after Gameweek 19.")
    st.stop()

force_refresh = st.button("Refresh official snapshots")

with st.spinner(f"Loading official Big Whammy ranks after GW{IRON_MAN_BASE_GW}…"):
    base_snapshot = get_or_capture_league_rank_snapshot(
        LEAGUE_ID,
        IRON_MAN_BASE_GW,
        force_refresh=force_refresh,
    )

with st.spinner(f"Loading official Big Whammy ranks after GW{latest_gw}…"):
    current_snapshot = get_or_capture_league_rank_snapshot(
        LEAGUE_ID,
        latest_gw,
        force_refresh=force_refresh,
    )

if not base_snapshot:
    st.error(f"No official snapshot found for GW{IRON_MAN_BASE_GW}.")
    st.stop()

if not current_snapshot:
    st.error(f"No official snapshot found for GW{latest_gw}.")
    st.stop()

base_by_entry = {int(row["entry"]): row for row in base_snapshot}
current_by_entry = {int(row["entry"]): row for row in current_snapshot}

rows = []
for entry, base_row in base_by_entry.items():
    current_row = current_by_entry.get(entry)
    if not current_row:
        continue

    start_rank = int(base_row["rank"])
    current_rank = int(current_row["rank"])
    rank_gain = start_rank - current_rank

    rows.append(
        {
            "Manager": current_row.get("player_name") or base_row.get("player_name", ""),
            "Team": current_row.get("entry_name") or base_row.get("entry_name", ""),
            "Rank After GW19": start_rank,
            f"Rank After GW{latest_gw}": current_rank,
            "Rank Gain": rank_gain,
            "Current Points": int(current_row.get("total", 0)),
        }
    )

if not rows:
    st.error("No matching managers found between the GW19 and current official snapshots.")
    st.stop()

df = pd.DataFrame(rows).sort_values(
    by=["Rank Gain", f"Rank After GW{latest_gw}"],
    ascending=[False, True],
).reset_index(drop=True)

positions = []
current_pos = 1
for i, row in df.iterrows():
    if i == 0:
        positions.append(current_pos)
    elif row["Rank Gain"] == df.loc[i - 1, "Rank Gain"]:
        positions.append(current_pos)
    else:
        current_pos = i + 1
        positions.append(current_pos)

df.insert(0, "Position", positions)


def medal(position: int) -> str:
    if position == 1:
        return "🥇"
    if position == 2:
        return "🥈"
    return ""


df.insert(1, "", df["Position"].apply(medal))

st.dataframe(
    df[
        [
            "Position",
            "",
            "Manager",
            "Team",
            "Rank After GW19",
            f"Rank After GW{latest_gw}",
            "Rank Gain",
            "Current Points",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

captured_at_values = [
    row.get("captured_at") for row in current_snapshot if row.get("captured_at")
]
if captured_at_values:
    st.caption(f"Current snapshot saved: {max(captured_at_values)}")

st.markdown(
    """
**Tie Rule:**  
If multiple managers finish 1st or 2nd, the prize money is shared.
"""
)
