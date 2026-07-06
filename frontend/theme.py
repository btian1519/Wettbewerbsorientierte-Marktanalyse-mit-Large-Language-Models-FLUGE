"""Central design tokens (colours, radii) shared by CSS, cards and the map.

Keeping the palette in one Python dict means the injected Streamlit CSS, the
result cards and the Canvas map all stay visually consistent, and a rebrand is a
one-file change.
"""

from __future__ import annotations

COLORS: dict[str, str] = {
    "teal": "#1a6d8e",
    "teal_dark": "#134e66",
    "teal_hover": "#20819f",
    "card": "#1d6a8a",
    "card_dark": "#155a77",
    "green": "#aee3a1",
    "green_dark": "#8ed67f",
    "green_text": "#2f6f2a",
    "grey_sidebar": "#d9d9d9",
    "grey_panel": "#eef0f1",
    "white": "#ffffff",
    "text_dark": "#12303b",
    # Map palette
    "ocean": "#eef4f7",
    "land": "#cbd8df",
    "land_active": "#9cc3d4",
    "route": "#123f56",
    "plane": "#8ed67f",
    "airport_dot": "#9aa7ad",
    "airport_hl": "#f2a71b",
}

RADIUS = "26px"
