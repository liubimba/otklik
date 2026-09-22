from enum import Enum


class Board(str, Enum):
    HH_RU = "hh_ru"
    HABR = "habr"
    KWORK = "kwork"


DEFAULT_BOARD = Board.HH_RU
