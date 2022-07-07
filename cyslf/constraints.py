from typing import TYPE_CHECKING, List

import pandas as pd


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
    # TODO: this type check shouldn't be necessary if we fix the input type handling
    return (
        not pd.isnull(move.player.unavailable_days)
        and move.team_to.practice_day in move.player.unavailable_days
    )
