"""Streamlit presentation layer.

Structure mirrors the brief: ``pages`` (start / results), ``components``
(reusable widgets), ``sidebar``, ``maps`` (the animated Canvas map) and
``export`` (PDF). The layer only talks to the backend through the injected
:class:`~backend.container.Container` — no business logic lives here.
"""
