import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from config import BASE_DIR, IRON_MAN_BASE_GW, LEAGUE_ID
from services.awards import (
    everest_table,
    knockout_cup_rows,
    late_surge_table,
    wildcard_wizard_table,
)
from services.fpl_service import (
    compute_net_points,
    fetch_all_league_standings,
    fetch_entry_event_picks,
)
from services.lps import coin_toss_seeded, elimination_schedule
from services.snapshots import get_or_capture_league_rank_snapshot

LEDGER_PATH = BASE_DIR / "data" / "winners_ledger_2025_26.json"

PAYOUTS = {
    "gw_slammer": 1800,
    "gw_second": 1100,
    "gw_third": 700,
    "manager_of_season": 15000,
    "second_place": 8000,
    "third_place": 6000,
    "fourth_place": 4000,
    "europa_1": 3500,
    "europa_2": 3000,
    "knockout_winner": 6000,
    "knockout_runner_up": 3000,
    "knockout_second_runner_up": 2000,
    "knockout_third_runner_up": 2000,
    "iron_man": 6000,
    "iron_man_runner_up": 3000,
    "everest": 3000,
    "last_person_standing": 6000,
    "second_last_person_standing": 4000,
    "third_last_person_standing": 3000,
    "wildcard_wizard": 3000,
    "late_surge": 3000,
    "diogo_jota_tribute": 3000,
}


def manager_key(manager: str, team: str) -> str:
    return f"{manager} - {team}"


def _entry(
    manager: str,
    team: str,
    award: str,
    detail: str,
    position: str,
    wc: float,
    source: str,
) -> Dict[str, Any]:
    return {
        "manager": manager,
        "team": team,
        "manager_team": manager_key(manager, team),
        "award": award,
        "detail": detail,
        "position": position,
        "wc": int(wc) if float(wc).is_integer() else round(float(wc), 2),
        "source": source,
    }


def _split_pot(total: int, winners: List[Dict[str, Any]]) -> float:
    return total / len(winners) if winners else 0


def _gw_points_rows(league_id: int, gw: int) -> pd.DataFrame:
    standings = fetch_all_league_standings(league_id)
    rows = []
    for manager in standings:
        entry_id = int(manager["entry"])
        picks = fetch_entry_event_picks(entry_id, gw)
        points = compute_net_points(picks)
        rows.append(
            {
                "entry": entry_id,
                "Manager": manager.get("player_name", ""),
                "Team": manager.get("entry_name", ""),
                "GWPoints": int(points["net_points"]),
                "TotalPoints": int(manager.get("total", 0)),
            }
        )

    return pd.DataFrame(rows).sort_values(
        by=["GWPoints", "TotalPoints"],
        ascending=[False, False],
    ).reset_index(drop=True)


def _score_groups(df: pd.DataFrame) -> List[Dict[str, Any]]:
    groups = []
    i = 0
    while i < len(df):
        value = df.loc[i, "GWPoints"]
        j = i
        indices = []
        while j < len(df) and df.loc[j, "GWPoints"] == value:
            indices.append(j)
            j += 1
        groups.append({"value": value, "indices": indices, "start_pos": i + 1, "size": len(indices)})
        i = j
    return groups


def _gameweek_slammer_entries(league_id: int) -> List[Dict[str, Any]]:
    entries = []

    for gw in range(1, 39):
        df = _gw_points_rows(league_id, gw)
        groups = _score_groups(df)
        if not groups:
            continue

        first = groups[0]
        if first["size"] == 1:
            row = df.loc[first["indices"][0]]
            entries.append(
                _entry(
                    row["Manager"],
                    row["Team"],
                    f"Gameweek Slammer GW{gw}",
                    f"{row['GWPoints']} net points",
                    "Winner",
                    PAYOUTS["gw_slammer"],
                    "Gameweek Slammers",
                )
            )
        elif first["size"] == 2:
            winners = [df.loc[index] for index in first["indices"]]
            payout = _split_pot(PAYOUTS["gw_slammer"] + PAYOUTS["gw_second"], winners)
            for row in winners:
                entries.append(
                    _entry(
                        row["Manager"],
                        row["Team"],
                        f"Gameweek Slammer GW{gw}",
                        f"{row['GWPoints']} net points",
                        "Joint Winner",
                        payout,
                        "Gameweek Slammers",
                    )
                )
        else:
            winners = [df.loc[index] for index in first["indices"]]
            payout = _split_pot(
                PAYOUTS["gw_slammer"] + PAYOUTS["gw_second"] + PAYOUTS["gw_third"],
                winners,
            )
            for row in winners:
                entries.append(
                    _entry(
                        row["Manager"],
                        row["Team"],
                        f"Gameweek Slammer GW{gw}",
                        f"{row['GWPoints']} net points",
                        "Joint Winner",
                        payout,
                        "Gameweek Slammers",
                    )
                )
            continue

        for group in groups[1:]:
            rows = [df.loc[index] for index in group["indices"]]
            if group["start_pos"] == 2:
                payout = _split_pot(PAYOUTS["gw_second"], rows)
                for row in rows:
                    entries.append(
                        _entry(
                            row["Manager"],
                            row["Team"],
                            f"Second Slammer GW{gw}",
                            f"{row['GWPoints']} net points",
                            "Second",
                            payout,
                            "Gameweek Slammers",
                        )
                    )
                if group["size"] > 1:
                    break
                continue

            if group["start_pos"] == 3:
                payout = _split_pot(PAYOUTS["gw_third"], rows)
                for row in rows:
                    entries.append(
                        _entry(
                            row["Manager"],
                            row["Team"],
                            f"Third Slammer GW{gw}",
                            f"{row['GWPoints']} net points",
                            "Third",
                            payout,
                            "Gameweek Slammers",
                        )
                    )
                break

    return entries


