"""Route database grouped by world regions for recommendation filtering."""

ALL_REGION_OD_ROUTES = {
    "Europe": [
        {"od": "IST-LHR", "origin": "Istanbul (IST)", "destination": "London (LHR)", "distance_km": 2490, "demand_tier": "high"},
        {"od": "IST-CDG", "origin": "Istanbul (IST)", "destination": "Paris (CDG)", "distance_km": 2260, "demand_tier": "high"},
        {"od": "IST-AMS", "origin": "Istanbul (IST)", "destination": "Amsterdam (AMS)", "distance_km": 2210, "demand_tier": "high"},
        {"od": "IST-FCO", "origin": "Istanbul (IST)", "destination": "Rome (FCO)", "distance_km": 1370, "demand_tier": "high"},
        {"od": "IST-MAD", "origin": "Istanbul (IST)", "destination": "Madrid (MAD)", "distance_km": 2730, "demand_tier": "medium"},
        {"od": "IST-VIE", "origin": "Istanbul (IST)", "destination": "Vienna (VIE)", "distance_km": 1275, "demand_tier": "high"},
        {"od": "IST-FRA", "origin": "Istanbul (IST)", "destination": "Frankfurt (FRA)", "distance_km": 1860, "demand_tier": "high"},
        {"od": "CDG-LHR", "origin": "Paris (CDG)", "destination": "London (LHR)", "distance_km": 345, "demand_tier": "high"},
        {"od": "CDG-AMS", "origin": "Paris (CDG)", "destination": "Amsterdam (AMS)", "distance_km": 400, "demand_tier": "high"},
        {"od": "CDG-FCO", "origin": "Paris (CDG)", "destination": "Rome (FCO)", "distance_km": 1105, "demand_tier": "high"},
        {"od": "CDG-MAD", "origin": "Paris (CDG)", "destination": "Madrid (MAD)", "distance_km": 1060, "demand_tier": "high"},
        {"od": "CDG-BCN", "origin": "Paris (CDG)", "destination": "Barcelona (BCN)", "distance_km": 860, "demand_tier": "high"},
        {"od": "CDG-VIE", "origin": "Paris (CDG)", "destination": "Vienna (VIE)", "distance_km": 1035, "demand_tier": "medium"},
        {"od": "CDG-LGW", "origin": "Paris (CDG)", "destination": "London Gatwick (LGW)", "distance_km": 310, "demand_tier": "medium"},
        {"od": "FRA-LHR", "origin": "Frankfurt (FRA)", "destination": "London (LHR)", "distance_km": 650, "demand_tier": "high"},
        {"od": "FRA-AMS", "origin": "Frankfurt (FRA)", "destination": "Amsterdam (AMS)", "distance_km": 365, "demand_tier": "high"},
        {"od": "FRA-FCO", "origin": "Frankfurt (FRA)", "destination": "Rome (FCO)", "distance_km": 960, "demand_tier": "high"},
        {"od": "FRA-MAD", "origin": "Frankfurt (FRA)", "destination": "Madrid (MAD)", "distance_km": 1440, "demand_tier": "high"},
        {"od": "LHR-AMS", "origin": "London (LHR)", "destination": "Amsterdam (AMS)", "distance_km": 360, "demand_tier": "high"},
        {"od": "LHR-FCO", "origin": "London (LHR)", "destination": "Rome (FCO)", "distance_km": 1430, "demand_tier": "high"},
        {"od": "LHR-MAD", "origin": "London (LHR)", "destination": "Madrid (MAD)", "distance_km": 1260, "demand_tier": "high"},
        {"od": "MAD-BCN", "origin": "Madrid (MAD)", "destination": "Barcelona (BCN)", "distance_km": 620, "demand_tier": "high"},
        {"od": "MUC-VIE", "origin": "Munich (MUC)", "destination": "Vienna (VIE)", "distance_km": 355, "demand_tier": "medium"},
    ],
    "Asia": [
        {"od": "HND-ICN", "origin": "Tokyo (HND)", "destination": "Seoul (ICN)", "distance_km": 1160, "demand_tier": "high"},
        {"od": "HKG-SIN", "origin": "Hong Kong (HKG)", "destination": "Singapore (SIN)", "distance_km": 2560, "demand_tier": "high"},
        {"od": "PVG-HKG", "origin": "Shanghai (PVG)", "destination": "Hong Kong (HKG)", "distance_km": 1230, "demand_tier": "high"},
        {"od": "DEL-BOM", "origin": "Delhi (DEL)", "destination": "Mumbai (BOM)", "distance_km": 1140, "demand_tier": "high"},
        {"od": "BKK-SIN", "origin": "Bangkok (BKK)", "destination": "Singapore (SIN)", "distance_km": 1430, "demand_tier": "high"},
        {"od": "CGK-KUL", "origin": "Jakarta (CGK)", "destination": "Kuala Lumpur (KUL)", "distance_km": 1120, "demand_tier": "medium"},
    ],
    "North America": [
        {"od": "JFK-LAX", "origin": "New York (JFK)", "destination": "Los Angeles (LAX)", "distance_km": 3980, "demand_tier": "high"},
        {"od": "LAX-SFO", "origin": "Los Angeles (LAX)", "destination": "San Francisco (SFO)", "distance_km": 540, "demand_tier": "high"},
        {"od": "ORD-ATL", "origin": "Chicago (ORD)", "destination": "Atlanta (ATL)", "distance_km": 980, "demand_tier": "high"},
        {"od": "YYZ-YVR", "origin": "Toronto (YYZ)", "destination": "Vancouver (YVR)", "distance_km": 3350, "demand_tier": "medium"},
        {"od": "MEX-CUN", "origin": "Mexico City (MEX)", "destination": "Cancun (CUN)", "distance_km": 1290, "demand_tier": "medium"},
    ],
    "South America": [
        {"od": "GRU-GIG", "origin": "Sao Paulo (GRU)", "destination": "Rio de Janeiro (GIG)", "distance_km": 360, "demand_tier": "high"},
        {"od": "BOG-MDE", "origin": "Bogota (BOG)", "destination": "Medellin (MDE)", "distance_km": 215, "demand_tier": "high"},
        {"od": "SCL-LIM", "origin": "Santiago (SCL)", "destination": "Lima (LIM)", "distance_km": 2460, "demand_tier": "medium"},
        {"od": "EZE-SCL", "origin": "Buenos Aires (EZE)", "destination": "Santiago (SCL)", "distance_km": 1140, "demand_tier": "medium"},
    ],
    "Africa": [
        {"od": "CAI-JNB", "origin": "Cairo (CAI)", "destination": "Johannesburg (JNB)", "distance_km": 6240, "demand_tier": "medium"},
        {"od": "NBO-ADD", "origin": "Nairobi (NBO)", "destination": "Addis Ababa (ADD)", "distance_km": 1160, "demand_tier": "medium"},
        {"od": "CMN-RAK", "origin": "Casablanca (CMN)", "destination": "Marrakech (RAK)", "distance_km": 200, "demand_tier": "high"},
        {"od": "LOS-ABV", "origin": "Lagos (LOS)", "destination": "Abuja (ABV)", "distance_km": 520, "demand_tier": "high"},
    ],
    "Oceania": [
        {"od": "SYD-MEL", "origin": "Sydney (SYD)", "destination": "Melbourne (MEL)", "distance_km": 715, "demand_tier": "high"},
        {"od": "BNE-SYD", "origin": "Brisbane (BNE)", "destination": "Sydney (SYD)", "distance_km": 730, "demand_tier": "high"},
        {"od": "AKL-SYD", "origin": "Auckland (AKL)", "destination": "Sydney (SYD)", "distance_km": 2160, "demand_tier": "high"},
        {"od": "PER-MEL", "origin": "Perth (PER)", "destination": "Melbourne (MEL)", "distance_km": 2720, "demand_tier": "medium"},
    ],
}

