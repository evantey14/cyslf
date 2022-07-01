from typing import List

import pandas as pd

from .models import Move


def breaks_constraints(moves: List[Move]) -> bool:
    for move in moves:
        # TODO: this type check shouldn't be necessary if we fix the input type handling
        if (
            not pd.isnull(move.player.unavailable_days)
            and move.team_to.practice_day in move.player.unavailable_days
        ):
            return True
        if move.player.frozen:
            return True
    return False
