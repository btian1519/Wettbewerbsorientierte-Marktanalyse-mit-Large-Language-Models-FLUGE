"""Colour palette and CSS injection for the modernised FlightScope look.

The palette is derived from the mockups (deep teal controls, soft green
primary actions, light-grey sidebar) but modernised with flatter surfaces,
rounded corners and consistent spacing. Map layer colours are exposed as RGB
lists for pydeck.
"""

from __future__ import annotations

import streamlit as st

# Brand palette (hex, for CSS).
TEAL = "#15607C"
TEAL_DARK = "#0F4A5F"
GREEN = "#8FCB6B"
GREEN_DARK = "#6FA84A"
SIDEBAR_BG = "#EDEFF1"
SURFACE = "#FFFFFF"
TEXT = "#1F2A33"
MUTED = "#5B6B76"

# Map layer colours (RGB / RGBA, for pydeck).
ARC_SOURCE_RGB = [21, 96, 124]
ARC_TARGET_RGB = [143, 203, 107]
MARKER_RGB = [15, 74, 95]
AIRCRAFT_RGB = [111, 168, 74]
HIGHLIGHT_RGB = [230, 126, 34]
LABEL_RGB = [31, 42, 51]

_CSS = f"""
<style>
    /* Base surfaces */
    section[data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG};
    }}
    .fs-title {{
        text-align: center;
        font-size: 3.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: {TEXT};
        margin: 1.2rem 0 0.2rem 0;
    }}
    .fs-subtitle {{
        text-align: center;
        font-size: 1.15rem;
        color: {MUTED};
        margin-bottom: 2.4rem;
    }}
    .fs-hint {{
        text-align: center;
        color: {MUTED};
        font-size: 0.9rem;
        margin-top: 1.2rem;
    }}

    /* Buttons: rounded pill style. */
    .stButton > button {{
        border-radius: 999px;
        border: none;
        padding: 0.55rem 1.2rem;
        font-weight: 700;
        transition: transform 0.05s ease, filter 0.15s ease;
    }}
    .stButton > button:hover {{ filter: brightness(1.05); }}
    .stButton > button:active {{ transform: translateY(1px); }}

    /* Primary (GO / Refresh): green. */
    .stButton > button[kind="primary"] {{
        background-color: {GREEN};
        color: {TEAL_DARK};
    }}
    .stButton > button[kind="primary"]:hover {{ background-color: {GREEN_DARK}; }}

    /* Recommendation card container. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-card-marker) {{
        background: linear-gradient(180deg, {TEAL} 0%, {TEAL_DARK} 100%);
        border: none;
        border-radius: 16px;
        padding: 0.4rem 0.6rem;
        color: #FFFFFF;
    }}
    .fs-rank-badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.4rem; height: 2.4rem;
        border-radius: 50%;
        background: #FFFFFF;
        color: {TEAL_DARK};
        font-weight: 800;
        font-size: 1.05rem;
    }}
    .fs-route {{ font-size: 1.5rem; font-weight: 800; color: #FFFFFF; }}
    .fs-pill {{
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border-radius: 999px;
        padding: 0.15rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 700;
        color: #FFFFFF;
    }}
    .fs-pill--match {{ background: {GREEN}; color: {TEAL_DARK}; }}
    .fs-kpi-label {{ font-size: 0.72rem; text-transform: uppercase; opacity: 0.8; }}
    .fs-kpi-value {{ font-size: 1.05rem; font-weight: 700; }}
    #MainMenu, footer {{ visibility: hidden; }}
</style>
"""


def inject() -> None:
    """Inject the FlightScope CSS once per page render."""
    st.markdown(_CSS, unsafe_allow_html=True)