AIRLINE_HOMEBASE_MAP = {
    # Europe
    "LH": ["FRA", "MUC"], "BA": "LHR", "AF": "CDG", "KL": "AMS",
    "IB": "MAD", "VY": "BCN", "U2": "LGW", "OS": "VIE",
    "TK": "IST", "AZ": "FCO",
    # Asia
    "CX": "HKG", "SQ": "SIN", "NH": "NRT", "JL": "NRT",
    "KE": "ICN", "MH": "KUL", "TG": "BKK", "CA": "PEK",
    "MU": "PVG", "AI": "DEL",
    # North America
    "AA": "DFW", "DL": "ATL", "UA": "ORD", "WN": "DAL",
    "AC": "YYZ", "B6": "JFK",
    # South America
    "LA": "SCL", "G3": "GRU", "AR": "EZE", "CM": "PTY",
    # Africa
    "ET": "ADD", "SA": "JNB", "MS": "CAI", "AT": "CMN",
    # Oceania
    "QF": "SYD", "NZ": "AKL", "VA": "BNE",
}

# Aircraft type mapping based on typical capacity and range
AIRCRAFT_TYPES = [
    {"code": "CRJ9", "seats": 90, "range_km": 2900, "turnaround_min": 25},
    {"code": "E190", "seats": 100, "range_km": 4500, "turnaround_min": 25},
    {"code": "E195", "seats": 120, "range_km": 4000, "turnaround_min": 25},
    {"code": "A319", "seats": 144, "range_km": 6300, "turnaround_min": 30},
    {"code": "A320", "seats": 194, "range_km": 6300, "turnaround_min": 30},
    {"code": "A321", "seats": 244, "range_km": 7000, "turnaround_min": 30},
    {"code": "B737-8", "seats": 189, "range_km": 5600, "turnaround_min": 30},
    {"code": "B737-9", "seats": 220, "range_km": 6570, "turnaround_min": 30},
]