def _overall_entries(league_id: int) -> List[Dict[str, Any]]:
    standings = fetch_all_league_standings(league_id)
    position_awards = {
        1: ("Manager of the Season", "Winner", PAYOUTS["manager_of_season"]),
        2: ("2nd Place", "Second", PAYOUTS["second_place"]),
        3: ("3rd Place", "Third", PAYOUTS["third_place"]),
        4: ("4th Place", "Fourth", PAYOUTS["fourth_place"]),
        5: ("Europa 1", "Fifth", PAYOUTS["europa_1"]),
        6: ("Europa 2", "Sixth", PAYOUTS["europa_2"]),
    }
    entries = []

    df = pd.DataFrame(
        [
            {
                "Manager": row.get("player_name", ""),
                "Team": row.get("entry_name", ""),
                "Total": int(row.get("total", 0)),
                "Official Rank": int(row.get("rank", 0)),
            }
            for row in standings
        ]
    ).sort_values(["Total", "Official Rank", "Manager"], ascending=[False, True, True]).reset_index(drop=True)

    groups = []
    i = 0
    while i < len(df):
        total = df.loc[i, "Total"]
        j = i
        indices = []
        while j < len(df) and df.loc[j, "Total"] == total:
            indices.append(j)
            j += 1
        groups.append({"start": i + 1, "end": j, "indices": indices})
        i = j

    for group in groups:
        occupied_positions = range(group["start"], group["end"] + 1)
        paid_positions = [pos for pos in occupied_positions if pos in position_awards]
        if not paid_positions:
            continue
        payout = sum(position_awards[pos][2] for pos in paid_positions) / len(group["indices"])
        first_position = paid_positions[0]
        award, position, _ = position_awards[first_position]
        if len(group["indices"]) > 1:
            position = f"Joint {position}"

        for index in group["indices"]:
            row = df.loc[index]
            entries.append(
                _entry(
                    row["Manager"],
                    row["Team"],
                    award,
                    f"Final Big Whammy rank {group['start']} with {row['Total']} points",
                    position,
                    payout,
                    "Overall Standings",
                )
            )

    jota_rows = [row for row in standings if int(row.get("rank", 0)) == 20]
    jota_payout = _split_pot(PAYOUTS["diogo_jota_tribute"], jota_rows)
    for row in jota_rows:
        entries.append(
            _entry(
                row.get("player_name", ""),
                row.get("entry_name", ""),
                "Diogo Jota Tribute Award",
                "Final Big Whammy rank 20",
                "#20 Finish",
                jota_payout,
                "Overall Standings",
            )
        )
    return entries


def _ranked_award_entries(
    df: pd.DataFrame,
    award_name: str,
    payout_keys: List[str],
    source: str,
    detail_fn,
) -> List[Dict[str, Any]]:
    entries = []
    for position, payout_key in enumerate(payout_keys, start=1):
        winners = df[df["Position"] == position]
        if winners.empty:
            continue
        payout = _split_pot(PAYOUTS[payout_key], winners.to_dict("records"))
        position_label = "Winner" if position == 1 else "Runner-up"
        for _, row in winners.iterrows():
            entries.append(
                _entry(
                    row["Manager"],
                    row["Team"],
                    award_name,
                    detail_fn(row),
                    position_label,
                    payout,
                    source,
                )
            )
    return entries


