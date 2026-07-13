"""Chess game state wrapper around the ``chess`` library."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import chess


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PlayerColor(str, Enum):
    WHITE = "white"
    BLACK = "black"


PIECE_UNICODE = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",
    "k": "♚",
    "q": "♛",
    "r": "♜",
    "b": "♝",
    "n": "♞",
    "p": "♟",
}


@dataclass
class GameConfig:
    player_color: PlayerColor = PlayerColor.WHITE
    difficulty: Difficulty = Difficulty.MEDIUM


@dataclass
class ChessGame:
    """Mutable game session with undo history."""

    config: GameConfig = field(default_factory=GameConfig)
    board: chess.Board = field(default_factory=chess.Board)
    _undo_stack: list[chess.Board] = field(default_factory=list, repr=False)

    def new_game(
        self,
        player_color: PlayerColor | str = PlayerColor.WHITE,
        difficulty: Difficulty | str = Difficulty.MEDIUM,
    ) -> None:
        self.config = GameConfig(
            player_color=PlayerColor(player_color),
            difficulty=Difficulty(difficulty),
        )
        self.board = chess.Board()
        self._undo_stack.clear()

    def is_player_turn(self) -> bool:
        turn = chess.WHITE if self.config.player_color == PlayerColor.WHITE else chess.BLACK
        return self.board.turn == turn

    def is_ai_turn(self) -> bool:
        return not self.is_player_turn() and not self.board.is_game_over()

    def legal_moves_from(self, square_name: str) -> list[chess.Move]:
        square = chess.parse_square(square_name)
        return [m for m in self.board.legal_moves if m.from_square == square]

    def make_move(
        self,
        from_square: str,
        to_square: str,
        promotion: str | None = None,
    ) -> chess.Move:
        move = self._parse_move(from_square, to_square, promotion)
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move: {from_square}{to_square}{promotion or ''}")
        self._undo_stack.append(self.board.copy())
        self.board.push(move)
        return move

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self.board = self._undo_stack.pop()
        return True

    def get_result(self) -> dict[str, Any] | None:
        if not self.board.is_game_over():
            return None

        outcome = self.board.outcome()
        if outcome is None:
            return {"status": "draw", "reason": "unknown", "winner": None}

        reason_map = {
            chess.Termination.CHECKMATE: "checkmate",
            chess.Termination.STALEMATE: "stalemate",
            chess.Termination.INSUFFICIENT_MATERIAL: "insufficient_material",
            chess.Termination.FIFTY_MOVES: "fifty_move_rule",
            chess.Termination.THREEFOLD_REPETITION: "threefold_repetition",
        }
        reason = reason_map.get(outcome.termination, "draw")
        winner = None
        if outcome.winner is not None:
            winner = "white" if outcome.winner == chess.WHITE else "black"

        return {"status": "game_over", "reason": reason, "winner": winner}

    def to_dict(self, last_move: chess.Move | None = None) -> dict[str, Any]:
        result = self.get_result()
        legal_moves = []
        for move in self.board.legal_moves:
            legal_moves.append({
                "from": chess.square_name(move.from_square),
                "to": chess.square_name(move.to_square),
                "promotion": chess.piece_symbol(move.promotion) if move.promotion else None,
                "uci": move.uci(),
            })

        last_move_data = None
        if last_move is not None:
            last_move_data = {
                "from": chess.square_name(last_move.from_square),
                "to": chess.square_name(last_move.to_square),
                "uci": last_move.uci(),
            }
        elif self.board.move_stack:
            prev = self.board.peek()
            last_move_data = {
                "from": chess.square_name(prev.from_square),
                "to": chess.square_name(prev.to_square),
                "uci": prev.uci(),
            }

        return {
            "fen": self.board.fen(),
            "board": self._board_matrix(),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "player_color": self.config.player_color.value,
            "difficulty": self.config.difficulty.value,
            "legal_moves": legal_moves,
            "last_move": last_move_data,
            "in_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_stalemate": self.board.is_stalemate(),
            "is_game_over": self.board.is_game_over(),
            "is_player_turn": self.is_player_turn(),
            "is_ai_turn": self.is_ai_turn(),
            "result": result,
            "can_undo": len(self._undo_stack) > 0,
            "halfmove_clock": self.board.halfmove_clock,
            "fullmove_number": self.board.fullmove_number,
        }

    def _board_matrix(self) -> list[list[str | None]]:
        matrix: list[list[str | None]] = []
        for rank in range(7, -1, -1):
            row: list[str | None] = []
            for file in range(8):
                piece = self.board.piece_at(chess.square(file, rank))
                if piece is None:
                    row.append(None)
                else:
                    symbol = piece.symbol()
                    row.append(PIECE_UNICODE.get(symbol, symbol))
            matrix.append(row)
        return matrix

    @staticmethod
    def _parse_move(from_square: str, to_square: str, promotion: str | None) -> chess.Move:
        uci = from_square + to_square
        if promotion:
            uci += promotion.lower()
        return chess.Move.from_uci(uci)