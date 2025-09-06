# services/fpl_service.py
import requests
from typing import Dict, List, Any, Tuple
import streamlit as st

# --- CONFIG ---
# Adjust TTL if needed (seconds). Lower during development, higher in production.
CACHE_TTL = 600  # 10 minutes

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
    Returns a dict with net_points, minus_points, raw_points.
    FPL API: entry_history["points"] is NET (after hits).
    """
    hist = entry_event.get("entry_history", {}) or {}
    net_points = int(hist.get("points", 0))                 # after hits
    minus_points = int(hist.get("event_transfers_cost", 0)) # positive
    raw_points = net_points + minus_points                  # before hits

    return {
        "net_points": net_points,
        "minus_points": minus_points,
        "raw_points": raw_points,
    }


