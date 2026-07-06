"""Results page main area: title, animated map, ranked cards, show-more, export.

Without any detail expander opened the main area is designed to fit on a single
screen; the map shows the currently visible results and grows as 'Show more'
reveals additional routes.
"""

from __future__ import annotations

import streamlit as st

from backend.container import Container
from frontend.components import render_result_card
from frontend.export import build_results_pdf
from frontend.maps import MapRenderer
from shared.constants import TOP_N_RESULTS, TOP_VISIBLE_RESULTS


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

    # --- Ranked result cards -------------------------------------------
    for r in shown:
        render_result_card(r, response.task.value)
        st.write("")

    # --- Show more / Export --------------------------------------------
    c1, c2, _ = st.columns([1.2, 1.2, 3])
    with c1:
        can_show_more = visible < min(TOP_N_RESULTS, len(response.results))
        if st.button("Show more", use_container_width=True, disabled=not can_show_more):
            st.session_state.visible = min(TOP_N_RESULTS, len(response.results))
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
