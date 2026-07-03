"""Static configuration data used by the FlightScope backend.

Copied verbatim from apps/app_flightscope_unified.py (REGION_BBOX, AIRLINES,
PLANNING_HORIZON_OPTIONS). Pure data, no behavior.
"""


REGION_BBOX = {
    "Global": {"lamin": -60.0, "lomin": -180.0, "lamax": 85.0, "lomax": 180.0},
    "Europe": {"lamin": 35.0, "lomin": -10.0, "lamax": 71.0, "lomax": 40.0},
    "Asia": {"lamin": -10.0, "lomin": 25.0, "lamax": 80.0, "lomax": 180.0},
    "North America": {"lamin": 7.0, "lomin": -170.0, "lamax": 83.0, "lomax": -50.0},
    "South America": {"lamin": -56.0, "lomin": -82.0, "lamax": 13.0, "lomax": -34.0},
    "Africa": {"lamin": -35.0, "lomin": -20.0, "lamax": 38.0, "lomax": 52.0},
    "Oceania": {"lamin": -50.0, "lomin": 110.0, "lamax": 0.0, "lomax": 180.0},
}

AIRLINES = {
    # Europe
    "LH": {"name": "Lufthansa", "base": "Munich (MUC)", "region": "Europe"},
    "BA": {"name": "British Airways", "base": "London (LHR)", "region": "Europe"},
    "AF": {"name": "Air France", "base": "Paris (CDG)", "region": "Europe"},
    "KL": {"name": "KLM", "base": "Amsterdam (AMS)", "region": "Europe"},
    "IB": {"name": "Iberia", "base": "Madrid (MAD)", "region": "Europe"},
    "VY": {"name": "Vueling", "base": "Barcelona (BCN)", "region": "Europe"},
    "U2": {"name": "easyJet", "base": "London (LGW)", "region": "Europe"},
    "OS": {"name": "Austrian", "base": "Vienna (VIE)", "region": "Europe"},
    "TK": {"name": "Turkish Airlines", "base": "Istanbul (IST)", "region": "Europe"},
    "AZ": {"name": "ITA Airways", "base": "Rome (FCO)", "region": "Europe"},
    # Asia
    "CX": {"name": "Cathay Pacific", "base": "Hong Kong (HKG)", "region": "Asia"},
    "SQ": {"name": "Singapore Airlines", "base": "Singapore (SIN)", "region": "Asia"},
    "NH": {"name": "ANA", "base": "Tokyo (NRT)", "region": "Asia"},
    "JL": {"name": "Japan Airlines", "base": "Tokyo (NRT)", "region": "Asia"},
    "KE": {"name": "Korean Air", "base": "Seoul (ICN)", "region": "Asia"},
    "MH": {"name": "Malaysia Airlines", "base": "Kuala Lumpur (KUL)", "region": "Asia"},
    "TG": {"name": "Thai Airways", "base": "Bangkok (BKK)", "region": "Asia"},
    "CA": {"name": "Air China", "base": "Beijing (PEK)", "region": "Asia"},
    "MU": {"name": "China Eastern", "base": "Shanghai (PVG)", "region": "Asia"},
    "AI": {"name": "Air India", "base": "Delhi (DEL)", "region": "Asia"},
    # North America
    "AA": {"name": "American Airlines", "base": "Dallas (DFW)", "region": "North America"},
    "DL": {"name": "Delta Air Lines", "base": "Atlanta (ATL)", "region": "North America"},
    "UA": {"name": "United Airlines", "base": "Chicago (ORD)", "region": "North America"},
    "WN": {"name": "Southwest Airlines", "base": "Dallas (DAL)", "region": "North America"},
    "AC": {"name": "Air Canada", "base": "Toronto (YYZ)", "region": "North America"},
    "B6": {"name": "JetBlue", "base": "New York (JFK)", "region": "North America"},
    # South America
    "LA": {"name": "LATAM Airlines", "base": "Santiago (SCL)", "region": "South America"},
    "G3": {"name": "Gol Airlines", "base": "São Paulo (GRU)", "region": "South America"},
    "AR": {"name": "Aerolíneas Argentinas", "base": "Buenos Aires (EZE)", "region": "South America"},
    "CM": {"name": "Copa Airlines", "base": "Panama City (PTY)", "region": "South America"},
    # Africa
    "ET": {"name": "Ethiopian Airlines", "base": "Addis Ababa (ADD)", "region": "Africa"},
    "SA": {"name": "South African Airways", "base": "Johannesburg (JNB)", "region": "Africa"},
    "MS": {"name": "EgyptAir", "base": "Cairo (CAI)", "region": "Africa"},
    "AT": {"name": "Royal Air Maroc", "base": "Casablanca (CMN)", "region": "Africa"},
    # Oceania
    "QF": {"name": "Qantas", "base": "Sydney (SYD)", "region": "Oceania"},
    "NZ": {"name": "Air New Zealand", "base": "Auckland (AKL)", "region": "Oceania"},
    "VA": {"name": "Virgin Australia", "base": "Brisbane (BNE)", "region": "Oceania"},
}

PLANNING_HORIZON_OPTIONS = {
    "Next 1 month": 1,
    "Next 3 months": 3,
    "Next 6 months": 6,
}
