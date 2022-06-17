from typing import List

from .models import Move


def breaks_constraints(moves: List[Move]) -> bool:
    for move in moves:
        if move.team_to.practice_day in move.player.unavailable_days:
            return True
        if move.player.frozen:
            return True
    return False
