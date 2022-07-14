from typing import TYPE_CHECKING, List


if TYPE_CHECKING:
    from .models import Move


def breaks_constraints(moves: List["Move"]) -> bool:
    for move in moves:
        if breaks_practice_constraint(move):
            return True
        if move.player.frozen:
            return True
    return False


def breaks_practice_constraint(move: "Move") -> bool:
    return (
        move.team_to is None
        or move.team_to.practice_day in move.player.unavailable_days
    )
