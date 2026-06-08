# pages/1_Big_Whammy_Table.py
import streamlit as st
import pandas as pd

from services.fpl_service import fetch_all_league_standings
from utils import add_logo_fixed
from config import LEAGUE_ID


# --- CONFIG ---
st.set_page_config(page_title="Big Whammy Dashboard", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("📊 Big Whammy League Standings")


def season_award(rank: int) -> str:
    awards = {
        1: "🥇 Manager of the Season",
        2: "🥈 2nd Place",
        3: "🥉 3rd Place",
        4: "4th Place",
        5: "Europa 1",
        6: "Europa 2",
        20: "⚽ #20 - Diogo Jota Tribute Award ❤️",
    }
    return awards.get(rank, "")

# Fetch all league standings (all pages)
with st.spinner("Loading full league standings…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

# Build DataFrame
df = pd.DataFrame([{
    "Overall Rank": m["rank"],
    "Award": season_award(int(m["rank"])),
    "Manager": m["player_name"],
    "Team": m["entry_name"],
    "Overall Points": m["total"]
} for m in standings])

# Sort, reset index, and drop the index column
df = df.sort_values("Overall Rank").reset_index(drop=True)

# ✅ Display without index
st.dataframe(df, use_container_width=True, hide_index=True)

tribute_winner = df[df["Overall Rank"] == 20]
if not tribute_winner.empty:
    winner = tribute_winner.iloc[0]
    st.subheader("⚽ Diogo Jota Tribute Award")
    st.markdown(
        f"""
**{winner["Manager"]} — {winner["Team"]}**  
Final Big Whammy rank: **20** · Overall points: **{winner["Overall Points"]}**

_Forever 20. Gone too soon, never forgotten._ ❤️
"""
    )
