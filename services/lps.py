# services/lps.py
from typing import Dict, List, Any, Tuple
import random

# --- Elimination schedule as provided ---
def elimination_schedule(gw: int) -> int:
    if gw == 1:
        return 0
    if 2 <= gw <= 6:
        return 2
    if 7 <= gw <= 27:
        return 3
    if 28 <= gw <= 35:
        return 2
    if 36 <= gw <= 38:
        return 1
    return 0

def coin_toss_seeded(items: List[Any], gw: int) -> List[Any]:
    """
    Deterministic shuffle per GW so results are stable/reproducible for ties that go that deep.
    """
    rng = random.Random(gw * 10_007)  # stable seed from GW
    items_copy = items[:]
    rng.shuffle(items_copy)
    return items_copy

def sort_key_for_bottom_cut(
    net_points: int,
    overall_rank: int,
    minus_points: int
) -> Tuple[int, int, int]:
    """
    Sort ascending by elimination priority:
    1) Fewest net points (worse first)
    2) Worst overall rank (bigger number is worse) -> descending => use negative sign trick by returning -rank? No:
       We want worse first, so key should put larger rank earlier => use rank directly but invert overall sort sense by providing it as (+rank)
    3) More minus points (worse first)
    """
    return (net_points, overall_rank, -(-minus_points))  # same as (net_points, overall_rank, minus_points)

# NOTE on goals scored/conceded tie-breakers:
# We skip them for now because they require per-player live stats aggregation.
# If ties remain after minus_points, we fall back to deterministic coin toss.
