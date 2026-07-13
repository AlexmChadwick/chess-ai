One-shotted chess game via Hermes Agent as a proof of concept of a Hermes Coder Profile. Leaving up in case anyone is curious.

# Chess AI

A browser-based chess game with a built-in AI opponent. Pure Python — no native engines, no pygame, no compilers required.

**Architecture:** `chess` library for rules → minimax/alpha-beta AI → stdlib `http.server` REST API → static HTML/CSS/JS frontend.

## Requirements

- Python **3.10+**
- macOS arm64, Linux, or Windows with a modern CPython build

All runtime dependencies are pure-Python wheels. Tested to install cleanly on **macOS arm64** without Xcode or any C compiler.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

For development (includes pytest):

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## Run

```bash
python -m chess_ai
# or
python main.py
```

The server starts at **http://127.0.0.1:8765** by default. Open that URL in any modern browser.

Optional flags:

```bash
python -m chess_ai --port 9000
python -m chess_ai --host 127.0.0.1 --port 8765
```

Press `Ctrl+C` to stop the server.

## How to Play

1. Open the printed URL in your browser.
2. Choose **difficulty** (Easy / Medium / Hard) and whether to play as **White** or **Black**.
3. Click **New Game** to start.
4. **Click** a piece, then click a highlighted square — or **drag-and-drop** pieces.
5. Legal moves are shown as dots (quiet moves) or rings (captures).
6. The last move is highlighted in yellow; the king glows red when in check.
7. When a pawn reaches the back rank, a **promotion picker** appears (Queen, Rook, Bishop, Knight).
8. **Undo** reverts the last half-move.
9. A modal announces checkmate, stalemate, or draw.

### Difficulty

| Level  | Search depth | Notes                          |
|--------|-------------|--------------------------------|
| Easy   | 2           | Occasional random moves (~15%) |
| Medium | 3           | Balanced play                  |
| Hard   | 4           | Stronger tactical play         |

## API

| Method | Path           | Body                                      | Description        |
|--------|----------------|-------------------------------------------|--------------------|
| GET    | `/api/state`   | —                                         | Current game state |
| POST   | `/api/new`     | `{"player_color":"white","difficulty":"medium"}` | New game   |
| POST   | `/api/move`    | `{"from":"e2","to":"e4","promotion":"q"}` | Player move        |
| POST   | `/api/ai-move` | `{}`                                      | AI move            |
| POST   | `/api/undo`    | `{}`                                      | Undo last move     |

## Project Layout

```
chess_ai/
  engine.py      # Game state wrapper (chess.Board)
  ai.py          # Minimax + alpha-beta + evaluation
  server.py      # HTTP server and REST API
  static/        # index.html, style.css, app.js
tests/           # pytest suite
main.py          # Alternate entry point
```

## Test

```bash
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pytest -q
```

## License

MIT
