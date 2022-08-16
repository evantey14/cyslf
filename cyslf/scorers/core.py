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


class LocationScorer(CountScorer):
    def _count_player(self, player: "Player", team: "Team") -> bool:
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
