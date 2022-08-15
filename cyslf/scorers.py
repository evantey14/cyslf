"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score. Each class implicitly
exposes an interface containing:
* update_score_addition(player, team): update internal metrics associated with adding player->team
* update_score_removal(player, team): update internal metrics associated with removing player->team
* get_score(): return a score between 0 and 1
"""

from typing import TYPE_CHECKING, Dict, List, Optional

from .utils import ELITE_PLAYER_SKILL_LEVEL, GOALIE_THRESHOLD


if TYPE_CHECKING:
    from .models import Player, Team


# CONVENIENCE SCORERS
class PracticeDayScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.league_size = len(players)
        self.matches = 0

    def update_score_addition(self, player: "Player", team: "Team"):
        if team.practice_day in player.preferred_days:
            self.matches += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if team.practice_day in player.preferred_days:
            self.matches -= 1

    def get_score(self) -> float:
        return self.matches / self.league_size


class LocationScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.league_size = len(players)
        self.matches = 0

    def update_score_addition(self, player: "Player", team: "Team"):
        if team.location in player.preferred_locations:
            self.matches += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if team.location in player.preferred_locations:
            self.matches -= 1

    def get_score(self) -> float:
        return self.matches / self.league_size


class TeammateScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.league_size = len(players)
        self.friend_matches = 0

    def update_score_addition(self, player: "Player", team: "Team"):
        for p in team.players:
            if f"{p.first_name} {p.last_name}" in player.teammate_requests:
                self.friend_matches += 1
            if f"{player.first_name} {player.last_name}" in p.teammate_requests:
                self.friend_matches += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        for p in team.players:
            if f"{p.first_name} {p.last_name}" in player.teammate_requests:
                self.friend_matches -= 1
            if f"{player.first_name} {player.last_name}" in p.teammate_requests:
                self.friend_matches -= 1

    def get_score(self) -> float:
        return self.friend_matches / self.league_size / 2


# PARITY SCORERS
def _calculate_rmse(values, ideal_value):
    """Calculate the root mean squared error from a list of values and ideal value"""
    squared_errors = [(v - ideal_value) ** 2 for v in values]
    return (sum(squared_errors) / len(squared_errors)) ** 0.5


class SizeScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_players = sum([len(t.players) for t in teams])
        self.team_sizes = {team.name: 0 for team in teams}

    def update_score_addition(self, player: "Player", team: "Team"):
        self.total_players += 1
        self.team_sizes[team.name] += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        self.total_players -= 1
        self.team_sizes[team.name] -= 1

    def get_score(self) -> float:
        ideal_size = self.total_players / len(self.team_sizes)
        rmse = _calculate_rmse(self.team_sizes.values(), ideal_size)
        return max(0, 1 - rmse)


class EliteScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_elite_players = 0
        for t in teams:
            for p in t.players:
                if p.skill == ELITE_PLAYER_SKILL_LEVEL:
                    self.total_elite_players = 0
        self.team_elite_players = {team.name: 0 for team in teams}

    def update_score_addition(self, player: "Player", team: "Team"):
        if player.skill == ELITE_PLAYER_SKILL_LEVEL:
            self.total_elite_players += 1
            self.team_elite_players[team.name] += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if player.skill == ELITE_PLAYER_SKILL_LEVEL:
            self.total_elite_players -= 1
            self.team_elite_players[team.name] -= 1

    def get_score(self) -> float:
        ideal_elite_players = self.total_elite_players / len(self.team_elite_players)
        rmse = _calculate_rmse(self.team_elite_players.values(), ideal_elite_players)
        return max(0, 1 - rmse)


class GradeScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_grade = 0
        self.total_players = 0
        for t in teams:
            for p in t.players:
                self.total_grade += p.grade
                self.total_players += 1

        self.team_grades = {team.name: 0.0 for team in teams}

    def update_score_addition(self, player: "Player", team: "Team"):
        self.total_grade += player.grade
        self.total_players += 1
        self.team_grades[team.name] = (
            len(team.players) * self.team_grades[team.name] + player.grade
        ) / (len(team.players) + 1)

    def update_score_removal(self, player: "Player", team: "Team"):
        self.total_grade -= player.grade
        self.total_players -= 1
        if len(team.players) == 1:
            self.team_grades[team.name] = 0
            return
        self.team_grades[team.name] = (
            len(team.players) * self.team_grades[team.name] - player.grade
        ) / (len(team.players) - 1)

    def get_score(self) -> float:
        ideal_grade = self.total_grade / self.total_players
        rmse = _calculate_rmse(self.team_grades.values(), ideal_grade)
        return max(0, 1 - rmse)


class SkillScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_skill = 0
        self.total_players = 0
        for t in teams:
            for p in t.players:
                self.total_skill += p.skill
                self.total_players += 1
        self.team_skills = {team.name: 0.0 for team in teams}

    def update_score_addition(self, player: "Player", team: "Team"):
        self.total_skill += player.skill
        self.total_players += 1
        self.team_skills[team.name] = (
            len(team.players) * self.team_skills[team.name] + player.skill
        ) / (len(team.players) + 1)

    def update_score_removal(self, player: "Player", team: "Team"):
        self.total_skill -= player.skill
        self.total_players -= 1
        if len(team.players) == 1:
            self.team_skills[team.name] = 0
            return
        self.team_skills[team.name] = (
            len(team.players) * self.team_skills[team.name] - player.skill
        ) / (len(team.players) - 1)

    def get_score(self) -> float:
        ideal_skill = self.total_skill / self.total_players
        rmse = _calculate_rmse(self.team_skills.values(), ideal_skill)
        return max(0, 1 - rmse)


class GoalieScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_goalies = 0
        for t in teams:
            for p in t.players:
                if p.skill <= GOALIE_THRESHOLD:
                    self.total_goalies = 0

        self.team_goalies = {team.name: 0 for team in teams}

    def update_score_addition(self, player: "Player", team: "Team"):
        if player.goalie_skill <= GOALIE_THRESHOLD:
            self.total_goalies += 1
            self.team_goalies[team.name] += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if player.goalie_skill <= GOALIE_THRESHOLD:
            self.total_goalies -= 1
            self.team_goalies[team.name] -= 1

    def get_score(self) -> float:
        ideal_goalies = self.total_goalies / len(self.team_goalies)
        rmse = _calculate_rmse(self.team_goalies.values(), ideal_goalies)
        return max(0, 1 - rmse)


SCORER_MAP = {
    "skill": SkillScorer,
    "grade": GradeScorer,
    "size": SizeScorer,
    "location": LocationScorer,
    "practice_day": PracticeDayScorer,
    "elite": EliteScorer,
    "teammate": TeammateScorer,
    "goalie": GoalieScorer,
}

DEFAULT_WEIGHTS = {
    "skill": 0.3,
    "grade": 0.3,
    "size": 0.15,
    "location": 0.05,
    "practice_day": 0.05,
    "elite": 0.15,
    "teammate": 0.1,
    "goalie": 0.1,
}

# COMPOSITE SCORER


class CompositeScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.scorers = {}
        for key, scorer in SCORER_MAP.items():
            self.scorers[key] = scorer(players, teams)

    def update_score_addition(self, player: "Player", team: "Team"):
        for scorer in self.scorers.values():
            scorer.update_score_addition(player, team)  # type: ignore

    def update_score_removal(self, player: "Player", team: "Team"):
        for scorer in self.scorers.values():
            scorer.update_score_removal(player, team)  # type: ignore

    def get_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        if weights is None:
            weights = DEFAULT_WEIGHTS
        score: float = 0
        total_weight: float = 0
        s = ""
        verbose = False
        for scorer_key, weight in weights.items():
            scorer = self.scorers[scorer_key]
            score += weight * scorer.get_score()  # type: ignore
            total_weight += weight
            if verbose:
                s += f"{scorer.get_score():.3f} "  # type: ignore
        if verbose:
            print(s, list(weights.keys()))
        return score / total_weight
