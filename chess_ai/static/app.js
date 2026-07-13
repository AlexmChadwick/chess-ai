/**
 * Chess AI — browser client
 */

const API = {
  async getState() {
    const res = await fetch("/api/state");
    return res.json();
  },
  async newGame(playerColor, difficulty) {
    const res = await fetch("/api/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_color: playerColor, difficulty }),
    });
    return res.json();
  },
  async move(from, to, promotion) {
    const body = { from, to };
    if (promotion) body.promotion = promotion;
    const res = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  },
  async aiMove() {
    const res = await fetch("/api/ai-move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    return res.json();
  },
  async undo() {
    const res = await fetch("/api/undo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    return res.json();
  },
};

const FILES = "abcdefgh";
const RANKS = "87654321";

let state = null;
let selectedSquare = null;
let legalTargets = [];
let pendingPromotion = null;
let isBusy = false;
let flipped = false;

const boardEl = document.getElementById("board");
const statusText = document.getElementById("status-text");
const turnIndicator = document.getElementById("turn-indicator");
const btnNew = document.getElementById("btn-new");
const btnUndo = document.getElementById("btn-undo");
const selectDifficulty = document.getElementById("difficulty");
const selectColor = document.getElementById("player-color");
const promoModal = document.getElementById("promotion-modal");
const gameOverModal = document.getElementById("game-over-modal");
const gameOverTitle = document.getElementById("game-over-title");
const gameOverMessage = document.getElementById("game-over-message");
const btnGameOverNew = document.getElementById("btn-game-over-new");

function squareName(file, rank) {
  return FILES[file] + RANKS[rank];
}

function parseSquare(name) {
  return { file: FILES.indexOf(name[0]), rank: RANKS.indexOf(name[1]) };
}

function displayCoord(file, rank) {
  if (flipped) {
    return {
      file: FILES[7 - file],
      rank: String(8 - rank),
    };
  }
  return { file: FILES[file], rank: RANKS[rank] };
}

function renderBoard() {
  boardEl.innerHTML = "";
  if (!state) return;

  const matrix = state.board;
  const lastFrom = state.last_move?.from;
  const lastTo = state.last_move?.to;

  for (let dr = 0; dr < 8; dr++) {
    for (let df = 0; df < 8; df++) {
      const rank = flipped ? 7 - dr : dr;
      const file = flipped ? 7 - df : df;
      const sq = squareName(file, rank);
      const piece = flipped ? matrix[7 - dr][7 - df] : matrix[dr][df];

      const div = document.createElement("div");
      div.className = "square";
      div.classList.add((file + rank) % 2 === 0 ? "light" : "dark");
      div.dataset.square = sq;

      if (sq === selectedSquare) div.classList.add("selected");
      if (sq === lastFrom || sq === lastTo) div.classList.add("last-move");

      const target = legalTargets.find((t) => t.to === sq);
      if (target) {
        div.classList.add(piece ? "legal-capture" : "legal-target");
      }

      if (state.in_check) {
        const kingPiece = state.turn === "white" ? "♔" : "♚";
        if (piece === kingPiece) div.classList.add("in-check");
      }

      if (piece) {
        const span = document.createElement("span");
        span.className = "piece";
        span.textContent = piece;
        span.draggable = isPlayerPiece(piece) && state.is_player_turn && !state.is_game_over;
        div.appendChild(span);
      }

      const coord = displayCoord(file, rank);
      if (df === 7) {
        const rankLabel = document.createElement("span");
        rankLabel.className = "coord rank";
        rankLabel.textContent = coord.rank;
        div.appendChild(rankLabel);
      }
      if (dr === 7) {
        const fileLabel = document.createElement("span");
        fileLabel.className = "coord file";
        fileLabel.textContent = coord.file;
        div.appendChild(fileLabel);
      }

      div.addEventListener("click", () => onSquareClick(sq));
      div.addEventListener("dragover", (e) => {
        e.preventDefault();
        div.classList.add("drag-over");
      });
      div.addEventListener("dragleave", () => div.classList.remove("drag-over"));
      div.addEventListener("drop", (e) => {
        e.preventDefault();
        div.classList.remove("drag-over");
        const from = e.dataTransfer.getData("text/plain");
        if (from) attemptMove(from, sq);
      });

      const pieceEl = div.querySelector(".piece");
      if (pieceEl) {
        pieceEl.addEventListener("dragstart", (e) => {
          e.dataTransfer.setData("text/plain", sq);
          selectSquare(sq);
        });
      }

      boardEl.appendChild(div);
    }
  }
}

function isPlayerPiece(piece) {
  const isWhite = "♔♕♖♗♘♙".includes(piece);
  return state.player_color === "white" ? isWhite : !isWhite;
}

function selectSquare(sq) {
  if (isBusy || !state || state.is_game_over || !state.is_player_turn) return;

  const movesFrom = state.legal_moves.filter((m) => m.from === sq);
  if (movesFrom.length === 0) {
    selectedSquare = null;
    legalTargets = [];
    renderBoard();
    return;
  }

  selectedSquare = sq;
  legalTargets = movesFrom;
  renderBoard();
}

function onSquareClick(sq) {
  if (isBusy || !state || state.is_game_over || !state.is_player_turn) return;

  if (selectedSquare === sq) {
    selectedSquare = null;
    legalTargets = [];
    renderBoard();
    return;
  }

  if (selectedSquare) {
    const move = legalTargets.find((m) => m.to === sq);
    if (move) {
      // Do not auto-pick promotion — show the picker when needed.
      attemptMove(selectedSquare, sq);
      return;
    }
  }

  selectSquare(sq);
}

function needsPromotion(from, to) {
  const moves = state.legal_moves.filter((m) => m.from === from && m.to === to);
  return moves.some((m) => m.promotion);
}

async function attemptMove(from, to, promotion) {
  if (needsPromotion(from, to) && !promotion) {
    pendingPromotion = { from, to };
    promoModal.classList.remove("hidden");
    return;
  }

  selectedSquare = null;
  legalTargets = [];
  isBusy = true;
  renderBoard();
  updateStatus("Making move…");

  const result = await API.move(from, to, promotion);
  if (!result.ok) {
    updateStatus(result.error || "Invalid move");
    isBusy = false;
    renderBoard();
    return;
  }

  await applyState(result.state);
  isBusy = false;

  if (state.is_ai_turn) {
    await requestAiMove();
  }
}

async function requestAiMove() {
  isBusy = true;
  updateStatus("AI is thinking…");
  renderBoard();

  const result = await API.aiMove();
  isBusy = false;

  if (!result.ok) {
    updateStatus(result.error || "AI move failed");
    renderBoard();
    return;
  }

  await applyState(result.state);
}

function updateStatus(message) {
  statusText.textContent = message;
}

function updateTurnIndicator() {
  if (!state) return;

  turnIndicator.classList.remove("in-check");

  if (state.is_game_over) {
    turnIndicator.textContent = "";
    return;
  }

  let text = state.is_player_turn ? "Your turn" : "AI is thinking…";
  if (state.in_check) {
    text += " — Check!";
    turnIndicator.classList.add("in-check");
  }
  turnIndicator.textContent = text;
}

function showGameOver() {
  if (!state?.is_game_over || !state.result) return;

  const { reason, winner } = state.result;
  let title = "Game Over";
  let message = "";

  if (reason === "checkmate") {
    title = "Checkmate!";
    const winnerName = winner === state.player_color ? "You win!" : "AI wins!";
    message = winnerName;
  } else if (reason === "stalemate") {
    title = "Stalemate";
    message = "Draw by stalemate.";
  } else {
    title = "Draw";
    const labels = {
      insufficient_material: "Insufficient material.",
      fifty_move_rule: "Fifty-move rule.",
      threefold_repetition: "Threefold repetition.",
    };
    message = labels[reason] || "The game is a draw.";
  }

  gameOverTitle.textContent = title;
  gameOverMessage.textContent = message;
  gameOverModal.classList.remove("hidden");
}

async function applyState(newState) {
  state = newState;
  flipped = state.player_color === "black";
  btnUndo.disabled = !state.can_undo || isBusy;

  if (state.is_game_over) {
    showGameOver();
    updateStatus("Game over");
  } else if (state.is_player_turn) {
    updateStatus("Your turn — select a piece to move");
  } else {
    updateStatus("Waiting for AI…");
  }

  updateTurnIndicator();
  renderBoard();
}

async function startNewGame() {
  gameOverModal.classList.add("hidden");
  selectedSquare = null;
  legalTargets = [];
  isBusy = true;

  const playerColor = selectColor.value;
  const difficulty = selectDifficulty.value;

  const result = await API.newGame(playerColor, difficulty);
  isBusy = false;

  if (!result.ok) {
    updateStatus(result.error || "Failed to start game");
    return;
  }

  await applyState(result.state);

  if (state.is_ai_turn) {
    await requestAiMove();
  }
}

async function doUndo() {
  isBusy = true;
  const result = await API.undo();
  isBusy = false;

  if (!result.ok) {
    updateStatus(result.error || "Nothing to undo");
    return;
  }

  selectedSquare = null;
  legalTargets = [];
  gameOverModal.classList.add("hidden");
  await applyState(result.state);
}

// Promotion picker
document.querySelectorAll(".promo-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    promoModal.classList.add("hidden");
    if (!pendingPromotion) return;
    const { from, to } = pendingPromotion;
    const piece = btn.dataset.piece;
    pendingPromotion = null;
    await attemptMove(from, to, piece);
  });
});

btnNew.addEventListener("click", startNewGame);
btnGameOverNew.addEventListener("click", startNewGame);
btnUndo.addEventListener("click", doUndo);

// Boot
(async () => {
  const result = await API.getState();
  if (result.ok) {
    selectDifficulty.value = result.state.difficulty;
    selectColor.value = result.state.player_color;
    await applyState(result.state);
    if (state.is_ai_turn) await requestAiMove();
  } else {
    await startNewGame();
  }
})();