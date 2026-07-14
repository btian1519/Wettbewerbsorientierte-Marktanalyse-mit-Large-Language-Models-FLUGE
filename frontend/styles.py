"""Injected CSS for the Streamlit UI, derived from :mod:`frontend.theme`.

Styling is centralised in one function so the look-and-feel stays consistent and
is trivial to tweak. Streamlit's semantic button kinds (``primary`` / secondary)
are used to distinguish the green action buttons from the teal pill buttons.
"""

from __future__ import annotations

import streamlit as st

from frontend.theme import COLORS as C


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = f"""
<style>
/* ---- Layout -------------------------------------------------------- */
.block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1200px; }}
#MainMenu, footer {{ visibility: hidden; }}

/* ---- Typography ---------------------------------------------------- */
.fs-title {{ font-size: 3.2rem; font-weight: 800; text-align: center;
             color: {C['text_dark']}; margin: 0.4rem 0 0.2rem 0; letter-spacing: -1px; }}
.fs-subtitle {{ font-size: 1.25rem; text-align: center; color: #333; margin-bottom: 2.2rem; }}
.fs-hint {{ text-align: center; color: #555; font-style: italic; margin-top: 1.4rem; }}
.fs-results-title {{ font-size: 1.9rem; font-weight: 800; color: {C['text_dark']}; margin: .2rem 0 1rem; }}
.fs-section-title {{ font-size: 1.5rem; font-weight: 800; color: {C['text_dark']}; text-align: left; margin: .2rem 0 1rem; }}

/* ---- Buttons ------------------------------------------------------- */
.stButton > button {{
    border-radius: 30px; font-weight: 700; border: none; padding: .55rem 1.2rem;
    transition: filter .15s ease;
}}
.stButton > button[kind="secondary"] {{
    background: {C['teal']}; color: white;
}}
.stButton > button[kind="secondary"]:hover {{ filter: brightness(1.1); color: white; }}
.stButton > button[kind="primary"] {{
    background: {C['green']}; color: {C['green_text']}; box-shadow: 0 2px 6px rgba(0,0,0,.15);
}}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.03); color: {C['green_text']}; }}

/* ---- Dropdowns (identical on start page & sidebar) ----------------- */
div[data-baseweb="select"] > div {{
    background: {C['teal']}; border-radius: 30px; border: none; color: white;
    font-weight: 700; min-height: 52px;
    display: flex; align-items: center;              /* vertically centre value */
}}
div[data-baseweb="select"] svg {{ color: white; fill: white; }}
div[data-baseweb="select"] div {{ color: white; }}
/* Non-editable: user may only pick from the list, not type or search. */
div[data-baseweb="select"] input {{
    pointer-events: none; caret-color: transparent; cursor: pointer;
}}
div[data-baseweb="select"] > div {{ cursor: pointer; }}

/* ---- Result cards -------------------------------------------------- */
.fs-card {{
    background: linear-gradient(180deg, {C['card']} 0%, {C['card_dark']} 100%);
    border-radius: 16px; padding: 14px 18px; color: white;
    display: flex; align-items: center; gap: 16px; box-shadow: 0 3px 8px rgba(0,0,0,.18);
}}
.fs-rank {{ background: white; color: {C['card']}; width: 38px; height: 38px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; flex: 0 0 auto; }}
.fs-route {{ font-size: 1.5rem; font-weight: 800; flex: 0 0 auto; min-width: 150px; letter-spacing: .5px; }}
.fs-chip {{ background: white; color: {C['card']}; border-radius: 10px; padding: 6px 14px; font-weight: 800;
            text-align: center; }}
.fs-chip .lbl {{ display:block; font-size: .62rem; font-weight: 700; color:#5a7c89; letter-spacing:.5px; }}
.fs-chip .val {{ display:block; font-size: 1.0rem; }}
.fs-spacer {{ flex: 1 1 auto; }}

/* ---- Detail panel -------------------------------------------------- */
.fs-detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 26px; }}
.fs-detail-grid .k {{ color:#5a7c89; font-size:.82rem; }}
.fs-detail-grid .v {{ font-weight: 700; text-align: right; color: {C['text_dark']}; }}
.fs-detail-h {{ font-weight:800; color:{C['teal']}; margin:.2rem 0 .4rem; }}
.fs-airport .row {{ display:flex; justify-content:space-between; gap:14px; padding:1px 0; }}
.fs-airport .k {{ color:#5a7c89; font-size:.8rem; }}
.fs-airport .v {{ font-weight:700; color:{C['text_dark']}; font-size:.82rem; text-align:right; }}
.fs-airport .apt-name {{ font-weight:700; color:{C['text_dark']}; font-size:.9rem; }}
.fs-airport .apt-loc {{ color:#5a7c89; font-size:.82rem; }}
.fs-airport .apt-region {{ color:#5a7c89; font-size:.8rem; }}

/* ---- Sidebar ------------------------------------------------------- */
section[data-testid="stSidebar"] {{ background: {C['grey_sidebar']}; }}
section[data-testid="stSidebar"] .fs-side-title {{ font-size:1.6rem; font-weight:800; text-align:center;
            color:{C['text_dark']}; margin:.2rem 0 1rem; }}
</style>
"""
