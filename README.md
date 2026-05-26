# FlightScope AI - Route Recommendation Engine

**Data-driven decision support system for airline route planning using LLM-powered market analysis.**

## Project Overview

FlightScope AI analyzes European aviation market data to recommend the top 3 new flight routes for airlines, including:
- Optimal route selection (origin/destination pairs)
- Estimated passenger volume
- Recommended aircraft type
- Transparent decision rationale

## Quick Start

### Installation

```bash
# Create and activate virtual environment (if not already done)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Applications

**Route Recommendation System (Main App):**
```bash
streamlit run apps/app_route_advisor.py
```

**Data Collection Tool:**
```bash
streamlit run apps/app_collector.py
```

### API Configuration

Data sources require API keys. Copy `config/collector_env.example` to `.env` in the project root (or set system environment variables):

```powershell
$env:AMADEUS_CLIENT_ID="your_id"
$env:AMADEUS_CLIENT_SECRET="your_secret"
$env:AVIATIONSTACK_API_KEY="your_key"
$env:AIRLABS_API_KEY="your_key"
```

`src/collect_sources.py` also supports legacy aliases `AVIATIONSTACK_KEY` and `AIRLABS_KEY`.

### GitHub Safety Checklist

Before pushing to GitHub:
- Never commit `.env` or real API keys
- Rotate any key that was shared in chat/screenshots
- Avoid committing large raw API dumps from `data/raw/`
- Keep only template config in `config/collector_env.example`

## Project Structure

```
.
├── src/                          # Core application modules
│   ├── __init__.py
│   ├── collect_sources.py        # API data collection engine
│   ├── recommendation_engine.py  # Route scoring & recommendation
│   └── route_database.py         # European OD pair database
│
├── apps/                         # Streamlit applications
│   ├── app_route_advisor.py      # Main route recommendation UI
│   └── app_collector.py          # Data collection interface
│
├── data/                         # Data storage
│   ├── raw/                      # Raw API outputs
│   │   ├── opensky/
│   │   ├── amadeus/
│   │   ├── aviationstack/
│   │   └── airlabs/
│   └── processed/                # Processed datasets (future)
│
├── docs/                         # Documentation
│   ├── README_Datenquellen_Template.md
│   ├── Session2_GroupPrep_Flug.md
│   ├── PPT_Slides_Flug_10min.md
│   └── PPT_Slides_Flug_10min_CN.md
│
├── config/                       # Configuration files
│   └── collector_env.example     # API key template
│
├── scripts/                      # Helper & utility scripts
│   ├── generate_ppt.py
│   ├── create_data_source_template.py
│   └── ... (other one-off utilities)
│
├── presentations/                # PowerPoint files
│   ├── FlightScope_AI_RWTH.pptx
│   └── FlightScope_AI_Praesentation.pptx
│
├── requirements.txt              # Python dependencies
├── .streamlit/                   # Streamlit configuration (future)
│   └── config.toml
│
└── README.md                     # This file
```

## Data Sources

### Supported APIs

| Source | Purpose | API Type | Status |
|--------|---------|----------|--------|
| OpenSky | Flight tracking & ops data | REST API | ✓ Free tier available |
| Eurostat | Official aviation statistics | REST API | ✓ No key required |
| Amadeus | Fare & itinerary search | REST API | ○ Requires key |
| Aviationstack | Live flight data | REST API | ○ Requires key |
| AirLabs | Flight tracking | REST API | ○ Requires key |

### Data Schema

See `docs/README_Datenquellen_Template.md` for detailed data collection template and quality guidelines.

## Architecture

### Recommendation Engine

Routes are scored on a weighted combination of:
- **Demand (40%)**: Passenger volume potential from market signals
- **Price Opportunity (30%)**: Revenue attractiveness
- **Competitive Intensity (20%)**: Market gap size
- **Operational Efficiency (10%)**: Distance, turnaround time

### Aircraft Selection

Automatic aircraft recommendation based on estimated passenger volume:
- A319: 100-150 pax
- A320: 150-250 pax
- A321: 250-350 pax

## Development

### Adding New Data Sources

1. Add collection function to `src/collect_sources.py`
2. Define schema in `src/route_database.py` (if needed)
3. Register in `CollectConfig` dataclass
4. Update UI in `apps/app_collector.py`

### Extending Route Database

Edit `src/route_database.py` to:
- Add new OD pairs to `EUROPEAN_OD_ROUTES`
- Adjust aircraft mapping in `AIRCRAFT_TYPES`
- Refine airline homebase mapping in `get_od_by_airline_homebase()`

## Team Responsibilities

| Role | Responsibility | Files |
|------|-----------------|-------|
| **Data Team** | Collect market data via APIs | `data/raw/` |
| **Analysis Team** | Validate route scores & recommendations | `docs/` |
| **Product** | Define airline requirements & parameters | `config/` |

## Dependencies

- `streamlit>=1.34.0` - Web UI framework
- `openpyxl>=3.1.0` - Excel template handling
- (Additional: requests, pandas for production data processing)

See `requirements.txt` for full list.

## License & Attribution

Project: RWTH - Wettbewerbsorientierte Marktanalyse mit Large Language Models (FLUGE)

Academic Use Only - Copyright 2026