AIRLINE_FLEET_OPTIONS = {
    "LH": ["A319", "A320", "A321"],
    "BA": ["A320", "A321", "B737-8"],
    "AF": ["A319", "A320", "A321"],
    "KL": ["E195", "A320", "A321"],
    "IB": ["A320", "A321"],
    "VY": ["A320", "A321"],
    "U2": ["A319", "A320", "A321"],
    "OS": ["CRJ9", "E195", "A320", "A321"],
    "TK": ["A320", "A321", "B737-8", "B737-9"],
    "AZ": ["A319", "A320", "A321"],
    "LX": ["A220-300", "A320", "A321"],
}

AIRCRAFT_SEAT_MAP = {
    "A220-300": 145,
    "A223": 145,
    "A319": 144,
    "A320": 180,
    "A20N": 186,
    "A321": 220,
    "A21N": 220,
    "A318": 132,
    "A332": 260,
    "A333": 300,
    "A359": 315,
    "A35K": 350,
    "B738": 189,
    "B37M": 189,
    "B739": 210,
    "B39M": 210,
    "B788": 248,
    "B789": 290,
    "B77W": 360,
    "B763": 240,
    "E190": 100,
    "E195": 120,
    "E295": 132,
    "CRJ9": 90,
    "AT76": 70,
    "DH8D": 78,
}

def get_all_od_routes():
    """Return all OD routes across all configured regions."""
    combined = []
    for routes in ALL_REGION_OD_ROUTES.values():
        combined.extend(routes)
    return combined


def get_routes_by_region(region: str):
    """Return route universe for selected region."""
    if not region or region == "Global":
        return get_all_od_routes()
    return ALL_REGION_OD_ROUTES.get(region, ALL_REGION_OD_ROUTES["Europe"])


def get_homebase_for_airline(airline_code: str) -> str:
    """Return the primary 3-letter homebase IATA for airline code, or empty string if unknown."""
    value = AIRLINE_HOMEBASE_MAP.get(airline_code)
    if isinstance(value, list):
        return str(value[0] if value else "")
    return str(value or "")


def get_homebases_for_airline(airline_code: str) -> list[str]:
    """Return all configured 3-letter homebases for an airline."""
    value = AIRLINE_HOMEBASE_MAP.get(airline_code)
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if value:
        return [str(value)]
    return []

def get_od_candidate_pool_info(airline_code: str, region: str = "Europe"):
    """Return candidate routes and whether they came from a homebase match or a generic region fallback."""
    routes = get_routes_by_region(region)
    bases = get_homebases_for_airline(airline_code)
    if not bases:
        return {"routes": routes, "source": "region-fallback", "homebase": ""}

    filtered = [od for od in routes if any(base in [od["od"][:3], od["od"][4:7]] for base in bases)]
    if filtered:
        if len(filtered) < 3:
            rest = [od for od in routes if od not in filtered]
            filtered = filtered + rest
        return {"routes": filtered, "source": "homebase-match", "homebase": "/".join(bases)}

    return {"routes": routes, "source": "region-fallback", "homebase": "/".join(bases)}

def get_od_by_airline_homebase(airline_code: str, region: str = "Europe"):
    """Filter OD routes relevant to airline home base within the selected region."""
    return get_od_candidate_pool_info(airline_code, region)["routes"]

def recommend_aircraft(estimated_pax: int, airline_code: str = "") -> str:
    """Recommend an aircraft using the airline's configured fleet when available."""
    fleet_codes = AIRLINE_FLEET_OPTIONS.get(str(airline_code or "").strip().upper()) or []
    if fleet_codes:
        candidate_types = [ac for ac in AIRCRAFT_TYPES if ac["code"] in fleet_codes]
    else:
        candidate_types = AIRCRAFT_TYPES

    if not candidate_types:
        candidate_types = AIRCRAFT_TYPES

    for ac in sorted(candidate_types, key=lambda x: x["seats"]):
        if estimated_pax <= ac["seats"]:
            return ac["code"]
    return sorted(candidate_types, key=lambda x: x["seats"])[-1]["code"]


def get_aircraft_seat_capacity(aircraft_code: str) -> int:
    """Return a typical seat count proxy for common aircraft ICAO/IATA equipment codes."""
    code = str(aircraft_code or "").strip().upper()
    return int(AIRCRAFT_SEAT_MAP.get(code) or 0)
