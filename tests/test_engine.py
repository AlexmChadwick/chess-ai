"""Tests for chess game engine wrapper."""

import chess
import pytest

from chess_ai.engine import ChessGame, Difficulty, PlayerColor


@pytest.fixture
def game() -> ChessGame:
    g = ChessGame()
    g.new_game()
    return g


def test_new_game_starts_at_initial_position(game: ChessGame) -> None:
    assert game.board.fen().startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
    assert game.is_player_turn()
    assert not game.is_ai_turn()


def test_legal_opening_move(game: ChessGame) -> None:
    move = game.make_move("e2", "e4")
    assert move.uci() == "e2e4"
    assert game.board.piece_at(chess.E4) is not None


def test_illegal_move_rejected(game: ChessGame) -> None:
    with pytest.raises(ValueError, match="Illegal move"):
        game.make_move("e2", "e5")


def test_undo_restores_position(game: ChessGame) -> None:
    fen_before = game.board.fen()
    game.make_move("e2", "e4")
    assert game.undo()
    assert game.board.fen() == fen_before


def test_undo_empty_stack(game: ChessGame) -> None:
    assert not game.undo()


def test_play_as_black_ai_moves_first() -> None:
    game = ChessGame()
    game.new_game(player_color=PlayerColor.BLACK)
    assert not game.is_player_turn()
    assert game.is_ai_turn()


def test_to_dict_shape(game: ChessGame) -> None:
    data = game.to_dict()
    assert len(data["board"]) == 8
    assert len(data["board"][0]) == 8
    assert data["turn"] == "white"
    assert data["player_color"] == "white"
    assert data["difficulty"] == "medium"
    assert data["is_game_over"] is False
    assert len(data["legal_moves"]) == 20


def test_checkmate_detection() -> None:
    game = ChessGame()
    game.board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
    result = game.get_result()
    assert result is not None
    assert result["reason"] == "checkmate"
    assert result["winner"] == "black"


def test_stalemate_detection() -> None:
    game = ChessGame()
    game.board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    result = game.get_result()
    assert result is not None
    assert result["reason"] == "stalemate"


def test_promotion_move() -> None:
    game = ChessGame()
    game.board = chess.Board("8/P7/8/8/8/8/8/4k2K w - - 0 1")
    move = game.make_move("a7", "a8", promotion="q")
    assert move.promotion == chess.QUEEN