# Home.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.fpl_service import fetch_all_league_standings, fetch_bootstrap_static
from services.lps import elimination_schedule, participants_left_after_gw
from services.articles import article_url, format_article_date, load_articles
from utils import add_logo_fixed
from config import LEAGUE_ID

st.set_page_config(page_title="Big Whammy - Home", layout="wide")

add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

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

# --- LPS schedule summary ---
bs = fetch_bootstrap_static()
events = bs.get("events", []) or []
season_finished = max((event.get("id", 0) for event in events if event.get("finished")), default=0) >= 38

leader_label = "Winner" if season_finished else "Current Leader"
points_label = "Winning Points" if season_finished else "Leader Points"
st.write(f"**{leader_label}:** {standings[0]['player_name']} ({standings[0]['entry_name']})")
st.write(f"**{points_label}:** {standings[0]['total']}")

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

with st.expander("View full LPS elimination schedule"):
    def lps_remaining_label(gw: int) -> str:
        remaining = participants_left_after_gw(gw)
        if gw == 36:
            return f"{remaining} - 🥉 Third Last Person Standing race"
        if gw == 37:
            return f"{remaining} - 🥈 Second Last Person Standing race"
        if gw == 38:
            return f"{remaining} - 🥇 Last Person Standing"
        return str(remaining)

    schedule_df = pd.DataFrame(
        [
            {
                "Gameweek": f"GW {gw}",
                "Eliminations": elimination_schedule(gw),
                "Participants Left": lps_remaining_label(gw),
            }
            for gw in range(1, 39)
        ]
    )
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)

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
st.subheader("Explore")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📊 Standings", use_container_width=True):
        st.switch_page("pages/1_Big_Whammy_Table.py")
with col2:
    if st.button("🏅 Gameweek Slammers", use_container_width=True):
        st.switch_page("pages/2_Gameweek_Slammers.py")
with col3:
    if st.button("💀 Last Person Standing", use_container_width=True):
        st.switch_page("pages/3_Last_Person_Standing.py")

col4, col5, col6 = st.columns(3)
with col4:
    if st.button("💪 Iron Man", use_container_width=True):
        st.switch_page("pages/4_Iron_Man.py")
with col5:
    if st.button("🃏 Wildcard Wizard", use_container_width=True):
        st.switch_page("pages/5_Wildcard_Wizard.py")
with col6:
    if st.button("🚀 Late Surge", use_container_width=True):
        st.switch_page("pages/6_Late_Surge.py")

col7, col8, _ = st.columns(3)
with col7:
    if st.button("🏔️ Everest Award", use_container_width=True):
        st.switch_page("pages/7_Everest_Award.py")
with col8:
    if st.button("🏆 Knockout Cup", use_container_width=True):
        st.switch_page("pages/8_Knockout_Cup.py")

if st.button("🏦 Winners' Tally", use_container_width=True):
    st.switch_page("pages/9_Winners_Tally.py")

# --- Latest Articles ---
articles = load_articles()
if articles:
    st.subheader("📝 Latest Articles")
    for article in articles[:3]:
        with st.container(border=True):
            st.markdown(f"### [{article.title}]({article_url(article.slug)})")
            st.caption(
                f"{format_article_date(article)} · {article.author} · {article.category}"
            )
            if article.summary:
                st.write(article.summary)
