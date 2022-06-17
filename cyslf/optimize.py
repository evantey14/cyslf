import itertools as it
from typing import List

from .constraints import breaks_constraints
from .models import League, Move, Player
from .scorers import score_league


def find_best_moves(player: Player, league: League, depth: int = 1) -> List[Move]:
    queue = []
    best_moves = []
    best_score = -1
    old_team = None
    for team in league.teams:
        if team == old_team:
            continue
    for team in league.teams:
        queue.append([Move(player=player, team_from=old_team, team_to=team)])

    while len(queue) > 0:
        proposed_moves = queue.pop()
        if breaks_constraints(proposed_moves):
            continue
        league.apply_moves(proposed_moves)
        score = score_league(league)
        league.undo_moves(proposed_moves)
        if score > best_score:
            best_score = score
            best_moves = proposed_moves

        if len(proposed_moves) < depth:
            last_team = proposed_moves[-1].team_to
            for p, t in it.product(last_team.players, league.teams):
                moved_players = [move.player for move in proposed_moves]
                if p in moved_players or t.name == last_team.name:
                    continue
                queue.append(
                    [*proposed_moves, Move(player=p, team_from=last_team, team_to=t)]
                )
    return best_moves
