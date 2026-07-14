"""Extended AIRPORTS import: cell cleaning + detail-block rendering."""

from __future__ import annotations

import re

from frontend.components.result_card import _airport_block
from ingestion.master_data import _clean_text


def test_clean_text_valid_and_unicode():
    assert _clean_text("  Berlin  ") == "Berlin"          # stripped
    assert _clean_text("İstanbul") == "İstanbul"          # unicode preserved


def test_clean_text_empty_and_errors_become_none():
    assert _clean_text("") is None
    assert _clean_text("   ") is None
    assert _clean_text(None) is None
    assert _clean_text(float("nan")) is None
    for err in ("#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NAME?"):
        assert _clean_text(err) is None
    for placeholder in ("N/A", "None", "null", "Unknown", "nan"):
        assert _clean_text(placeholder) is None


def _lines(block: str) -> list[str]:
    return re.findall(r">([^<]+)<", block)


def test_airport_block_full_structure_and_order():
    block = _airport_block("Barcelona-El Prat Airport", "BCN", "Barcelona", "Spain", "Europe")
    assert _lines(block) == ["Barcelona-El Prat Airport (BCN)", "Barcelona, Spain", "Europe"]


def test_airport_block_omits_missing_without_placeholders():
    # No name/city/country -> only IATA + region.
    assert _lines(_airport_block(None, "ZZZ", None, None, "Europe")) == ["ZZZ", "Europe"]
    # City present, country missing.
    assert _lines(_airport_block("X Apt", "XXX", "Madrid", None, "Europe")) == ["X Apt (XXX)", "Madrid", "Europe"]
    # Country present, city missing.
    assert _lines(_airport_block("X Apt", "XXX", None, "Spain", "Europe")) == ["X Apt (XXX)", "Spain", "Europe"]
