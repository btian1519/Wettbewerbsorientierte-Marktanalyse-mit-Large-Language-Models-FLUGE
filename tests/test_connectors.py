from __future__ import annotations

import pytest

from ingestion.connectors import AircraftDbConnector, AirLabsConnector, AmadeusConnector
from ingestion.connectors.base import AuthError, ConnectorError
from shared.config import Settings


class _Resp:
    def __init__(self, status: int, payload, text: str = ""):
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _Session:
    def __init__(self, resp: _Resp):
        self._resp = resp
        self.calls: list = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        return self._resp


def _airlabs(monkeypatch, resp: _Resp) -> AirLabsConnector:
    monkeypatch.setenv("AIRLABS_API_KEY", "test-key")
    return AirLabsConnector(Settings(), session=_Session(resp))


def test_airlabs_parses_routes(monkeypatch):
    payload = {"response": [
        {"airline_iata": "LH", "flight_number": "400", "dep_iata": "fra", "arr_iata": "jfk",
         "days": ["mon", "wed", "fri"], "aircraft_icao": "A333"},
        {"airline_iata": "LH", "dep_iata": "FRA", "arr_iata": "MUC", "days": ["mon", "tue"]},
        {"dep_iata": "FRA", "arr_iata": "XXX"},  # missing airline -> skipped
    ]}
    conn = _airlabs(monkeypatch, _Resp(200, payload))
    routes = conn.fetch_routes("FRA")
    assert len(routes) == 2
    r0 = routes[0]
    assert r0.airline_iata == "LH" and r0.origin_iata == "FRA" and r0.dest_iata == "JFK"
    assert r0.frequency == 3 and r0.aircraft_type == "A333"


def test_airlabs_auth_required(monkeypatch):
    monkeypatch.delenv("AIRLABS_API_KEY", raising=False)
    conn = AirLabsConnector(Settings(), session=_Session(_Resp(200, {"response": []})))
    assert conn.is_configured() is False
    with pytest.raises(AuthError):
        conn.fetch_routes("FRA")


def test_airlabs_surfaces_api_error_body(monkeypatch):
    # AirLabs returns HTTP 200 with an error object for restricted endpoints.
    payload = {"error": {"message": "Api function is not found", "code": "not_found"}}
    conn = _airlabs(monkeypatch, _Resp(200, payload))
    with pytest.raises(ConnectorError, match="Api function is not found"):
        conn.fetch_routes("FRA")


def test_airlabs_http_error_maps_to_connector_error(monkeypatch):
    conn = _airlabs(monkeypatch, _Resp(400, None, text="bad request"))
    with pytest.raises(ConnectorError):
        conn.fetch_routes("FRA")


def test_airlabs_401_is_auth_error(monkeypatch):
    conn = _airlabs(monkeypatch, _Resp(401, None))
    conn.max_attempts = 1
    with pytest.raises(AuthError):
        conn.fetch_routes("FRA")


def test_aircraft_seats_lookup():
    ac = AircraftDbConnector(Settings())
    assert ac.seats_for("A320") == 180
    assert ac.seats_for("B77W") == 350
    assert ac.seats_for("UNKNOWN") == 180  # fallback
    assert ac.seats_for(None) == 180


def test_amadeus_not_configured(monkeypatch):
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)
    conn = AmadeusConnector(Settings())
    assert conn.is_configured() is False
