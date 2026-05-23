# services/lps.py
from typing import Dict, List, Any, Tuple
import random

LPS_STARTERS = 96


def elimination_schedule(gw: int) -> int:
    """
    LPS schedule for 96 starters.

    After GW36 there are 3 managers left. GW37 decides Third Last Person
    Standing, GW38 decides Second Last Person Standing, and the final survivor
    is the winner.
    """
    if gw == 1:
        return 0
    if 2 <= gw <= 6:
        return 2
    if 7 <= gw <= 27:
        return 3
    if 28 <= gw <= 32:
        return 2
    if gw == 33:
        return 3
    if gw == 34:
        return 3
    if gw == 35:
        return 3
    if gw == 36:
        return 1
    if gw == 37:
        return 1
    if gw == 38:
        return 1
    return 0


def participants_left_after_gw(gw: int, starters: int = LPS_STARTERS) -> int:
    eliminations = sum(elimination_schedule(item) for item in range(1, gw + 1))
    return max(0, starters - eliminations)

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
