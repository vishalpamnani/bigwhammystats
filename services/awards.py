from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from services.fpl_service import (
    compute_net_points,
    fetch_all_league_standings,
    fetch_entry_event_picks,
    fetch_entry_history,
    fetch_h2h_matches,
    fetch_league_cup_status,
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


@st.cache_data(ttl=600, show_spinner=False)
def everest_rows(league_id: int, latest_completed_gw: int) -> List[Dict[str, Any]]:
    standings = fetch_all_league_standings(league_id)
    rows: List[Dict[str, Any]] = []

    for manager in standings:
        entry_id = int(manager["entry"])
        entry_history = fetch_entry_history(entry_id)
        chip_gws = {
            int(chip["event"])
            for chip in entry_history.get("chips", []) or []
            if chip.get("event") is not None
        }

        for gw_row in entry_history.get("current", []) or []:
            gw = int(gw_row.get("event", 0))
            if not 1 <= gw <= min(38, latest_completed_gw):
                continue
            if gw in chip_gws:
                continue

            raw_points = int(gw_row.get("points", 0))
            minus_points = int(gw_row.get("event_transfers_cost", 0))
            rows.append(
                {
                    "Manager": manager.get("player_name", ""),
                    "Team": manager.get("entry_name", ""),
                    "Gameweek": f"GW{gw}",
                    "Points": raw_points,
                    "Minus Points": minus_points,
                    "Net Points": raw_points - minus_points,
                }
            )

    return rows


def everest_table(league_id: int, latest_completed_gw: int) -> pd.DataFrame:
    rows = everest_rows(league_id, latest_completed_gw)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values(
        by=["Net Points", "Points", "Gameweek", "Manager"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)
    return _position_rows(df, ["Net Points"])


def _match_participant(match: Dict[str, Any], side: int) -> Dict[str, Any]:
    return {
        "entry": int(match.get(f"entry_{side}_entry") or 0),
        "Manager": match.get(f"entry_{side}_player_name", ""),
        "Team": match.get(f"entry_{side}_name", ""),
        "Points": int(match.get(f"entry_{side}_points") or 0),
    }


def _winner_and_loser(match: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    entry_1 = _match_participant(match, 1)
    entry_2 = _match_participant(match, 2)
    winner_entry = int(match.get("winner") or 0)

    if winner_entry == entry_1["entry"]:
        return entry_1, entry_2
    return entry_2, entry_1


@st.cache_data(ttl=600, show_spinner=False)
def knockout_cup_rows(league_id: int) -> List[Dict[str, Any]]:
    cup_status = fetch_league_cup_status(league_id)
    cup_league_id = cup_status.get("league")
    if not cup_league_id:
        return []

    final_matches = fetch_h2h_matches(int(cup_league_id), event=38)
    semifinal_matches = fetch_h2h_matches(int(cup_league_id), event=37)
    if not final_matches:
        return []

    final_match = final_matches[0]
    winner, runner_up = _winner_and_loser(final_match)
    rows = [
        {
            "Award": "Winner",
            "Manager": winner["Manager"],
            "Team": winner["Team"],
            "Gameweek": f"GW{final_match.get('event')}",
            "Points": winner["Points"],
        },
        {
            "Award": "Runner-up",
            "Manager": runner_up["Manager"],
            "Team": runner_up["Team"],
            "Gameweek": f"GW{final_match.get('event')}",
            "Points": runner_up["Points"],
        },
    ]

    semifinal_losers = []
    for match in semifinal_matches:
        if (match.get("knockout_name") or "").lower() != "semi-final":
            continue
        _, loser = _winner_and_loser(match)
        loser["Gameweek"] = f"GW{match.get('event')}"
        semifinal_losers.append(loser)

    semifinal_losers = sorted(
        semifinal_losers,
        key=lambda item: (-item["Points"], item["Manager"]),
    )

    runner_up_labels = ["Second Runner-up", "Third Runner-up"]
    for index, loser in enumerate(semifinal_losers[:2]):
        rows.append(
            {
                "Award": runner_up_labels[index],
                "Manager": loser["Manager"],
                "Team": loser["Team"],
                "Gameweek": loser["Gameweek"],
                "Points": loser["Points"],
            }
        )

    return rows
