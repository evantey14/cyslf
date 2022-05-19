from .constraints import breaks_schedule_constraint
from .models import League, Player
from .scorers import score_league


def find_best_move(player: Player, league: League):  # -> move
    best_move = None
    best_score = -1

    old_team = None
    for team in league.teams:
        if player in team.players:
            old_team = team

    for team in league.teams:
        proposed_move = (player, old_team, team)
        league.apply_moves([proposed_move])
        score = score_league(league)
        # print(f"{score:.3f}", proposed_move)
        breaks_constraint = breaks_schedule_constraint(league)
        league.undo_moves([proposed_move])
        if not breaks_constraint and score > best_score:
            best_score = score
            best_move = proposed_move
    return best_move, best_score


def optimize_player_assignment(player: Player, league: League):
    # N.B. this is pretty inefficient. If we need this to be faster,
    # we could change how the score/checkers work.
    # TODO: probably work in a "depth" argument
    best_move, best_score = find_best_move(player, league)
    moves = [best_move]
    for player in best_move[2].players.copy():
        league.apply_moves([best_move])
        next_best_move, next_best_score = find_best_move(player, league)
        league.undo_moves([best_move])
        if next_best_score > best_score:
            moves = [best_move, next_best_move]
            best_score = next_best_score
    league.apply_moves(moves)
