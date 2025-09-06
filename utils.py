# utils.py
import streamlit as st
import base64

def add_logo_fixed(logo_path: str = "TBWlogo.png", width: int = 120, top: int = 20, left: int = 16):
    """
    Render a fixed-position logo at the top-left (visually above the Streamlit nav).
    Embeds image as base64 so it always works.
    """
    # Read and encode the image as base64
    with open(logo_path, "rb") as f:
        img_data = f.read()
    encoded = base64.b64encode(img_data).decode()

    st.markdown(
        f"""
        <style>
        .big-whammy-logo {{
            position: fixed;
            top: {top}px;
            left: {left}px;
            width: {width}px;
            z-index: 10000;
        }}
        @media (max-width: 880px) {{
            .big-whammy-logo {{ display: none !important; }}
        }}
        </style>

        <div class="big-whammy-logo">
            <img src="data:image/png;base64,{encoded}" style="width:100%; height:auto; display:block;" />
        </div>
        """,
        unsafe_allow_html=True,
    )
