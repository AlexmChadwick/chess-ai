"""Entry point: ``python -m chess_ai``."""

from chess_ai.server import main as _main


def main() -> None:
    _main()


if __name__ == "__main__":
    main()