def _iron_man_entries(league_id: int) -> List[Dict[str, Any]]:
    base_snapshot = get_or_capture_league_rank_snapshot(league_id, IRON_MAN_BASE_GW, force_refresh=True)
    current_snapshot = get_or_capture_league_rank_snapshot(league_id, 38, force_refresh=True)

    base_by_entry = {int(row["entry"]): row for row in base_snapshot}
    rows = []
    for current_row in current_snapshot:
        entry = int(current_row["entry"])
        base_row = base_by_entry.get(entry)
        if not base_row:
            continue
        start_rank = int(base_row["rank"])
        current_rank = int(current_row["rank"])
        rows.append(
            {
                "Manager": current_row.get("player_name", ""),
                "Team": current_row.get("entry_name", ""),
                "Rank Gain": start_rank - current_rank,
                "Rank After GW19": start_rank,
                "Current Rank": current_rank,
            }
        )

    df = pd.DataFrame(rows).sort_values("Rank Gain", ascending=False).reset_index(drop=True)
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

    return _ranked_award_entries(
        df,
        "Iron Man",
        ["iron_man", "iron_man_runner_up"],
        "Iron Man",
        lambda row: f"+{row['Rank Gain']} ranks, GW19 rank {row['Rank After GW19']} to final rank {row['Current Rank']}",
    )


def _lps_entries(league_id: int) -> List[Dict[str, Any]]:
    standings = fetch_all_league_standings(league_id)
    idx_by_entry = {int(row["entry"]): row for row in standings}
    survivors = set(idx_by_entry)
    elimination_log: Dict[int, List[Dict[str, Any]]] = {}

    for gw in range(1, 39):
        n_elim = elimination_schedule(gw)
        if n_elim == 0 or len(survivors) <= 1:
            elimination_log[gw] = []
            continue

        rows = []
        for entry_id in survivors:
            picks = fetch_entry_event_picks(entry_id, gw)
            points = compute_net_points(picks)
            standing = idx_by_entry.get(entry_id, {})
            rows.append(
                {
                    "entry": entry_id,
                    "Manager": standing.get("player_name", ""),
                    "Team": standing.get("entry_name", ""),
                    "OverallRank": int(standing.get("rank", 10**9)),
                    "OverallPoints": int(standing.get("total", 0)),
                    "RawPoints": int(points["raw_points"]),
                    "MinusPoints": int(points["minus_points"]),
                    "NetPoints": int(points["net_points"]),
                }
            )

        df = pd.DataFrame(rows).sort_values(
            by=["NetPoints", "OverallRank", "MinusPoints"],
            ascending=[True, True, False],
        ).reset_index(drop=True)

        threshold = df.iloc[n_elim - 1]["NetPoints"] if n_elim < len(df) else df.iloc[-1]["NetPoints"]
        bottom_block = df[df["NetPoints"] <= threshold].copy()
        strict_out = bottom_block[bottom_block["NetPoints"] < bottom_block["NetPoints"].max()].copy()
        remaining_slots = max(0, n_elim - len(strict_out))
        tied_group = bottom_block[bottom_block["NetPoints"] == bottom_block["NetPoints"].max()].copy()

        eliminated_rows = [row for _, row in strict_out.iterrows()]
        if remaining_slots > 0 and len(tied_group) > 0:
            tied_group = tied_group.sort_values(
                by=["OverallRank", "MinusPoints"],
                ascending=[False, False],
            ).reset_index(drop=True)
            if remaining_slots < len(tied_group):
                tied_group = pd.DataFrame(coin_toss_seeded(list(tied_group.to_dict("records")), gw))
            eliminated_rows.extend([tied_group.iloc[i] for i in range(min(remaining_slots, len(tied_group)))])

        eliminated_entries = []
        for row in eliminated_rows:
            entry_id = int(row["entry"])
            if entry_id not in survivors:
                continue
            survivors.remove(entry_id)
            eliminated_entries.append(dict(row))
        elimination_log[gw] = eliminated_entries

    entries = []
    third_last = elimination_log.get(37, [])
    second_last = elimination_log.get(38, [])
    winner_entry = next(iter(survivors)) if survivors else None

    if third_last:
        row = third_last[0]
        entries.append(
            _entry(
                row["Manager"],
                row["Team"],
                "Third Last Person Standing",
                f"Eliminated in GW37 with {row['NetPoints']} net points",
                "Third Last",
                PAYOUTS["third_last_person_standing"],
                "Last Person Standing",
            )
        )
    if second_last:
        row = second_last[0]
        entries.append(
            _entry(
                row["Manager"],
                row["Team"],
                "Second Last Person Standing",
                f"Eliminated in GW38 with {row['NetPoints']} net points",
                "Second Last",
                PAYOUTS["second_last_person_standing"],
                "Last Person Standing",
            )
        )
    if winner_entry:
        standing = idx_by_entry[winner_entry]
        entries.append(
            _entry(
                standing.get("player_name", ""),
                standing.get("entry_name", ""),
                "Last Person Standing",
                "Final survivor after GW38",
                "Winner",
                PAYOUTS["last_person_standing"],
                "Last Person Standing",
            )
        )
    return entries


