"""Minimax chess engine with alpha-beta pruning and positional evaluation."""

from __future__ import annotations

import random
from typing import Callable

import chess

from chess_ai.engine import Difficulty

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}

# Piece-square tables (from white's perspective; mirrored for black).
PAWN_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]

KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 0, 5, 5, 0, 0, 0,
]

QUEEN_TABLE = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]

KING_MIDDLE_TABLE = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
]

KING_END_TABLE = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]

PIECE_SQUARE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}

DIFFICULTY_DEPTH = {
    Difficulty.EASY: 2,
    Difficulty.MEDIUM: 3,
    Difficulty.HARD: 4,
}


def _is_endgame(board: chess.Board) -> bool:
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(
        board.pieces(chess.QUEEN, chess.BLACK)
    )
    return queens == 0


def _pst_value(board: chess.Board, square: int, piece: chess.Piece) -> int:
    tables = PIECE_SQUARE_TABLES
    if piece.piece_type == chess.KING:
        table = KING_END_TABLE if _is_endgame(board) else KING_MIDDLE_TABLE
    else:
        table = tables[piece.piece_type]

    index = square if piece.color == chess.WHITE else chess.square_mirror(square)
    return table[index]


def evaluate(board: chess.Board) -> int:
    """Return centipawn score from white's perspective."""
    if board.is_checkmate():
        return -30_000 if board.turn == chess.WHITE else 30_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for square, piece in board.piece_map().items():
        sign = 1 if piece.color == chess.WHITE else -1
        score += sign * PIECE_VALUES[piece.piece_type]
        score += sign * _pst_value(board, square, piece)

    # Mobility bonus (lightweight).
    mobility = len(list(board.legal_moves))
    score += (mobility if board.turn == chess.WHITE else -mobility) * 2

    return score


def _move_order_score(board: chess.Board, move: chess.Move) -> int:
    """Heuristic move ordering: captures and checks first."""
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim and attacker:
            score += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
    board.push(move)
    if board.is_check():
        score += 50
    board.pop()
    return score


def _ordered_moves(board: chess.Board) -> list[chess.Move]:
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: _move_order_score(board, m), reverse=True)
    return moves


def minimax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    maximizing: bool,
    evaluate_fn: Callable[[chess.Board], int] = evaluate,
) -> int:
    if depth == 0 or board.is_game_over():
        return evaluate_fn(board)

    if maximizing:
        value = -float("inf")
        for move in _ordered_moves(board):
            board.push(move)
            value = max(value, minimax(board, depth - 1, alpha, beta, False, evaluate_fn))
            board.pop()
            alpha = max(alpha, value)
            if beta <= alpha:
                break
        return int(value)
    else:
        value = float("inf")
        for move in _ordered_moves(board):
            board.push(move)
            value = min(value, minimax(board, depth - 1, alpha, beta, True, evaluate_fn))
            board.pop()
            beta = min(beta, value)
            if beta <= alpha:
                break
        return int(value)


def choose_move(board: chess.Board, difficulty: Difficulty | str) -> chess.Move:
    """Select the best legal move for the side to move."""
    diff = Difficulty(difficulty)
    depth = DIFFICULTY_DEPTH[diff]
    legal = list(board.legal_moves)
    if not legal:
        raise ValueError("No legal moves available")

    if diff == Difficulty.EASY and random.random() < 0.15:
        return random.choice(legal)

    maximizing = board.turn == chess.WHITE
    best_move = legal[0]
    best_score = -float("inf") if maximizing else float("inf")

    for move in _ordered_moves(board):
        board.push(move)
        score = minimax(board, depth - 1, -float("inf"), float("inf"), not maximizing)
        board.pop()

        if maximizing:
            if score > best_score:
                best_score = score
                best_move = move
        else:
            if score < best_score:
                best_score = score
                best_move = move

    return best_move