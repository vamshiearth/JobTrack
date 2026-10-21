from dataclasses import dataclass
import re


class InvalidBoardToken(ValueError):
    pass


@dataclass(frozen=True)
class GreenhouseBoard:
    token: str
    company_name: str


_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,127}$")


class GreenhouseBoardRegistry:
    def __init__(self, boards: tuple[GreenhouseBoard, ...] = ()):
        self._boards = {board.token: board for board in boards}

    def resolve(self, token: str) -> GreenhouseBoard:
        board = self._boards.get(token)
        if board is None or not _TOKEN_PATTERN.fullmatch(token):
            raise InvalidBoardToken("board token is not registered")
        return board

    def add(self, board: GreenhouseBoard) -> None:
        if not _TOKEN_PATTERN.fullmatch(board.token):
            raise InvalidBoardToken("board token has an invalid format")
        self._boards[board.token] = board