def build_winners_ledger(league_id: int = LEAGUE_ID) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    entries.extend(_overall_entries(league_id))
    entries.extend(_gameweek_slammer_entries(league_id))
    entries.extend(_iron_man_entries(league_id))
    entries.extend(_lps_entries(league_id))

    wildcard_df = wildcard_wizard_table(league_id, 38)
    if not wildcard_df.empty:
        entries.extend(
            _ranked_award_entries(
                wildcard_df,
                "Wildcard Wizard",
                ["wildcard_wizard"],
                "Wildcard Wizard",
                lambda row: f"{row['Gameweek']}, {row['Points']} points",
            )
        )

    late_surge_df = late_surge_table(league_id, 38)
    if not late_surge_df.empty:
        entries.extend(
            _ranked_award_entries(
                late_surge_df,
                "Late Surge",
                ["late_surge"],
                "Late Surge",
                lambda row: f"{row['Total Points']} points from GW34-GW38",
            )
        )

    everest_df = everest_table(league_id, 38)
    if not everest_df.empty:
        entries.extend(
            _ranked_award_entries(
                everest_df,
                "Everest Award",
                ["everest"],
                "Everest Award",
                lambda row: f"{row['Gameweek']}, {row['Net Points']} net points without chips",
            )
        )

    for row in knockout_cup_rows(league_id):
        payout_key = {
            "Winner": "knockout_winner",
            "Runner-up": "knockout_runner_up",
            "Second Runner-up": "knockout_second_runner_up",
            "Third Runner-up": "knockout_third_runner_up",
        }.get(row["Award"])
        if not payout_key:
            continue
        entries.append(
            _entry(
                row["Manager"],
                row["Team"],
                "Knockout Cup",
                f"{row['Gameweek']}, {row['Points']} points",
                row["Award"],
                PAYOUTS[payout_key],
                "Knockout Cup",
            )
        )

    return {
        "season": "2025-26",
        "currency": "WC",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": league_id,
        "entries": entries,
    }


def save_winners_ledger(path: Path = LEDGER_PATH, league_id: int = LEAGUE_ID) -> Dict[str, Any]:
    ledger = build_winners_ledger(league_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
    return ledger


def load_winners_ledger(path: Path = LEDGER_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"season": "2025-26", "currency": "WC", "entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def ledger_dataframe(ledger: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(ledger.get("entries", []))
    if df.empty:
        return pd.DataFrame(columns=["manager_team", "award", "detail", "position", "wc"])
    return df.sort_values(["manager_team", "award", "detail"]).reset_index(drop=True)


def totals_dataframe(ledger: Dict[str, Any]) -> pd.DataFrame:
    df = ledger_dataframe(ledger)
    if df.empty:
        return pd.DataFrame(columns=["Manager-Team", "Awards Won", "Total WC"])
    grouped = (
        df.groupby("manager_team")
        .agg(**{"Awards Won": ("award", "count"), "Total WC": ("wc", "sum")})
        .reset_index()
        .rename(columns={"manager_team": "Manager-Team"})
        .sort_values(["Total WC", "Awards Won", "Manager-Team"], ascending=[False, False, True])
    )
    return grouped


def ledger_csv(df: pd.DataFrame) -> str:
    output = io.StringIO()
    df.to_csv(output, index=False, quoting=csv.QUOTE_MINIMAL)
    return output.getvalue()


def printable_ledger_html(manager_team: str, df: pd.DataFrame, total_wc: float) -> str:
    rows = "\n".join(
        f"<tr><td>{row['award']}</td><td>{row['detail']}</td><td>{row['position']}</td><td>{row['wc']} WC</td></tr>"
        for _, row in df.iterrows()
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{manager_team} - Whammy Coins Ledger</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #111; }}
    h1 {{ margin-bottom: 4px; }}
    .muted {{ color: #555; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
    th {{ background: #f3f3f3; }}
    .total {{ margin-top: 20px; font-size: 20px; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Whammy Coins Ledger</h1>
  <div class="muted">{manager_team}</div>
  <table>
    <thead>
      <tr><th>Award</th><th>Detail</th><th>Position</th><th>WC Won</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="total">Total WC Won: {total_wc} WC</div>
</body>
</html>"""
