import streamlit as st

from services.winners_ledger import (
    ledger_csv,
    ledger_dataframe,
    load_winners_ledger,
    printable_ledger_html,
    totals_dataframe,
)
from utils import add_logo_fixed

st.set_page_config(page_title="Winners' Tally", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

st.title("🏦 Whammy Coins Ledger")
st.caption("Final locked winners' tally for The Big Whammy 2025-26.")

ledger = load_winners_ledger()
df = ledger_dataframe(ledger)
totals_df = totals_dataframe(ledger)

if df.empty:
    st.info("Winners' ledger has not been generated yet.")
    st.stop()

total_wc = int(df["wc"].sum())
unique_winners = int(df["manager_team"].nunique())
top_row = totals_df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Total WC Awarded", f"{total_wc:,} WC")
col2.metric("Winning Entries", unique_winners)
col3.metric("Top Ledger", f"{top_row['Total WC']:,} WC")
st.caption(f"Top Ledger: {top_row['Manager-Team']}")

winner_options = ["All winners", *totals_df["Manager-Team"].tolist()]
selected = st.selectbox("Filter by manager-team", winner_options)

if selected == "All winners":
    st.subheader("All Award Entries")
    display_df = df.rename(
        columns={
            "manager_team": "Manager-Team",
            "award": "Award",
            "detail": "Detail",
            "position": "Position",
            "wc": "WC Won",
        }
    )[["Manager-Team", "Award", "Detail", "Position", "WC Won"]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.subheader("Totals by Manager-Team")
    st.dataframe(totals_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download full ledger CSV",
        data=ledger_csv(display_df),
        file_name="big_whammy_winners_ledger_2025_26.csv",
        mime="text/csv",
    )
else:
    filtered = df[df["manager_team"] == selected].copy()
    selected_total = filtered["wc"].sum()

    st.subheader(selected)
    st.metric("Total WC Won", f"{int(selected_total):,} WC")

    display_df = filtered.rename(
        columns={
            "award": "Award",
            "detail": "Detail",
            "position": "Position",
            "wc": "WC Won",
        }
    )[["Award", "Detail", "Position", "WC Won"]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv_col, html_col = st.columns(2)
    with csv_col:
        st.download_button(
            "Download CSV",
            data=ledger_csv(display_df),
            file_name=f"{selected.replace(' ', '_').replace('/', '-')}_ledger.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with html_col:
        st.download_button(
            "Download printable HTML",
            data=printable_ledger_html(selected, filtered, selected_total),
            file_name=f"{selected.replace(' ', '_').replace('/', '-')}_ledger.html",
            mime="text/html",
            use_container_width=True,
        )

st.markdown(
    """
**Note:** WC means Whammy Coins. This ledger is locked from final season award results.
"""
)

# redeploy trigger