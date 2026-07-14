"""Master-data loaders for the two mandated source files.

Hard project constraint: airlines come *only* from ``AIRLINES.py`` and airports
*only* from ``AIRPORTS.xlsx``. Nothing is hard-coded here beyond how to read
those files.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from shared.config import Settings, get_settings
from shared.geo import continent_from_coords
from shared.logging_config import get_logger
from shared.utils import extract_iata

log = get_logger("ingestion.master_data")


class FileMasterDataSource:
    """Loads airports from Excel and airlines from the Python data file."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------ #
    # Airlines
    # ------------------------------------------------------------------ #
    def load_airlines(self) -> list[dict]:
        path: Path = self._settings.airlines_file
        if not path.exists():
            raise FileNotFoundError(f"AIRLINES file not found: {path}")
        airlines_dict = self._import_airlines_dict(path)
        rows: list[dict] = []
        for iata, meta in airlines_dict.items():
            rows.append(
                {
                    "iata": iata,
                    "name": meta["name"],
                    "base": meta["base"],
                    "region": meta["region"],
                    "base_iata": extract_iata(meta.get("base", "")),
                }
            )
        log.info("Parsed %d airlines from %s", len(rows), path.name)
        return rows

    @staticmethod
    def _import_airlines_dict(path: Path) -> dict:
        spec = importlib.util.spec_from_file_location("_airlines_data", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module spec from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "AIRLINES"):
            raise KeyError("AIRLINES.py must define a top-level AIRLINES dict")
        return dict(module.AIRLINES)

    # ------------------------------------------------------------------ #
    # Airports
    # ------------------------------------------------------------------ #
    def load_airports(self) -> list[dict]:
        path: Path = self._settings.airports_file
        if not path.exists():
            raise FileNotFoundError(f"AIRPORTS file not found: {path}")

        df = pd.read_excel(path, sheet_name=0)
        col = {c.lower(): c for c in df.columns}
        iata_col = self._find(col, "iata")
        cont_col = self._find(col, "continent")
        lon_col = self._find(col, "ngengrad", "lon", "long")  # German "Längengrad"
        lat_col = self._find(col, "reitengrad", "lat")  # German "Breitengrad"
        name_col = self._find(col, "airport", "name", required=False)
        land_col = self._find(col, "land", "country", required=False)

        df = df.rename(
            columns={
                iata_col: "iata",
                cont_col: "continent",
                lon_col: "lon",
                lat_col: "lat",
            }
        )
        df = df.dropna(subset=["iata", "lon", "lat", "continent"])
        df = df.drop_duplicates(subset="iata", keep="first")

        rows: list[dict] = []
        corrected = 0
        for _, r in df.iterrows():
            lat, lon = float(r["lat"]), float(r["lon"])
            file_continent = str(r["continent"]).strip()
            # Derive continent from coordinates; the file's Continent column is
            # unreliable (e.g. Alaskan airports tagged "Africa"). Fall back to the
            # file label only if the coordinate is outside every region.
            continent = continent_from_coords(lat, lon) or file_continent
            if continent != file_continent:
                corrected += 1
            rows.append(
                {
                    "iata": str(r["iata"]).strip().upper()[:3],
                    "name": (str(r[name_col]).strip() if name_col and pd.notna(r[name_col]) else None),
                    "country": (str(r[land_col]).strip() if land_col and pd.notna(r[land_col]) else None),
                    "lon": lon,
                    "lat": lat,
                    "continent": continent,
                }
            )
        log.info(
            "Parsed %d usable airports from %s (continent corrected from coordinates for %d)",
            len(rows), path.name, corrected,
        )
        return rows

    @staticmethod
    def _find(col_map: dict[str, str], *needles: str, required: bool = True) -> str | None:
        for needle in needles:
            for lower, original in col_map.items():
                if needle.lower() in lower:
                    return original
        if required:
            raise KeyError(f"AIRPORTS.xlsx missing a column matching {needles!r}")
        return None
