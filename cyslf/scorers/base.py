from math import tanh
from typing import TYPE_CHECKING, List


if TYPE_CHECKING:
    from .models import Player, Team


def _normalize(x: float) -> float:
    # Force a number to be between 0 and 1
    return 1 - tanh(x)


class CountScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.league_size = len(players)
        self.count = 0
        for t in teams:
            self.count += sum([self._count_player(p, t) for p in t.players])

    def _count_player(self, player: "Player", team: "Team") -> bool:
        raise NotImplementedError

    def update_score_addition(self, player: "Player", team: "Team"):
        if self._count_player(player, team):
            self.count += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        if self._count_player(player, team):
            self.count -= 1

    def get_score(self) -> float:
        return self.count / self.league_size


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
        self.team_counts = {team.name: 0 for team in teams}
        for t in teams:
            team_count = sum([self._count_player(p) for p in t.players])
            self.total_player_count += team_count
            self.team_counts[t.name] += team_count

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
        return _normalize(rmse)


class MeanParityScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.total_value = 0
        self.team_means = {team.name: 0.0 for team in teams}
        for t in teams:
            team_mean = sum([self._get_value(p) for p in t.players])
            self.total_value += team_mean
            self.team_means[t.name] += team_mean
        self.total_players = sum([len(t.players) for t in teams])

    def _get_value(self, player: "Player") -> bool:
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
        return _normalize(rmse)
