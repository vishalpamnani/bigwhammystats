# pages/1_Big_Whammy_Table.py
import streamlit as st
import pandas as pd

from services.fpl_service import fetch_all_league_standings
from utils import add_logo_fixed


# --- CONFIG ---
st.set_page_config(page_title="Big Whammy Dashboard", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151  # <-- replace with your actual league id

st.title("📊 Big Whammy League Standings")

# Fetch all league standings (all pages)
with st.spinner("Loading full league standings…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

# Build DataFrame
df = pd.DataFrame([{
    "Overall Rank": m["rank"],
    "Manager": m["player_name"],
    "Team": m["entry_name"],
    "Overall Points": m["total"]
} for m in standings])

# Sort, reset index, and drop the index column
df = df.sort_values("Overall Rank").reset_index(drop=True)

# ✅ Display without index
st.dataframe(df, use_container_width=True, hide_index=True)
