"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score.

TODOs:
    * the biggest performance boost we'd get is precomputing team scores and updating that on
    Team.add_player and Team.remove_player. Right now, depth=3 is infeasible past like 100 players.
"""

import numpy as np

from .models import League
from .utils import get_distance, max_distance


# TOTAL SCORER
def score_league(league: League) -> float:
    return (
        0.25 * score_skill(league)
        + 0.25 * score_grade(league)
        + 0.25 * score_size(league)
        + 0.25 * score_convenience(league)
    )


# CONVENIENCE SCORERS
# TODO: this is currently the slowest scorer by far. the nan check and the min distance together
# take like 40% of the time.
def score_convenience(league: League) -> float:
    score = 1
    league_size = league.size
    for team in league.teams:
        t_lat, t_long = team.latitude, team.longitude
        for player in team.players:
            p_lat, p_long = player.latitude, player.longitude
            distance = get_distance(p_lat, p_long, t_lat, t_long)
            if np.isnan(distance):
                continue
            score -= min(max_distance, distance) / league_size
    return max(0, score)


# PARITY SCORERS
# TODO: make a scorer to ensure even spread of top tier players
def score_size(league: League) -> float:
    ideal_size = league.ideal_team_size
    squared_errors = [
        (len(team.players) - ideal_size) ** 2 / ideal_size**2 for team in league.teams
    ]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))


def score_grade(league: League) -> float:
    ideal_grade = league.ideal_team_grade
    squared_errors = [
        (team.get_grade() - ideal_grade) ** 2 / (ideal_grade**2)
        for team in league.teams
    ]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))


def score_skill(league: League) -> float:
    ideal_skill = league.ideal_team_skill
    squared_errors = [
        (team.get_skill() - ideal_skill) ** 2 / (ideal_skill**2)
        for team in league.teams
    ]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))
