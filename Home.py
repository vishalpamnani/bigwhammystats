# Home.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.fpl_service import fetch_all_league_standings, fetch_bootstrap_static
from services.lps import elimination_schedule
from utils import add_logo_fixed

st.set_page_config(page_title="Big Whammy - Home", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

LEAGUE_ID = 1124151

st.title("🏡 Welcome to The Big Whammy!")

# Intro text
st.markdown("""  
Track your weekly awards 🏆, eliminations ❌, and overall table 📊 all in one place.
""")

# League summary
with st.spinner("Fetching league summary…"):
    standings = fetch_all_league_standings(LEAGUE_ID)

st.subheader("📊 League Summary")
st.write(f"**Total Managers:** {len(standings)}")
st.write(f"**Current Leader:** {standings[0]['player_name']} ({standings[0]['entry_name']})")
st.write(f"**Leader Points:** {standings[0]['total']}")

# --- LPS schedule summary ---
bs = fetch_bootstrap_static()
events = bs.get("events", []) or []

# find next GW with eliminations (after latest completed GW)
now_utc = datetime.now(timezone.utc)
current_gw = None
for ev in events:
    if ev.get("finished"):
        current_gw = ev["id"]
next_gw = (current_gw or 0) + 1

if next_gw <= 38 and elimination_schedule(next_gw) > 0:
    st.write(f"**LPS Schedule:** {elimination_schedule(next_gw)} eliminations in GW {next_gw}")
else:
    st.write("**LPS Schedule:** No eliminations scheduled.")

# --- Next Deadline (IST) ---
try:
    next_event = None
    for ev in events:
        dt_str = ev.get("deadline_time")
        if not dt_str:
            continue
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt > now_utc:
            next_event = ev
            break

    if next_event:
        dt_utc = datetime.fromisoformat(next_event["deadline_time"].replace("Z", "+00:00"))
        dt_ist = dt_utc.astimezone(ZoneInfo("Asia/Kolkata"))
        ist_str = dt_ist.strftime("%a, %d %b %Y • %I:%M %p IST")

        delta = dt_utc - now_utc
        total_seconds = int(delta.total_seconds())
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            countdown = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            countdown = f"{hours}h {minutes}m"
        else:
            countdown = f"{minutes}m"

        st.write(f"**Next Deadline:** {ist_str} — starts in {countdown}")
    else:
        st.write("**Next Deadline:** No upcoming deadline found.")
except Exception:
    st.write("**Next Deadline:** unavailable.")

# Navigation buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏅 Gameweek Slammers"):
        st.switch_page("pages/2_Gameweek_Slammers.py")
with col2:
    if st.button("📊 Standings"):
        st.switch_page("pages/1_Big_Whammy_Table.py")
with col3:
    if st.button("💀 Last Person Standing"):
        st.switch_page("pages/3_Last_Person_Standing.py")
