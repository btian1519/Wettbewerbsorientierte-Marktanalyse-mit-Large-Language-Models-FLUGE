"""Reusable Streamlit widgets (input dropdowns, result cards)."""

from frontend.components.inputs import (
    airline_dropdown,
    scope_dropdown,
    task_dropdown,
)
from frontend.components.result_card import render_result_card

__all__ = ["airline_dropdown", "scope_dropdown", "task_dropdown", "render_result_card"]
