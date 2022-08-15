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
class CountScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.league_size = len(players)
        self.count = 0
        for t in teams:
            self.count += sum([self._count_player(p, t) for p in t.players])

    def _count_player(self, player: "Player", team: "Team"):
        raise NotImplementedError

    def update_score_addition(self, player: "Player", team: "Team"):
        if self._count_player(player, team):
            self.count += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if self._count_player(player, team):
            self.count -= 1

    def get_score(self) -> float:
        return self.count / self.league_size


class PracticeDayScorer(CountScorer):
    def _count_player(self, player: "Player", team: "Team"):
        return team.practice_day in player.preferred_days


class LocationScorer(CountScorer):
    def _count_player(self, player: "Player", team: "Team"):
        return team.location in player.preferred_locations


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


def _update_rolling_mean(old_mean, old_size, value, add_value):
    """Calculate the updated rolling mean for added or removed values."""
    if add_value:
        return (old_size * old_mean + value) / (old_size + 1)
    else:
        if old_size == 1:
            # If there aren't any more points, return 0 to avoid a divide-by-zero error
            return 0
        return (old_size * old_mean - value) / (old_size - 1)


class CountParityScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_player_count = 0
        for t in teams:
            self.total_player_count += sum([self._count_player(p) for p in t.players])
        self.team_counts = {team.name: 0 for team in teams}

    def _count_player(self, player: "Player") -> bool:
        raise NotImplementedError

    def update_score_addition(self, player: "Player", team: "Team"):
        if self._count_player(player):
            self.total_player_count += 1
            self.team_counts[team.name] += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if self._count_player(player):
            self.total_player_count -= 1
            self.team_counts[team.name] -= 1

    def get_score(self) -> float:
        ideal_team_count = self.total_player_count / len(self.team_counts)
        rmse = _calculate_rmse(self.team_counts.values(), ideal_team_count)
        return max(0, 1 - rmse)


class SizeScorer(CountParityScorer):
    def _count_player(self, player: "Player"):
        return True


class EliteScorer(CountParityScorer):
    def _count_player(self, player: "Player"):
        return player.skill == ELITE_PLAYER_SKILL_LEVEL


class GoalieScorer(CountParityScorer):
    def _count_player(self, player: "Player"):
        return player.goalie_skill <= GOALIE_THRESHOLD


class MeanParityScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_value = 0
        for t in teams:
            self.total_value += sum([self._get_value(p) for p in t.players])
        self.total_players = sum([len(t.players) for t in teams])
        self.team_means = {team.name: 0.0 for team in teams}

    def _get_value(self, player: "Player"):
        raise NotImplementedError

    def update_score_addition(self, player: "Player", team: "Team"):
        self.total_value += self._get_value(player)
        self.total_players += 1
        self.team_means[team.name] = _update_rolling_mean(
            self.team_means[team.name],
            len(team.players),
            self._get_value(player),
            add_value=True,
        )

    def update_score_removal(self, player: "Player", team: "Team"):
        self.total_value -= self._get_value(player)
        self.total_players -= 1
        self.team_means[team.name] = _update_rolling_mean(
            self.team_means[team.name],
            len(team.players),
            self._get_value(player),
            add_value=False,
        )

    def get_score(self) -> float:
        ideal_value = self.total_value / self.total_players
        rmse = _calculate_rmse(self.team_means.values(), ideal_value)
        return max(0, 1 - rmse)


class GradeScorer(MeanParityScorer):
    def _get_value(self, player: "Player"):
        return player.grade


class SkillScorer(MeanParityScorer):
    def _get_value(self, player: "Player"):
        return player.skill


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
