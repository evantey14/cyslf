"""
Scorers

Scorers should score a given league setup on a scale from 0 to 1.

The main goal here is that "better league arrangement" gets a higher score. Each class implicitly
exposes an interface containing:
* update_score_addition(player, team): update internal metrics associated with adding player->team
* update_score_removal(player, team): update internal metrics associated with removing player->team
* get_score(): return a score between 0 and 1

base.py contains some abstract base scorers that we use here.

CompositeScorer is the primary exported scorer -- it goes scores everything in SCORER_MAP
"""


from typing import TYPE_CHECKING, Dict, List, Optional

from ..utils import (
    BOTTOM_TIER_SKILLS,
    FIRST_ROUND_SKILL,
    GOALIE_THRESHOLD,
    MID_TIER_SKILLS,
    TOP_TIER_SKILLS,
)
from .base import CountParityScorer, CountScorer, MeanParityScorer


if TYPE_CHECKING:
    from .models import Player, Team


# CONVENIENCE SCORERS
class PracticeDayScorer(CountScorer):
    def _count_player(self, player: "Player", team: "Team") -> bool:
        return team.practice_day in player.preferred_days


class LocationScorer:
    def __init__(self, players: List["Player"], teams: List["Team"]):
        self.league_size = len(players)
        self.count = 0.0
        for t in teams:
            self.count += sum([self._count_player(p, t) for p in t.players])

    def _count_player(self, player: "Player", team: "Team") -> float:
        if team.location in player.preferred_locations:
            return 1
        elif team.location in player.backup_locations:
            return 0.5
        else:
            return 0

    def update_score_addition(self, player: "Player", team: "Team"):
        self.count += self._count_player(player, team)

    def update_score_removal(self, player: "Player", team: "Team"):
        self.count -= self._count_player(player, team)

    def get_score(self) -> float:
        return self.count / self.league_size


class TeammateScorer:
    """Scorer for up to 1 teammate request

    We check friend requests by simply checking if {first_name} {last_name} is in the request
    string. We also award at most one friend request per player. This means when adding / removing
    players, we only want to increment / decrement if that player was uniquely requested by someone
    else on the team.
    """

    def __init__(self, players: List["Player"], teams: List["Team"]):
        # Assumes teams are empty, which is technically how we do it
        self.league_size = len(players)
        self.friend_matches = 0

    def update_score_addition(self, player: "Player", team: "Team"):
        request_satisfied = False
        for p in team.players:
            name = f"{p.first_name} {p.last_name}"
            if name in player.teammate_requests and not request_satisfied:
                self.friend_matches += 1
                request_satisfied = True
            if f"{player.first_name} {player.last_name}" in p.teammate_requests:
                player_is_unique = True
                for q in team.players:
                    if p == q:
                        continue
                    if f"{q.first_name} {q.last_name}" in p.teammate_requests:
                        player_is_unique = False
                        break
                if player_is_unique:
                    self.friend_matches += 1

    def update_score_removal(self, player: "Player", team: "Team"):
        request_satisfied = False
        for p in team.players:
            name = f"{p.first_name} {p.last_name}"
            if name in player.teammate_requests and not request_satisfied:
                self.friend_matches -= 1
                request_satisfied = True
            if f"{player.first_name} {player.last_name}" in p.teammate_requests:
                player_is_unique = True
                for q in team.players:
                    if p == q or player == q:
                        continue
                    if f"{q.first_name} {q.last_name}" in p.teammate_requests:
                        player_is_unique = False
                        break
                if player_is_unique:
                    self.friend_matches -= 1

    def get_score(self) -> float:
        return self.friend_matches / self.league_size


# PARITY SCORERS
class SizeScorer(CountParityScorer):
    def _count_player(self, player: "Player") -> bool:
        return True


class FirstRoundScorer(CountParityScorer):
    def _count_player(self, player: "Player") -> bool:
        return player.skill == FIRST_ROUND_SKILL


class TopTierScorer(CountParityScorer):
    def _count_player(self, player: "Player") -> bool:
        return player.skill in TOP_TIER_SKILLS


class MidTierScorer(CountParityScorer):
    def _count_player(self, player: "Player") -> bool:
        return player.skill in MID_TIER_SKILLS


class BottomTierScorer(CountParityScorer):
    def _count_player(self, player: "Player") -> bool:
        return player.skill in BOTTOM_TIER_SKILLS


class GoalieScorer(CountParityScorer):
    def _count_player(self, player: "Player") -> bool:
        return player.goalie_skill <= GOALIE_THRESHOLD


class GradeScorer(MeanParityScorer):
    def _get_value(self, player: "Player") -> bool:
        return player.grade


class SkillScorer(MeanParityScorer):
    def _get_value(self, player: "Player") -> bool:
        return player.skill


SCORER_MAP = {
    "skill": SkillScorer,
    "grade": GradeScorer,
    "size": SizeScorer,
    "location": LocationScorer,
    "practice_day": PracticeDayScorer,
    "teammate": TeammateScorer,
    "first_round": FirstRoundScorer,
    "top": TopTierScorer,
    "mid": MidTierScorer,
    "bottom": BottomTierScorer,
    "goalie": GoalieScorer,
}

DEFAULT_WEIGHTS = {
    "skill": 0.3,
    "grade": 0.3,
    "size": 0.15,
    "location": 0.05,
    "practice_day": 0.05,
    "first_round": 0.15,
    "top": 0.1,
    "mid": 0.1,
    "bottom": 0.1,
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
