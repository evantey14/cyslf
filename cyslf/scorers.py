"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score.

TODOs:
    * the biggest performance boost we'd get is precomputing team scores and updating that on
    Team.add_player and Team.remove_player. Right now, depth=3 is infeasible past like 100 players.
"""

from typing import Dict, Optional

from .models import League
from .utils import MAX_DISTANCE, get_distance


# CONVENIENCE SCORERS
def score_practice_day(league: League) -> float:
    total_matches = 0
    for team in league.teams:
        practice_day = team.practice_day
        matches = sum(
            [1 if practice_day in p.preferred_days else 0 for p in team.players]
        )
        total_matches += matches
    return total_matches / league.size


def score_location(league: League) -> float:
    score = 1
    league_size = league.size
    for team in league.teams:
        t_lat, t_long = team.latitude, team.longitude
        scaled_distances = [
            min(
                MAX_DISTANCE,
                get_distance(player.latitude, player.longitude, t_lat, t_long),
            )
            / league_size
            for player in team.players
        ]
        score -= sum(scaled_distances)
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
    "location": score_location,
    "practice_day": score_practice_day,
}

# COMPOSITE SCORER

DEFAULT_WEIGHTS = {
    "skill": 0.3,
    "grade": 0.3,
    "size": 0.3,
    "location": 0.05,
    "practice_day": 0.05,
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
