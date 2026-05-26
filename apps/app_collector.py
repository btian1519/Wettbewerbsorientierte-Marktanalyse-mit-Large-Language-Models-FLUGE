from datetime import date
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from src.collect_sources import CollectConfig, collect_once, get_available_sources


REGION_BBOX = {
    "Global": {"lamin": -60.0, "lomin": -180.0, "lamax": 85.0, "lomax": 180.0},
    "Europe": {"lamin": 35.0, "lomin": -10.0, "lamax": 71.0, "lomax": 40.0},
    "Asia": {"lamin": -10.0, "lomin": 25.0, "lamax": 80.0, "lomax": 180.0},
    "North America": {"lamin": 7.0, "lomin": -170.0, "lamax": 83.0, "lomax": -50.0},
    "South America": {"lamin": -56.0, "lomin": -82.0, "lamax": 13.0, "lomax": -34.0},
    "Africa": {"lamin": -35.0, "lomin": -20.0, "lamax": 38.0, "lomax": 52.0},
    "Oceania": {"lamin": -50.0, "lomin": 110.0, "lamax": 0.0, "lomax": 180.0},
}

BASE_DIR = Path(__file__).resolve().parent.parent
CONTEXT_PATH = BASE_DIR / "data" / "processed" / "last_collection_context.json"


def save_collection_context(
    region: str,
    bbox: dict,
    origin: str,
    destination: str,
    departure_date_iso: str,
    adults: int,
    result: dict,
) -> None:
    CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "region": region,
        "bbox": bbox,
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date_iso,
        "adults": adults,
        "ok_sources": [item.get("source") for item in result.get("ok", [])],
        "ok_count": len(result.get("ok", [])),
    }
    CONTEXT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


st.set_page_config(page_title="FlightScope AI - One Click Collector", layout="wide")
st.title("✈️ FlightScope AI")
st.caption("One-Click Market Data Collection")

available_sources = get_available_sources()

with st.sidebar:
    st.header("Flight & Market Parameters")
    region = st.selectbox("Region", list(REGION_BBOX.keys()), index=0)

    bbox = REGION_BBOX[region]
    st.caption(
        f"OpenSky bbox for {region}: "
        f"lat {bbox['lamin']}..{bbox['lamax']}, lon {bbox['lomin']}..{bbox['lomax']}"
    )

    with st.expander("Advanced Filters", expanded=False):
        st.caption("Optional OD/date filters used by provider APIs when available.")
        origin = st.text_input("Departure Airport (IATA)", value="FRA", max_chars=3).strip().upper()
        destination = st.text_input("Arrival Airport (IATA)", value="LHR", max_chars=3).strip().upper()
        departure_date = st.date_input("Departure Date", value=date(2026, 6, 15))
        adults = st.number_input("Passengers", min_value=1, max_value=9, value=1, step=1)

    with st.expander("Data Source Status", expanded=False):
        st.markdown(f"**Available Data Sources:** {sum(available_sources.values())}/{len(available_sources)}")
        if not available_sources.get("amadeus"):
            st.caption("⚠️ Amadeus: API key not configured")
        if not available_sources.get("aviationstack"):
            st.caption("⚠️ Aviationstack: API key not configured (AVIATIONSTACK_API_KEY)")
        else:
            st.caption("ℹ️ Aviationstack free plan has a low monthly request limit")
        if not available_sources.get("airlabs"):
            st.caption("⚠️ AirLabs: API key not configured (AIRLABS_API_KEY)")

    st.divider()
    st.caption("Tip: For client demos, keep only Region and click Collect Data Now.")

col1, col2 = st.columns([2, 1])
with col1:
    run = st.button("🔄 Collect Data Now", type="primary", use_container_width=True, key="collect_btn")

if run:
    cfg = CollectConfig(
        origin=origin,
        destination=destination,
        departure_date=departure_date.isoformat(),
        adults=int(adults),
        dep_iata=origin,
        arr_iata=destination,
        eurostat_dataset="",
        geo="DE",
        start_period="2023-01",
        end_period="2026-12",
        lamin=bbox["lamin"],
        lomin=bbox["lomin"],
        lamax=bbox["lamax"],
        lomax=bbox["lomax"],
        use_opensky=available_sources.get("opensky", False),
        use_eurostat=available_sources.get("eurostat", False),
        use_amadeus=available_sources.get("amadeus", False),
        use_aviationstack=available_sources.get("aviationstack", False),
        use_airlabs=available_sources.get("airlabs", False),
    )

    with st.spinner("Collecting market data..."):
        result = collect_once(cfg)

    save_collection_context(
        region=region,
        bbox=bbox,
        origin=origin,
        destination=destination,
        departure_date_iso=departure_date.isoformat(),
        adults=int(adults),
        result=result,
    )

    st.subheader("Collection Complete")
    if result["ok"]:
        st.success(f"✅ Successfully collected from {len(result['ok'])} source(s)")
        st.dataframe(
            [{"Source": r["source"], "Records": r["records"], "File": r["path"].split("\\")[-1]} for r in result["ok"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error("No data collected. Check API configuration.")

st.divider()
st.markdown("**Status:** Ready | One-click collection mode")
st.caption("Data stored in: `data/raw/<source>/timestamp.json`")