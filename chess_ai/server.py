"""HTTP server with JSON REST API and static file serving."""

from __future__ import annotations

import json
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from chess_ai.ai import choose_move
from chess_ai.engine import ChessGame, Difficulty, PlayerColor

STATIC_DIR = Path(__file__).parent / "static"


class ChessAPIHandler(BaseHTTPRequestHandler):
    """Handle REST API requests and serve static assets."""

    game: ChessGame = ChessGame()
    _lock = threading.Lock()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Quiet by default; enable for debugging.

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self._json_response(self._get_state())
        elif path in ("/", "/index.html"):
            self._serve_static("index.html")
        elif path.startswith("/static/"):
            self._serve_static(path[len("/static/"):])
        else:
            filename = path.lstrip("/")
            if filename and (STATIC_DIR / filename).is_file():
                self._serve_static(filename)
            else:
                self._error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()

        handlers = {
            "/api/new": self._handle_new,
            "/api/move": self._handle_move,
            "/api/ai-move": self._handle_ai_move,
            "/api/undo": self._handle_undo,
        }
        handler = handlers.get(path)
        if handler is None:
            self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        handler(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _get_state(self) -> dict[str, Any]:
        with self._lock:
            return {"ok": True, "state": self.game.to_dict()}

    def _handle_new(self, body: dict[str, Any]) -> None:
        player_color = body.get("player_color", PlayerColor.WHITE.value)
        difficulty = body.get("difficulty", Difficulty.MEDIUM.value)
        try:
            PlayerColor(player_color)
            Difficulty(difficulty)
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with self._lock:
            self.game.new_game(player_color=player_color, difficulty=difficulty)
            state = self.game.to_dict()
        self._json_response({"ok": True, "state": state})

    def _handle_move(self, body: dict[str, Any]) -> None:
        from_sq = body.get("from")
        to_sq = body.get("to")
        promotion = body.get("promotion")

        if not from_sq or not to_sq:
            self._error(HTTPStatus.BAD_REQUEST, "Fields 'from' and 'to' are required")
            return

        with self._lock:
            if not self.game.is_player_turn():
                self._error(HTTPStatus.BAD_REQUEST, "Not the player's turn")
                return
            try:
                move = self.game.make_move(from_sq, to_sq, promotion)
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            state = self.game.to_dict(last_move=move)

        self._json_response({"ok": True, "state": state})

    def _handle_ai_move(self, body: dict[str, Any]) -> None:
        with self._lock:
            if not self.game.is_ai_turn():
                self._error(HTTPStatus.BAD_REQUEST, "Not the AI's turn")
                return
            try:
                move = choose_move(self.game.board, self.game.config.difficulty)
                self.game._undo_stack.append(self.game.board.copy())
                self.game.board.push(move)
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            state = self.game.to_dict(last_move=move)

        self._json_response({"ok": True, "state": state})

    def _handle_undo(self, body: dict[str, Any]) -> None:
        with self._lock:
            if not self.game.undo():
                self._error(HTTPStatus.BAD_REQUEST, "Nothing to undo")
                return
            state = self.game.to_dict()
        self._json_response({"ok": True, "state": state})

    def _json_response(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json_response({"ok": False, "error": message}, status=status)

    def _serve_static(self, filename: str) -> None:
        # Resolve under STATIC_DIR only (block path traversal).
        base = STATIC_DIR.resolve()
        filepath = (STATIC_DIR / filename).resolve()
        try:
            filepath.relative_to(base)
        except ValueError:
            self._error(HTTPStatus.NOT_FOUND, f"File not found: {filename}")
            return
        if not filepath.is_file():
            self._error(HTTPStatus.NOT_FOUND, f"File not found: {filename}")
            return

        content_type, _ = mimetypes.guess_type(str(filepath))
        if content_type is None:
            content_type = "application/octet-stream"

        data = filepath.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), ChessAPIHandler)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_server(host, port)
    url = f"http://{host}:{port}"
    print(f"Chess AI server running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Chess AI — browser-based chess with minimax AI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)