"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score.

TODOs:
    * the biggest performance boost we'd get is precomputing team scores and updating that on
    Team.add_player and Team.remove_player. Right now, depth=3 is infeasible past like 100 players.
"""

from typing import Dict, Optional

import numpy as np

from .models import League
from .utils import get_distance, max_distance


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


SCORER_MAP = {
    "skill": score_skill,
    "grade": score_grade,
    "size": score_size,
    "convenience": score_convenience,
}

# COMPOSITE SCORER

DEFAULT_WEIGHTS = {
    "skill": 0.3,
    "grade": 0.3,
    "size": 0.3,
    "convenience": 0.1,
}


def score_league(
    league: League, weights: Optional[Dict[str, float]] = None, verbose=False
) -> float:
    if weights is None:
        weights = DEFAULT_WEIGHTS
    score: float = 0
    total_weight: float = 0
    s = ""
    for scorer_key, weight in weights.items():
        scorer = SCORER_MAP[scorer_key]
        score += weight * scorer(league)
        total_weight += weight
        if verbose:
            s += f"{scorer(league):.3f} "
    if verbose:
        print(s, list(weights.keys()))
    return score / total_weight
