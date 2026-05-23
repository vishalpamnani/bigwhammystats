from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from services.fpl_service import (
    compute_net_points,
    fetch_all_league_standings,
    fetch_entry_event_picks,
    fetch_entry_history,
)

LATE_SURGE_GWS = list(range(34, 39))


def _wildcard_gws_from_history(entry_history: Dict[str, Any], latest_completed_gw: int) -> List[Dict[str, int]]:
    wildcard_gws = []
    for chip in entry_history.get("chips", []) or []:
        chip_name = (chip.get("name") or "").lower()
        gw = chip.get("event")
        if chip_name != "wildcard" or gw is None:
            continue

        gw = int(gw)
        if 1 <= gw <= min(38, latest_completed_gw):
            wildcard_gws.append({"gw": gw})

    wildcard_gws = sorted(wildcard_gws, key=lambda item: item["gw"])
    for index, item in enumerate(wildcard_gws, start=1):
        item["wildcard_number"] = index

    return wildcard_gws


def _position_rows(df: pd.DataFrame, rank_cols: List[str]) -> pd.DataFrame:
    positions = []
    current_pos = 1

    for i, row in df.iterrows():
        if i == 0:
            positions.append(current_pos)
            continue

        previous = df.loc[i - 1]
        tied = all(row[col] == previous[col] for col in rank_cols)
        if tied:
            positions.append(current_pos)
        else:
            current_pos = i + 1
            positions.append(current_pos)

    output = df.copy()
    output.insert(0, "Position", positions)
    return output


@st.cache_data(ttl=600, show_spinner=False)
def wildcard_wizard_rows(league_id: int, latest_completed_gw: int) -> List[Dict[str, Any]]:
    standings = fetch_all_league_standings(league_id)
    rows: List[Dict[str, Any]] = []

    for manager in standings:
        entry_id = int(manager["entry"])
        entry_history = fetch_entry_history(entry_id)
        wildcard_gws = _wildcard_gws_from_history(entry_history, latest_completed_gw)

        for wildcard in wildcard_gws:
            gw = wildcard["gw"]
            picks = fetch_entry_event_picks(entry_id, gw)
            active_chip = (picks.get("active_chip") or "").lower()
            if active_chip and active_chip != "wildcard":
                continue

            points = compute_net_points(picks)
            rows.append(
                {
                    "Manager": manager.get("player_name", ""),
                    "Team": manager.get("entry_name", ""),
                    "Gameweek": f"GW{gw} - WC {wildcard['wildcard_number']}",
                    "Points": int(points["raw_points"]),
                }
            )

    return rows


def wildcard_wizard_table(league_id: int, latest_completed_gw: int) -> pd.DataFrame:
    rows = wildcard_wizard_rows(league_id, latest_completed_gw)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values(
        by=["Points", "Gameweek", "Manager"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    return _position_rows(df, ["Points"])


@st.cache_data(ttl=600, show_spinner=False)
def late_surge_rows(league_id: int, latest_completed_gw: int) -> List[Dict[str, Any]]:
    standings = fetch_all_league_standings(league_id)
    completed_gws = [gw for gw in LATE_SURGE_GWS if gw <= latest_completed_gw]
    rows: List[Dict[str, Any]] = []

    if not completed_gws:
        return rows

    for manager in standings:
        entry_id = int(manager["entry"])
        gw_scores: Dict[int, int] = {}

        for gw in completed_gws:
            picks = fetch_entry_event_picks(entry_id, gw)
            points = compute_net_points(picks)
            gw_scores[gw] = int(points["net_points"])

        rows.append(
            {
                "Manager": manager.get("player_name", ""),
                "Team": manager.get("entry_name", ""),
                "Total Points": sum(gw_scores.values()),
                "Highest Single GW": max(gw_scores.values()),
                **{f"GW{gw}": gw_scores.get(gw, 0) for gw in LATE_SURGE_GWS},
            }
        )

    return rows


def late_surge_table(league_id: int, latest_completed_gw: int) -> pd.DataFrame:
    rows = late_surge_rows(league_id, latest_completed_gw)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values(
        by=["Total Points", "Highest Single GW", "Manager"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return _position_rows(df, ["Total Points", "Highest Single GW"])
