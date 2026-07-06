"""Data ingestion layer.

Two families of sources, both behind Protocols in :mod:`ingestion.interfaces`:

* **Master data** — airports & airlines — loaded from the mandated external
  files (``AIRPORTS.xlsx`` / ``AIRLINES.py``).
* **Supply/demand** — weekly route facts — produced today by the demo generator
  and, in future, by live APIs (interfaces prepared in ``api_interfaces``).

Everything downstream depends only on the interfaces, so swapping demo data for
a real API is an injection change, not a rewrite.
"""
