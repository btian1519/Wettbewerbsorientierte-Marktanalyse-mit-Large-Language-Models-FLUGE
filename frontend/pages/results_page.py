"""Results page main area: title, animated map, ranked cards, show-more, export.

Without any detail expander opened the main area is designed to fit on a single
screen; the map shows the currently visible results and grows as 'Show more'
reveals additional routes, collapsing again with 'Show less'.
"""

from __future__ import annotations

import streamlit as st

from backend.container import Container
from frontend.components import render_result_card
from frontend.export import build_results_pdf
from frontend.maps import MapRenderer
from shared.constants import SHOW_MORE_MIN_RESULTS, TOP_N_RESULTS, TOP_VISIBLE_RESULTS


def render_results_page(container: Container, map_renderer: MapRenderer) -> None:
    response = st.session_state.get("response")
    if response is None:
        st.info("No analysis yet — configure the scope in the sidebar and press Refresh.")
        return

    st.markdown(f'<div class="fs-results-title">{response.title}</div>', unsafe_allow_html=True)

    if not response.results:
        st.warning("No routes matched this scope and the current filters. Try relaxing the filters.")
        return

    visible = st.session_state.get("visible", TOP_VISIBLE_RESULTS)
    shown = response.results[:visible]

    # --- Map (top third) ------------------------------------------------
    scope_airports = container.catalog_service.airports_for_scope(response.scope)
    map_height = st.session_state.get("map_height", 360)
    map_renderer.render(response.scope, scope_airports, shown, height=map_height)

    st.write("")

    # --- Section subheading (shown for every mode) ---------------------
    st.markdown(
        '<div class="fs-section-title">Recommended priorities...</div>',
        unsafe_allow_html=True,
    )

    # --- Ranked result cards -------------------------------------------
    for r in shown:
        render_result_card(r, response.task.value)
        st.write("")

    # --- Show more / less / Export -------------------------------------
    c1, c2, _ = st.columns([1.2, 1.2, 3])
    with c1:
        # Single toggle driven solely by `visible` (the existing display state):
        #   collapsed (top 3)  -> "Show more"  -> expand to top-N
        #   expanded (top N)   -> "Show less"  -> collapse back to top 3
        # Only the display changes; no new results are computed or loaded, and the
        # map stays in sync because it renders response.results[:visible].
        expanded_visible = min(TOP_N_RESULTS, len(response.results))
        has_extra = len(response.results) >= SHOW_MORE_MIN_RESULTS
        extended = visible > TOP_VISIBLE_RESULTS
        # Disabled only when fewer than SHOW_MORE_MIN_RESULTS (4) results qualify,
        # i.e. there is nothing beyond the top 3 to reveal.
        if st.button(
            "Show less" if extended else "Show more",
            use_container_width=True,
            disabled=not has_extra,
        ):
            st.session_state.visible = TOP_VISIBLE_RESULTS if extended else expanded_visible
            st.rerun()
    with c2:
        airline = container.catalog_service.airline(response.airline_iata)
        pdf_bytes = build_results_pdf(response, airline.name if airline else response.airline_iata)
        st.download_button(
            "Export",
            data=pdf_bytes,
            file_name=f"flightscope_{response.scope.replace('/', '-')}_{response.week}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
