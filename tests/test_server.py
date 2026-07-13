"""Tests for HTTP API handlers."""

import json
import threading
from http.client import HTTPConnection

import pytest

import chess_ai
from chess_ai.server import ChessAPIHandler, create_server


@pytest.fixture
def api():
    """Start a local server on an ephemeral port for the duration of the test."""
    ChessAPIHandler.game = ChessAPIHandler.game.__class__()
    server = create_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    conn = HTTPConnection("127.0.0.1", port, timeout=10)

    def request(method: str, path: str, body: dict | None = None) -> dict:
        if body is not None:
            payload = json.dumps(body)
            conn.request(method, path, body=payload, headers={"Content-Type": "application/json"})
        else:
            conn.request(method, path)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        data["_status"] = resp.status
        return data

    yield {"request": request, "port": port}

    conn.close()
    server.shutdown()
    thread.join(timeout=2)


def test_get_state(api) -> None:
    data = api["request"]("GET", "/api/state")
    assert data["ok"]
    assert data["state"]["turn"] == "white"


def test_new_game(api) -> None:
    data = api["request"]("POST", "/api/new", {"player_color": "black", "difficulty": "hard"})
    assert data["ok"]
    assert data["state"]["player_color"] == "black"
    assert data["state"]["difficulty"] == "hard"
    assert data["state"]["is_ai_turn"]


def test_move_endpoint(api) -> None:
    data = api["request"]("POST", "/api/move", {"from": "e2", "to": "e4"})
    assert data["ok"]
    assert data["state"]["last_move"]["uci"] == "e2e4"


def test_illegal_move_rejected(api) -> None:
    data = api["request"]("POST", "/api/move", {"from": "e2", "to": "e5"})
    assert not data["ok"]
    assert data["_status"] == 400


def test_ai_move_after_player(api) -> None:
    api["request"]("POST", "/api/move", {"from": "e2", "to": "e4"})
    data = api["request"]("POST", "/api/ai-move", {})
    assert data["ok"]
    assert data["state"]["last_move"] is not None


def test_undo(api) -> None:
    api["request"]("POST", "/api/move", {"from": "e2", "to": "e4"})
    data = api["request"]("POST", "/api/undo", {})
    assert data["ok"]
    assert data["state"]["last_move"] is None


def test_static_index(api) -> None:
    conn = HTTPConnection("127.0.0.1", api["port"], timeout=5)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    assert "Chess AI" in resp.read().decode()
    conn.close()


def test_import_package() -> None:
    assert chess_ai.__version__