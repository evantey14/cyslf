"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score.
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
def score_convenience(league: League) -> float:
    score = 1
    for team in league.teams:
        for player in team.players:
            distance = get_distance(
                player.latitude, player.longitude, team.latitude, team.longitude
            )
            if np.isnan(distance):
                continue
            score -= min(max_distance, distance) / league.size
    return max(0, score)


# PARITY SCORERS

# TODO: "ideal" numbers really only need to be calculated once. This could be fixed if these were
# all classes.
# TODO: make a scorer to ensure even spread of top tier players


def score_size(league: League) -> float:
    sizes = [len(team.players) for team in league.teams]
    ideal_size = league.ideal_team_size
    squared_errors = [(size - ideal_size) ** 2 / (ideal_size**2) for size in sizes]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))


def score_grade(league: League) -> float:
    grades = [team.get_grade() for team in league.teams]
    ideal_grade = league.ideal_team_grade
    squared_errors = [
        (grade - ideal_grade) ** 2 / (ideal_grade**2) for grade in grades
    ]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))


def score_skill(league: League) -> float:
    team_skills = [team.get_skill() for team in league.teams]
    ideal_skill = league.ideal_team_skill
    squared_errors = [
        (skill - ideal_skill) ** 2 / (ideal_skill**2) for skill in team_skills
    ]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))
