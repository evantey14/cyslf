import itertools as it
from typing import Dict, List, Optional

from .constraints import breaks_constraints
from .models import League, Move, Player
from .utils import handle_error


def find_best_moves(
    player: Player,
    league: League,
    depth: int = 1,
    weights: Optional[Dict[str, float]] = None,
) -> List[Move]:
    queue = []
    best_moves = []
    best_score: float = -1
    old_team = None 

    # removed this because jason wants locked players who are on incompatible teams to be re-assigned
    # if player.lock: return []
    
    for team in league.teams:
        queue.append([Move(player=player, team_from=old_team, team_to=team)])


    while len(queue) > 0:
        proposed_moves = queue.pop()
        if breaks_constraints(proposed_moves):            
            continue
        league.apply_moves(proposed_moves)
        score = league.scorer.get_score(weights=weights)
        league.undo_moves(proposed_moves)
        if score > best_score:
            best_score = score
            best_moves = proposed_moves

        if len(proposed_moves) < depth:
            last_team = proposed_moves[-1].team_to
            if last_team is None:
                handle_error(
                    f"Proposed move tried to unassign a player, which is not allowed. Please check "
                    f"move proposal creation. Move: {proposed_moves[-1]}", True
                )

            for p, t in it.product(last_team.players, league.teams):
                if p.lock: continue
                moved_players = [move.player for move in proposed_moves]
                if p in moved_players or t.name == last_team.name:
                    continue
                queue.append(
                    [*proposed_moves, Move(player=p, team_from=last_team, team_to=t)]
                )
    if len(best_moves) == 0:
        handle_error(
            f"Failed to place Player {player.first_name} {player.last_name} on a team. This is "
            "likely due to unsatisfiable scheduling constraints (There is no valid team for this player). Please try manually assigning "
            "this player before retrying.", True
        )
    return best_moves
