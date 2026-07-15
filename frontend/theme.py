"""Central design tokens (colours, radii) shared by CSS, cards and the map.

Keeping the palette in one Python dict means the injected Streamlit CSS, the
result cards and the Canvas map all stay visually consistent, and a rebrand is a
one-file change.
"""

from __future__ import annotations

# Highlight orange — single source of truth for the highlighted airport markers.
PRIMARY_ORANGE = "#f2a71b"
# Shared primary green — single source of truth for the animated plane icons AND
# the primary action buttons (Analyze! / Refresh / Sync Now), so they read as one
# family. Bright, modern emerald with a slightly darker companion for hover.
PRIMARY_GREEN = "#2ecc71"
PRIMARY_GREEN_HOVER = "#27ae60"

COLORS: dict[str, str] = {
    "teal": "#1a6d8e",
    "teal_dark": "#134e66",
    "teal_hover": "#20819f",
    "card": "#1d6a8a",
    "card_dark": "#155a77",
    "green": "#aee3a1",
    "green_dark": "#8ed67f",
    "green_text": "#2f6f2a",
    # Shared primary green (plane icons + primary action buttons) and its hover.
    "primary_green": PRIMARY_GREEN,
    "primary_green_hover": PRIMARY_GREEN_HOVER,
    "grey_sidebar": "#d9d9d9",
    "grey_panel": "#eef0f1",
    "white": "#ffffff",
    "text_dark": "#12303b",
    # Map palette
    "ocean": "#eef4f7",
    "land": "#cbd8df",
    "land_active": "#9cc3d4",
    "route": "#123f56",
    "plane": PRIMARY_GREEN,
    "airport_dot": "#9aa7ad",
    "airport_hl": PRIMARY_ORANGE,
}

RADIUS = "26px"
