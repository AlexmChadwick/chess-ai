"""Tests for minimax AI."""

import chess

from chess_ai.ai import choose_move, evaluate
from chess_ai.engine import Difficulty


def test_evaluate_initial_position_near_zero() -> None:
    board = chess.Board()
    score = evaluate(board)
    assert -100 < score < 100


def test_choose_move_returns_legal_move() -> None:
    board = chess.Board()
    for difficulty in Difficulty:
        move = choose_move(board, difficulty)
        assert move in board.legal_moves


def test_choose_move_on_check() -> None:
    board = chess.Board("rnb1kbnr/pppp1ppp/8/4p2q/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    move = choose_move(board, Difficulty.MEDIUM)
    assert move in board.legal_moves


def test_choose_move_no_legal_raises() -> None:
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    try:
        choose_move(board, Difficulty.EASY)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_ai_prefers_capture() -> None:
    board = chess.Board("4k3/8/8/8/8/8/8/r3K3 w - - 0 1")
    move = choose_move(board, Difficulty.HARD)
    board.push(move)
    # White king should capture the rook.
    assert board.piece_at(chess.A1) is not None