"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score.
"""

import numpy as np

from .models import League
from .utils import get_distance, max_distance


# TOTAL SCORER
def score_league(league: League):
    return (
        0.25 * score_skill(league)
        + 0.25 * score_grade(league)
        + 0.25 * score_size(league)
        + 0.25 * score_convenience(league)
    )


# CONVENIENCE SCORERS
def score_convenience(league: League):
    score = 1
    for team in league.teams:
        for player in team.players:
            distance = get_distance(player, team)
            if np.isnan(distance):
                continue
            score -= (
                min(max_distance, distance) / 246
            )  # should be over number of players?
    return max(0, score)


# PARITY SCORERS

# TODO: the sigmas shouldn't depend on the current league config?
# Right now it depends on the full league at the time of calculation


def score_size(league: League):
    sizes = [len(team.players) for team in league.teams]
    ideal_size = sum(sizes) / len(sizes)
    # N.B sigma normalizes squared errors. We really only care about expressibility between 0 and 1.
    sigma = 5 * np.std(sizes)
    if sigma == 0:
        return 1
    squared_errors = [(size - ideal_size) ** 2 / sigma for size in sizes]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))


def score_grade(league: League):
    grades = [team.get_grade() for team in league.teams]
    ideal_grade = 3.4  # sum(grades) / len(grades)
    # N.B sigma normalizes squared errors. We really only care about expressibility between 0 and 1.
    sigma = 5 * 0.58  # np.std(grades)
    if sigma == 0:
        return 1
    squared_errors = [(grade - ideal_grade) ** 2 / sigma for grade in grades]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))


def score_skill(league: League):
    # Ideal skill distribution is full equality
    # If we want we could break this down into equality for each tier of player.
    team_skills = [team.get_skill() for team in league.teams]
    ideal_skill = 3.18  # sum(team_skills) / len(team_skills)
    # N.B sigma normalizes squared errors. We really only care about expressibility between 0 and 1.
    sigma = 5 * 1.03  # np.std(team_skills)
    if sigma == 0:
        return 1
    squared_errors = [(skill - ideal_skill) ** 2 / sigma for skill in team_skills]
    return max(0, 1 - sum(squared_errors) / len(squared_errors))
