import argparse
import json
import importlib.util
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
OPENSKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
_OPENSKY_TOKEN_CACHE: Dict[str, Any] = {"access_token": "", "expires_at": 0.0}


def load_local_env(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a local .env file if present."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or not str(os.environ.get(key) or "").strip()):
            os.environ[key] = value


def load_opensky_credentials_file(credentials_path: Path) -> None:
    """Load OpenSky OAuth2 credentials from a local JSON file if present."""
    if not credentials_path.exists():
        return

    try:
        payload = json.loads(credentials_path.read_text(encoding="utf-8"))
    except Exception:
        return

    client_id = str(payload.get("clientId") or "").strip()
    client_secret = str(payload.get("clientSecret") or "").strip()
    if client_id and "OPENSKY_CLIENT_ID" not in os.environ:
        os.environ["OPENSKY_CLIENT_ID"] = client_id
    if client_secret and "OPENSKY_CLIENT_SECRET" not in os.environ:
        os.environ["OPENSKY_CLIENT_SECRET"] = client_secret


load_local_env(BASE_DIR / ".env")
load_opensky_credentials_file(BASE_DIR / "openskyapi" / "credentials.json")


def check_credential(env_var_name: str) -> bool:
    """Check if a credential is configured."""
    return bool(os.getenv(env_var_name))


def get_env_first(*names: str) -> Optional[str]:
    """Return the first non-empty environment variable among aliases."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _is_playwright_available() -> bool:
    """Return True if Playwright is importable, without raising when absent.

    ``importlib.util.find_spec`` raises ``ModuleNotFoundError`` for a dotted
    submodule whose parent package is missing, so guard it to stay portable on
    machines without Playwright (Check24 is optional).
    """
    try:
        return importlib.util.find_spec("playwright.sync_api") is not None
    except ModuleNotFoundError:
        return False


def get_available_sources() -> Dict[str, bool]:
    """Return dict of available sources based on configured credentials."""
    return {
        "opensky": True,
        "opensky_flights": bool(get_env_first("OPENSKY_CLIENT_ID") and get_env_first("OPENSKY_CLIENT_SECRET")),
        "eurostat": True,
        "amadeus": check_credential("AMADEUS_CLIENT_ID") and check_credential("AMADEUS_CLIENT_SECRET"),
        "aviationstack": bool(get_env_first("AVIATIONSTACK_API_KEY", "AVIATIONSTACK_KEY")),
        "airlabs": bool(get_env_first("AIRLABS_API_KEY", "AIRLABS_KEY")),
        "check24": _is_playwright_available(),
    }


@dataclass
class CollectConfig:
    origin: str = "FRA"
    destination: str = "LHR"
    departure_date: str = "2026-06-15"
    return_date: str = "2026-06-22"
    adults: int = 1
    check24_cabin: str = "EPBF"
    check24_max_offers: int = 10

    dep_iata: str = "FRA"
    arr_iata: str = "LHR"

    eurostat_dataset: str = ""
    geo: str = "DE"
    start_period: str = "2023-01"
    end_period: str = "2026-12"

    lamin: float = 47.0
    lomin: float = 5.5
    lamax: float = 55.0
    lomax: float = 15.5

    use_opensky: bool = True
    use_eurostat: bool = True
    use_amadeus: bool = True
    use_aviationstack: bool = True
    use_airlabs: bool = True
    use_check24: bool = True


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(source: str, payload: Dict[str, Any]) -> Path:
    source_dir = RAW_DIR / source
    ensure_dir(source_dir)
    out = source_dir / f"{utc_now()}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
    final_headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if headers:
        final_headers.update(headers)
    req = Request(url=url, headers=final_headers, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def http_post_form_json(url: str, form: Dict[str, str], headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
    data = urlencode(form).encode("utf-8")
    final_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    if headers:
        final_headers.update(headers)
    req = Request(url=url, data=data, headers=final_headers, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def _parse_eur_amount(value: str) -> float:
    text = str(value or "").replace("\xa0", " ").replace("€", "").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def _safe_locator_text(locator: Any) -> str:
    try:
        if locator.count() > 0:
            return _normalize_text(locator.first.inner_text())
    except Exception:
        return ""
    return ""


def _safe_locator_texts(locator: Any) -> List[str]:
    try:
        return [_normalize_text(text) for text in locator.all_inner_texts() if _normalize_text(text)]
    except Exception:
        return []


def _default_return_date(departure_date: str) -> str:
    try:
        return (date.fromisoformat(departure_date) + timedelta(days=7)).isoformat()
    except ValueError:
        return departure_date


def _extract_check24_offer(offer: Any) -> Dict[str, Any]:
    label = _safe_locator_text(offer.locator('[data-testid^="offer_label_"]'))
    price_text = _safe_locator_text(offer.locator('[data-testid="price_formatted"]'))
    luggage_text = _safe_locator_text(offer.locator('[data-testid="inclusive_luggage_text"]'))
    dynamic_points = _safe_locator_text(offer.locator('[data-testid="dynamic_points"]'))
    flights: List[Dict[str, str]] = []

    for segment_key in ["flight_0_info", "flight_1_info"]:
        segment = offer.locator(f'[data-testid="{segment_key}"]')
        if segment.count() == 0:
            continue
        carrier_summary = _safe_locator_text(segment.locator('[data-testid="carrier_text"]'))
        carrier_name = _safe_locator_text(segment.locator('[data-testid="carrier_name"]')) or carrier_summary
        flights.append(
            {
                "departure_time": _safe_locator_text(segment.locator('[data-testid="departure_time"]')),
                "departure_iata": _safe_locator_text(segment.locator('[data-testid="departure_iata"]')),
                "departure_date": _safe_locator_text(segment.locator('[data-testid="departure_date"]')),
                "duration": _safe_locator_text(segment.locator('[data-testid="travel_time_duration"]')),
                "stops": _safe_locator_text(segment.locator('[data-testid="travel_time_stops"]')),
                "arrival_time": _safe_locator_text(segment.locator('[data-testid="arrival_time"]')),
                "arrival_iata": _safe_locator_text(segment.locator('[data-testid="arrival_iata"]')),
                "arrival_date": _safe_locator_text(segment.locator('[data-testid="arrival_date"]')),
                "carrier_name": carrier_name,
                "carrier_detail": carrier_summary,
            }
        )

    carriers = [flight.get("carrier_name", "") for flight in flights if flight.get("carrier_name")]
    unique_carriers = list(dict.fromkeys(carriers))
    stops_summary = list(dict.fromkeys([flight.get("stops", "") for flight in flights if flight.get("stops")]))
    return {
        "label": label,
        "price_text": price_text,
        "price_eur": _parse_eur_amount(price_text),
        "luggage": luggage_text,
        "dynamic_points": dynamic_points,
        "carriers": unique_carriers,
        "outbound_carrier": flights[0].get("carrier_name", "") if flights else "",
        "inbound_carrier": flights[1].get("carrier_name", "") if len(flights) > 1 else "",
        "stops": stops_summary,
        "flights": flights,
    }


def collect_check24(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_code: str = "EPBF",
    max_offers: int = 10,
    headless: bool = True,
) -> Dict[str, Any]:
    if not origin or not destination or not departure_date:
        raise RuntimeError("Check24 requires origin, destination, and departure_date")

    return_date = return_date or _default_return_date(departure_date)
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not installed. Run 'python -m pip install playwright' and 'python -m playwright install chromium'.") from exc

    query = {
        "from_0": f"{origin}-A",
        "to_0": f"{destination}-A",
        "date_0": departure_date,
        "from_1": f"{destination}-A",
        "to_1": f"{origin}-A",
        "date_1": return_date,
        "adt": max(1, int(adults)),
        "class": cabin_code,
    }
    url = f"https://flug.check24.de/search?{urlencode(query)}"
    offers: List[Dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page(locale="de-DE", user_agent="Mozilla/5.0")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            cookie_button = page.get_by_text("Nur notwendige Cookies", exact=True).first
            if cookie_button.count() > 0:
                cookie_button.click(timeout=5000)
                page.wait_for_timeout(1500)
            page.wait_for_selector('[data-testid="offer_0"]', timeout=90000)
            headline = _safe_locator_text(page.locator('[data-testid="results_headline"]'))
            direct_count = _safe_locator_text(page.locator('[data-testid="filter_transfer_count_0_count"]'))
            direct_price = _safe_locator_text(page.locator('[data-testid="filter_transfer_count_0_price"]'))

            for index in range(max(1, int(max_offers))):
                offer = page.locator(f'[data-testid="offer_{index}"]').first
                if offer.count() == 0:
                    break
                offers.append(_extract_check24_offer(offer))

            browser.close()
        except PlaywrightTimeoutError as exc:
            browser.close()
            raise RuntimeError(f"Check24 timed out while loading offers: {exc}") from exc
        except Exception:
            browser.close()
            raise

    return {
        "source": "check24",
        "endpoint": url,
        "collected_at": utc_now(),
        "records": len(offers),
        "query": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": max(1, int(adults)),
            "cabin_code": cabin_code,
        },
        "summary": {
            "headline": headline,
            "direct_count": direct_count,
            "direct_min_price": direct_price,
        },
        "offers": offers,
    }


def get_opensky_auth_headers(require_auth: bool = False) -> Dict[str, str]:
    """Return OpenSky Bearer auth headers when OAuth2 credentials are configured."""
    client_id = get_env_first("OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_ID")
    client_secret = get_env_first("OPENSKY_CLIENT_SECRET", "OPENSKY_CLIENT_SECRET")

    if not client_id or not client_secret:
        if require_auth:
            raise RuntimeError(
                "Missing OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET. "
                "OpenSky flights endpoints now require OAuth2 client credentials."
            )
        return {}

    now_ts = time.time()
    cached_token = str(_OPENSKY_TOKEN_CACHE.get("access_token") or "")
    expires_at = float(_OPENSKY_TOKEN_CACHE.get("expires_at") or 0.0)
    if cached_token and now_ts < expires_at - 30:
        return {"Authorization": f"Bearer {cached_token}"}

    token_data = http_post_form_json(
        OPENSKY_TOKEN_URL,
        {
            "grant_type": "client_credentials",
            "client_id": str(client_id),
            "client_secret": str(client_secret),
        },
    )
    access_token = str(token_data.get("access_token") or "")
    expires_in = int(token_data.get("expires_in") or 1800)
    if not access_token:
        raise RuntimeError("Failed to obtain OpenSky OAuth2 access token")

    _OPENSKY_TOKEN_CACHE["access_token"] = access_token
    _OPENSKY_TOKEN_CACHE["expires_at"] = now_ts + expires_in
    return {"Authorization": f"Bearer {access_token}"}


# ---------------------------------------------------------------------------
# OpenSky flights – hub airports per region (ICAO codes)
# ---------------------------------------------------------------------------
REGION_HUB_ICAO: Dict[str, List[str]] = {
    "Europe":        ["EDDF", "EGLL", "LFPG", "EHAM", "LEMD", "LIRF", "EDDM", "LOWW"],
    "Asia":          ["VHHH", "WSSS", "RJTT", "RKSI", "ZBAA", "ZSPD", "VTBS", "WMKK"],
    "North America": ["KJFK", "KLAX", "KATL", "KORD", "KDFW", "CYYZ"],
    "South America": ["SBGR", "SCEL", "SAEZ", "SKBO"],
    "Africa":        ["HAAB", "FAOR", "HECA", "GMMN", "DNMM"],
    "Oceania":       ["YSSY", "YMML", "NZAA", "YBBN"],
}

# ICAO airport code -> IATA airport code
ICAO_AIRPORT_TO_IATA: Dict[str, str] = {
    "EDDF": "FRA", "EGLL": "LHR", "LFPG": "CDG", "EHAM": "AMS", "LEMD": "MAD",
    "LIRF": "FCO", "EDDM": "MUC", "LOWW": "VIE", "EBBR": "BRU", "LSZH": "ZRH",
    "LEBL": "BCN", "LFMN": "NCE", "EGKK": "LGW", "EPWA": "WAW", "LHBP": "BUD",
    "VHHH": "HKG", "WSSS": "SIN", "RJTT": "HND", "RJAA": "NRT", "RKSI": "ICN",
    "ZBAA": "PEK", "ZSPD": "PVG", "VTBS": "BKK", "WMKK": "KUL", "VIDP": "DEL",
    "VABB": "BOM", "ZGSZ": "SZX", "ZGGG": "CAN", "RCTP": "TPE", "VOMM": "MAA",
    "VECC": "CCU", "RPLL": "MNL", "WIII": "CGK", "VDPP": "PNH",
    "KJFK": "JFK", "KLAX": "LAX", "KATL": "ATL", "KORD": "ORD", "KDFW": "DFW",
    "CYYZ": "YYZ", "KIAH": "IAH", "KSFO": "SFO", "KDEN": "DEN", "KMIA": "MIA",
    "CYVR": "YVR", "CYUL": "YUL", "KBOS": "BOS", "KJFK": "JFK",
    "SBGR": "GRU", "SCEL": "SCL", "SAEZ": "EZE", "SKBO": "BOG", "SBGL": "GIG",
    "SBCF": "CNF", "SPIM": "LIM", "SEQM": "UIO",
    "HAAB": "ADD", "FAOR": "JNB", "HECA": "CAI", "GMMN": "CMN", "DNMM": "LOS",
    "HKJK": "NBO", "FMMI": "TNR", "GOBD": "DSS", "HTDA": "DAR",
    "YSSY": "SYD", "YMML": "MEL", "NZAA": "AKL", "YBBN": "BNE",
    "YPPH": "PER", "NFFN": "NAN",
}

# ICAO airline 3-letter designator -> IATA 2-letter code
ICAO_AIRLINE_TO_IATA: Dict[str, str] = {
    # Europe
    "DLH": "LH",  "BAW": "BA",  "AFR": "AF",  "KLM": "KL",  "IBE": "IB",
    "AZA": "AZ",  "AUA": "OS",  "SWR": "LX",  "SAS": "SK",  "RYR": "FR",
    "EZY": "U2",  "VLG": "VY",  "TAP": "TP",  "LOT": "LO",  "MAL": "MA",
    "BEL": "SN",  "TUI": "X3",  "EWG": "EW",  "CFG": "DE",  "CLX": "CV",
    # Asia
    "CPA": "CX",  "SIA": "SQ",  "JAL": "JL",  "ANA": "NH",  "KAL": "KE",
    "AAR": "OZ",  "CCA": "CA",  "CSN": "CZ",  "CHH": "HU",  "MAS": "MH",
    "THA": "TG",  "GAP": "GA",  "PAL": "PR",  "UAE": "EK",  "ETD": "EY",
    "QTR": "QR",  "GFA": "GF",  "SVA": "SV",  "OMA": "WY",  "PIA": "PK",
    "IAW": "IA",  "ICE": "FI",  "HDA": "HD",  "APJ": "MM",  "JJP": "GK",
    # North America
    "AAL": "AA",  "DAL": "DL",  "UAL": "UA",  "SWA": "WN",  "ASA": "AS",
    "JBU": "B6",  "SKW": "OO",  "WJA": "WS",  "ACA": "AC",  "FFT": "F9",
    "NKS": "NK",  "HAL": "HA",  "ENY": "MQ",
    # South America
    "TAM": "JJ",  "GLO": "G3",  "AVA": "AV",  "LAN": "LA",  "ARG": "AR",
    "CGD": "P9",  "EXS": "LS",
    # Africa
    "ETH": "ET",  "SAA": "SA",  "MSR": "MS",  "RAM": "AT",  "AHA": "W3",
    "KQA": "KQ",  "MGL": "MK",  "DAH": "AH",
    # Oceania
    "QFA": "QF",  "ANZ": "NZ",  "VAU": "VA",  "JST": "JQ",
}


def _parse_callsign_airline(callsign: Optional[str]) -> str:
    """Extract IATA airline code from an ICAO callsign (first 3 chars = ICAO designator)."""
    if not callsign:
        return ""
    cs = callsign.strip().upper()
    if len(cs) >= 3:
        icao_prefix = cs[:3]
        iata = ICAO_AIRLINE_TO_IATA.get(icao_prefix, "")
        if iata:
            return iata
    # fallback: try 2-char IATA directly (some operators file with IATA callsigns)
    if len(cs) >= 2:
        return cs[:2]
    return ""


def _iter_opensky_time_windows(begin_epoch: int, end_epoch: int, chunk_seconds: int = 24 * 3600) -> List[tuple[int, int]]:
    """Split a larger interval into API-safe chunks that do not cross more than two UTC day partitions."""
    windows: List[tuple[int, int]] = []
    cursor = int(begin_epoch)
    end_epoch = int(end_epoch)
    while cursor < end_epoch:
        chunk_end = min(cursor + chunk_seconds, end_epoch)
        windows.append((cursor, chunk_end))
        cursor = chunk_end
    return windows


def collect_opensky_flights_region(
    region: str,
    begin_epoch: int,
    end_epoch: int,
) -> Dict[str, Any]:
    """
    Query OpenSky /flights/departure for each hub airport in the region.
    Returns aggregated OD pair counts per airline.

    OpenSky constraint: each request must not cross more than two UTC day partitions,
    so this function automatically splits larger intervals into smaller chunks.
    Uses OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET for OAuth2 auth.
    """
    hubs = REGION_HUB_ICAO.get(region, [])
    if not hubs:
        raise RuntimeError(
            f"OpenSky flights history is not configured for region '{region}'. "
            "Choose a concrete region with defined hub airports."
        )

    auth_headers = get_opensky_auth_headers(require_auth=True)

    # od_counts[airline_iata][dep_iata-arr_iata] = count
    od_counts: Dict[str, Dict[str, int]] = {}
    raw_records: int = 0
    errors: List[str] = []

    for hub_icao in hubs:
        for chunk_begin, chunk_end in _iter_opensky_time_windows(begin_epoch, end_epoch):
            params = urlencode({"airport": hub_icao, "begin": chunk_begin, "end": chunk_end})
            url = f"https://opensky-network.org/api/flights/departure?{params}"
            try:
                flights = http_get_json(url, headers=auth_headers, timeout=20)
                if not isinstance(flights, list):
                    errors.append(f"{hub_icao} [{chunk_begin},{chunk_end}]: unexpected response type")
                    continue
                raw_records += len(flights)
                for f in flights:
                    dep_icao = (f.get("estDepartureAirport") or "").strip().upper()
                    arr_icao = (f.get("estArrivalAirport") or "").strip().upper()
                    if not dep_icao or not arr_icao or dep_icao == arr_icao:
                        continue
                    dep_iata = ICAO_AIRPORT_TO_IATA.get(dep_icao, dep_icao)
                    arr_iata = ICAO_AIRPORT_TO_IATA.get(arr_icao, arr_icao)
                    airline = _parse_callsign_airline(f.get("callsign"))
                    if not airline:
                        continue
                    od = f"{dep_iata}-{arr_iata}"
                    od_counts.setdefault(airline, {})
                    od_counts[airline][od] = od_counts[airline].get(od, 0) + 1
            except Exception as exc:
                errors.append(f"{hub_icao} [{chunk_begin},{chunk_end}]: {exc}")

    result = {
        "source": "opensky_flights",
        "region": region,
        "collected_at": utc_now(),
        "begin_epoch": begin_epoch,
        "end_epoch": end_epoch,
        "hubs_queried": hubs,
        "raw_records": raw_records,
        "records": sum(len(v) for v in od_counts.values()),
        "od_counts": od_counts,
        "errors": errors,
    }
    return result


def collect_opensky_states(lamin: float, lomin: float, lamax: float, lomax: float) -> Dict[str, Any]:
    params = urlencode({"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax})
    url = f"https://opensky-network.org/api/states/all?{params}"

    headers = get_opensky_auth_headers(require_auth=False)

    data = http_get_json(url, headers=headers)
    return {
        "source": "opensky",
        "endpoint": url,
        "collected_at": utc_now(),
        "records": len(data.get("states") or []),
        "data": data,
    }


def collect_aviationstack(dep_iata: Optional[str], arr_iata: Optional[str]) -> Dict[str, Any]:
    api_key = get_env_first("AVIATIONSTACK_API_KEY", "AVIATIONSTACK_KEY")
    if not api_key:
        raise RuntimeError("Missing AVIATIONSTACK_API_KEY (or AVIATIONSTACK_KEY)")

    query = {"access_key": api_key}
    if dep_iata:
        query["dep_iata"] = dep_iata
    if arr_iata:
        query["arr_iata"] = arr_iata

    url = f"http://api.aviationstack.com/v1/flights?{urlencode(query)}"
    data = http_get_json(url)
    return {
        "source": "aviationstack",
        "endpoint": url,
        "collected_at": utc_now(),
        "records": len(data.get("data") or []),
        "data": data,
    }


def collect_airlabs(dep_iata: Optional[str], arr_iata: Optional[str]) -> Dict[str, Any]:
    api_key = get_env_first("AIRLABS_API_KEY", "AIRLABS_KEY")
    if not api_key:
        raise RuntimeError("Missing AIRLABS_API_KEY (or AIRLABS_KEY)")

    query = {"api_key": api_key}
    if dep_iata:
        query["dep_iata"] = dep_iata
    if arr_iata:
        query["arr_iata"] = arr_iata

    url = f"https://airlabs.co/api/v9/flights?{urlencode(query)}"
    data = http_get_json(url)
    return {
        "source": "airlabs",
        "endpoint": url,
        "collected_at": utc_now(),
        "records": len(data.get("response") or []),
        "data": data,
    }


def get_amadeus_token() -> str:
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing AMADEUS_CLIENT_ID or AMADEUS_CLIENT_SECRET")

    token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    token_data = http_post_form_json(token_url, payload)
    token = token_data.get("access_token")
    if not token:
        raise RuntimeError("Failed to obtain Amadeus token")
    return token


def collect_amadeus_offers(origin: str, destination: str, departure_date: str, adults: int) -> Dict[str, Any]:
    token = get_amadeus_token()
    query = urlencode(
        {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "EUR",
            "max": 50,
        }
    )
    url = f"https://test.api.amadeus.com/v2/shopping/flight-offers?{query}"
    data = http_get_json(url, headers={"Authorization": f"Bearer {token}"})
    return {
        "source": "amadeus",
        "endpoint": url,
        "collected_at": utc_now(),
        "records": len(data.get("data") or []),
        "data": data,
    }


def collect_eurostat(dataset_code: str, geo: Optional[str], start_period: Optional[str], end_period: Optional[str]) -> Dict[str, Any]:
    params = {}
    if geo:
        params["geo"] = geo
    if start_period:
        params["sinceTimePeriod"] = start_period
    if end_period:
        params["untilTimePeriod"] = end_period

    suffix = f"?{urlencode(params)}" if params else ""
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset_code}{suffix}"
    data = http_get_json(url)
    return {
        "source": "eurostat",
        "endpoint": url,
        "collected_at": utc_now(),
        "records": len(data.get("value") or {}),
        "data": data,
    }


def collect_opensky_flights_region_and_save(region: str, begin_epoch: int, end_epoch: int) -> Dict[str, Any]:
    """Collect OpenSky departure data for a region and save to data/raw/opensky_flights/."""
    payload = collect_opensky_flights_region(region, begin_epoch, end_epoch)
    path = write_json("opensky_flights", payload)
    return {"path": str(path), **payload}


def collect_once(config: CollectConfig) -> Dict[str, List[Dict[str, Any]]]:
    ok: List[Dict[str, Any]] = []
    warn: List[Dict[str, Any]] = []

    if config.use_opensky:
        try:
            opensky_payload = collect_opensky_states(config.lamin, config.lomin, config.lamax, config.lomax)
            path = write_json("opensky", opensky_payload)
            ok.append({"source": "opensky", "path": str(path), "records": opensky_payload.get("records", 0)})
        except Exception as exc:
            warn.append({"source": "opensky", "error": str(exc)})

    if config.use_eurostat and config.eurostat_dataset:
        try:
            eurostat_payload = collect_eurostat(
                config.eurostat_dataset,
                config.geo,
                config.start_period,
                config.end_period,
            )
            path = write_json("eurostat", eurostat_payload)
            ok.append({"source": "eurostat", "path": str(path), "records": eurostat_payload.get("records", 0)})
        except Exception as exc:
            warn.append({"source": "eurostat", "error": str(exc)})

    if config.use_amadeus:
        try:
            amadeus_payload = collect_amadeus_offers(
                config.origin,
                config.destination,
                config.departure_date,
                config.adults,
            )
            path = write_json("amadeus", amadeus_payload)
            ok.append({"source": "amadeus", "path": str(path), "records": amadeus_payload.get("records", 0)})
        except Exception as exc:
            warn.append({"source": "amadeus", "error": str(exc)})

    if config.use_aviationstack:
        try:
            aviationstack_payload = collect_aviationstack(config.dep_iata, config.arr_iata)
            path = write_json("aviationstack", aviationstack_payload)
            ok.append({"source": "aviationstack", "path": str(path), "records": aviationstack_payload.get("records", 0)})
        except Exception as exc:
            warn.append({"source": "aviationstack", "error": str(exc)})

    if config.use_airlabs:
        try:
            airlabs_payload = collect_airlabs(config.dep_iata, config.arr_iata)
            path = write_json("airlabs", airlabs_payload)
            ok.append({"source": "airlabs", "path": str(path), "records": airlabs_payload.get("records", 0)})
        except Exception as exc:
            warn.append({"source": "airlabs", "error": str(exc)})

    if config.use_check24:
        if config.origin and config.destination and config.departure_date:
            try:
                check24_payload = collect_check24(
                    config.origin,
                    config.destination,
                    config.departure_date,
                    return_date=config.return_date,
                    adults=config.adults,
                    cabin_code=config.check24_cabin,
                    max_offers=config.check24_max_offers,
                )
                path = write_json("check24", check24_payload)
                ok.append({"source": "check24", "path": str(path), "records": check24_payload.get("records", 0)})
            except Exception as exc:
                warn.append({"source": "check24", "error": str(exc)})
        else:
            warn.append({"source": "check24", "error": "Skipped: missing origin, destination, or departure date"})

    return {"ok": ok, "warn": warn}


def run_once(args: argparse.Namespace) -> None:
    config = CollectConfig(
        origin=args.origin,
        destination=args.destination,
        departure_date=args.departure_date,
        return_date=args.return_date,
        adults=args.adults,
        check24_cabin=args.check24_cabin,
        check24_max_offers=args.check24_max_offers,
        dep_iata=args.dep_iata,
        arr_iata=args.arr_iata,
        eurostat_dataset=args.eurostat_dataset,
        geo=args.geo,
        start_period=args.start_period,
        end_period=args.end_period,
        lamin=args.lamin,
        lomin=args.lomin,
        lamax=args.lamax,
        lomax=args.lomax,
        use_opensky=not args.skip_opensky,
        use_eurostat=not args.skip_eurostat,
        use_amadeus=not args.skip_amadeus,
        use_aviationstack=not args.skip_aviationstack,
        use_airlabs=not args.skip_airlabs,
        use_check24=not args.skip_check24,
    )
    result = collect_once(config)

    for item in result["warn"]:
        print(f"[WARN] {item['source']} failed: {item['error']}")

    for item in result["ok"]:
        print(f"[OK] {item['source']}: {item['path']} (records={item['records']})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="API-first data collector for FlightScope")
    parser.add_argument("--loop-seconds", type=int, default=0, help="Run continuously with this interval. 0 = run once")

    parser.add_argument("--origin", default="FRA", help="Origin IATA for fare query")
    parser.add_argument("--destination", default="LHR", help="Destination IATA for fare query")
    parser.add_argument("--departure-date", default="2026-06-15", help="Departure date YYYY-MM-DD")
    parser.add_argument("--return-date", default="2026-06-22", help="Return date YYYY-MM-DD for Check24 round-trip search")
    parser.add_argument("--adults", type=int, default=1, help="Number of adults for fare query")
    parser.add_argument("--check24-cabin", default="EPBF", help="Check24 cabin code (EPBF=Economy)")
    parser.add_argument("--check24-max-offers", type=int, default=10, help="Maximum number of Check24 offers to capture")

    parser.add_argument("--dep-iata", default="FRA", help="Departure IATA for live flight feeds")
    parser.add_argument("--arr-iata", default="LHR", help="Arrival IATA for live flight feeds")

    parser.add_argument("--eurostat-dataset", default="", help="Eurostat dataset code (optional)")
    parser.add_argument("--geo", default="DE", help="Geo filter for Eurostat")
    parser.add_argument("--start-period", default="2023-01", help="Eurostat start period")
    parser.add_argument("--end-period", default="2026-12", help="Eurostat end period")

    parser.add_argument("--lamin", type=float, default=47.0)
    parser.add_argument("--lomin", type=float, default=5.5)
    parser.add_argument("--lamax", type=float, default=55.0)
    parser.add_argument("--lomax", type=float, default=15.5)

    parser.add_argument("--skip-opensky", action="store_true", help="Skip OpenSky source")
    parser.add_argument("--skip-eurostat", action="store_true", help="Skip Eurostat source")
    parser.add_argument("--skip-amadeus", action="store_true", help="Skip Amadeus source")
    parser.add_argument("--skip-aviationstack", action="store_true", help="Skip Aviationstack source")
    parser.add_argument("--skip-airlabs", action="store_true", help="Skip AirLabs source")
    parser.add_argument("--skip-check24", action="store_true", help="Skip Check24 web source")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.loop_seconds <= 0:
        run_once(args)
        return

    while True:
        run_once(args)
        time.sleep(args.loop_seconds)


if __name__ == "__main__":
    main()
