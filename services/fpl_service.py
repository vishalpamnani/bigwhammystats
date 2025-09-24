# services/fpl_service.py
import requests
from typing import Dict, List, Any, Tuple
import streamlit as st

# --- CONFIG ---
# Adjust TTL if needed (seconds). Lower during development, higher in production.
CACHE_TTL = 600  # 10 minutes

@st.cache_data(ttl=300, show_spinner=False)
def fetch_bootstrap_static() -> Dict[str, Any]:
    """
    Fetches the FPL bootstrap-static payload (events, teams, elements, etc.).
    We'll use the 'events' list to determine which GWs are finished.
    """
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# -------- League / standings (handles pagination to fetch >50 entries) --------
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_all_league_standings(league_id: int) -> List[Dict[str, Any]]:
    """
    Returns full classic-league standings across all pages.
    Each item contains: entry, entry_name, player_name, rank, total, etc.
    """
    results: List[Dict[str, Any]] = []
    page = 1
    while True:
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        page_results = data.get("standings", {}).get("results", [])
        results.extend(page_results)
        has_next = data.get("standings", {}).get("has_next", False)
        if not has_next:
            break
        page += 1
    return results

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def standings_index_by_entry(league_id: int) -> Dict[int, Dict[str, Any]]:
    """
    Convenience index: entry_id -> standing row (for quick lookups like overall rank/total).
    """
    items = fetch_all_league_standings(league_id)
    return {row["entry"]: row for row in items}

# -------- GW picks / points for a single entry --------
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_entry_event_picks(entry_id: int, gw: int) -> Dict[str, Any]:
    """
    Raw event data for an entry for GW (includes entry_history: points, event_transfers_cost, etc.)
    """
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def compute_net_points(entry_event: Dict[str, Any]):
    """
    Compute raw, minus and net points for an entry's GW event.

    Note: different FPL endpoints / payloads can be inconsistent in whether
    'entry_history["points"]' is raw or net. For your league data the API
    sends the RAW points in `entry_history["points"]`, and the hits are
    in `entry_history["event_transfers_cost"]`.

    So we interpret:
      RawPoints  = entry_history["points"]
      MinusPoints = event_transfers_cost (positive number)
      NetPoints  = RawPoints - MinusPoints

    This function intentionally returns integers and is defensive against
    missing fields.
    """
    hist = entry_event.get("entry_history", {}) or {}
    # Treat `points` as RAW points (before hits)
    raw_points = int(hist.get("points", 0))
    minus_points = int(hist.get("event_transfers_cost", 0))  # positive
    net_points = raw_points - minus_points

    return {
        "raw_points": raw_points,
        "minus_points": minus_points,
        "net_points": net_points,
    }
# temp change to force redeploy
