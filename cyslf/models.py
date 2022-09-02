from dataclasses import asdict, dataclass, field
from typing import List, Optional, Set

import pandas as pd

from .constraints import breaks_practice_constraint
from .scorers import CompositeScorer
from .utils import (
    BOTTOM_TIER_SKILLS,
    FIRST_ROUND_SKILL,
    GOALIE_THRESHOLD,
    MID_TIER_SKILLS,
    TOP_TIER_SKILLS,
)
from .validation import (
    validate_player_bools,
    validate_player_days,
    validate_player_ints,
    validate_player_locations,
    validate_player_strs,
    validate_team_day,
    validate_team_location,
    validate_team_name,
)


@dataclass(frozen=True)
class Player:
    id: int
    first_name: str
    last_name: str
    grade: int
    skill: int
    coach_skill: int
    parent_skill: int
    goalie_skill: int
    unavailable_days: str
    preferred_days: str
    disallowed_locations: str
    preferred_locations: str
    backup_locations: str
    teammate_requests: str
    lock: bool
    emailed_parents: bool
    school: str
    comment: str

    @classmethod
    def from_raw_dict(cls, raw_dict):
        """Preprocess a raw csv row in dictionary form to create a Player."""
        # Convert nans to empty strings
        str_keys = [
            "unavailable_days",
            "preferred_days",
            "disallowed_locations",
            "preferred_locations",
            "backup_locations",
            "teammate_requests",
        ]
        for key in str_keys:
            if pd.isnull(raw_dict[key]):
                raw_dict[key] = ""

        raw_dict["skill"] = raw_dict["coach_skill"]
        if pd.isnull(raw_dict["skill"]):
            raw_dict["skill"] = raw_dict["parent_skill"]

        return cls(**raw_dict)

    def to_raw_dict(self) -> dict:
        """Create a raw dict that can be saved to a csv."""
        raw_dict = asdict(self)
        del raw_dict["skill"]
        return raw_dict

    def __post_init__(self):
        """Validate player data."""
        validate_player_strs(self)
        validate_player_ints(self)
        validate_player_bools(self)
        validate_player_days(self)
        validate_player_locations(self)


@dataclass
class Team:
    name: str
    practice_day: str
    location: str
    players: Set[Player] = field(default_factory=set)
    # TODO: practice time

    def get_skill(self) -> float:
        if len(self.players) == 0:
            return 0
        return sum([player.skill for player in self.players]) / len(self.players)

    def get_grade(self) -> float:
        if len(self.players) == 0:
            return 0
        return sum([player.grade for player in self.players]) / len(self.players)

    def get_first_round(self) -> int:
        return sum([p.skill == FIRST_ROUND_SKILL for p in self.players])

    def get_top_tier(self) -> int:
        return sum([p.skill in TOP_TIER_SKILLS for p in self.players])

    def get_mid_tier(self) -> int:
        return sum([p.skill in MID_TIER_SKILLS for p in self.players])

    def get_bottom_tier(self) -> int:
        return sum([p.skill in BOTTOM_TIER_SKILLS for p in self.players])

    def get_goalies(self) -> int:
        return sum([p.goalie_skill <= GOALIE_THRESHOLD for p in self.players])

    def __repr__(self):
        return (
            f"Team {self.name:11} "
            f"({self.practice_day} "
            f"{self.location} "
            f"size={len(self.players)}, "
            f"skill={self.get_skill():.2f}, "
            f"grade={self.get_grade():.2f})"
        )

    def __post_init__(self):
        validate_team_name(self)
        validate_team_day(self)
        validate_team_location(self)


@dataclass(frozen=True)
class Move:
    """A class representing moving a player from one team to another."""

    player: Player
    team_from: Optional[Team] = None
    team_to: Optional[Team] = None


@dataclass
class League:
    teams: List[Team]
    available_players: Set[Player]  # TODO: consider a PQ

    def __post_init__(self):
        self.scorer = CompositeScorer(self.players, self.teams)

    @property
    def players(self) -> List[Player]:
        """Return all players in the league."""
        return [p for team in self.teams for p in team.players] + list(
            self.available_players
        )

    def get_next_player(self) -> Player:
        """Gets the next highest-skilled available player for assignment."""
        return min(self.available_players, key=lambda p: p.skill)

    def add_player(self, player: Player, team: Team):
        # Note that the order matters. The scorer must run before the team changes.
        self.scorer.update_score_addition(player, team)
        team.players.add(player)

    def remove_player(self, player: Player, team: Team):
        # Note that the order matters. The scorer must run before the team changes.
        self.scorer.update_score_removal(player, team)
        team.players.remove(player)

    def apply_moves(self, moves: List[Move]) -> None:
        for move in moves:
            if move.team_from is not None:
                self.remove_player(move.player, move.team_from)
            else:
                self.available_players.remove(move.player)
            if move.team_to is not None:
                self.add_player(move.player, move.team_to)
            else:
                self.available_players.add(move.player)

    def undo_moves(self, moves: List[Move]) -> None:
        for move in moves:
            if move.team_to is not None:
                self.remove_player(move.player, move.team_to)
            else:
                self.available_players.remove(move.player)
            if move.team_from is not None:
                self.add_player(move.player, move.team_from)
            else:
                self.available_players.add(move.player)

    def reset_league(self) -> None:
        for team in self.teams:
            for player in list(team.players):
                self.apply_moves([Move(player=player, team_from=team, team_to=None)])

    def details(self) -> None:
        for key, scorer in self.scorer.scorers.items():
            print(f"{key:12}: {scorer.get_score():.3f}")

        team_info_dicts = []
        for team in self.teams:
            team_info_dict = {
                "name": team.name,
                "day": team.practice_day,
                "location": team.location,
                "size": len(team.players),
                "first_round": team.get_first_round(),
                "top_tier": team.get_top_tier(),
                "mid_tier": team.get_mid_tier(),
                "bottom_tier": team.get_bottom_tier(),
                "goalies": team.get_goalies(),
                "skill": team.get_skill(),
                "grade": team.get_grade(),
            }

            team_info_dicts.append(team_info_dict)
        team_info_df = pd.DataFrame.from_records(team_info_dicts)
        with pd.option_context("display.precision", 3):
            print(team_info_df.sort_values(by="name"))

    @classmethod
    def from_csvs(cls, player_csv: str, team_csv: str) -> "League":
        player_info = pd.read_csv(player_csv)
        team_info = pd.read_csv(team_csv)
        teams = {}
        for i, row in team_info.iterrows():
            teams[row["name"]] = Team(**row.to_dict())

        # Add all players as available to start
        players = []
        assigned_team_names = []
        for i, row in player_info.iterrows():
            player_dict = row.to_dict()
            team_name = player_dict.pop("team", None)
            player = Player.from_raw_dict(player_dict)
            assigned_team_names.append(team_name)
            players.append(player)

        league = cls(teams=list(teams.values()), available_players=set(players))

        # Now go and move them to their teams
        for player, team_name in zip(players, assigned_team_names):
            if not pd.isnull(team_name):
                if team_name not in teams:
                    raise ValueError(
                        f"Failed to add {player.first_name} {player.last_name} to Team "
                        f"{team_name}. This team was not found in the team information: "
                        f"{list(teams.keys())}. Please check your spelling, correct this in the "
                        "csv and retry."
                    )
                move = Move(player=player, team_from=None, team_to=teams[team_name])
                if breaks_practice_constraint(move):
                    raise ValueError(
                        f"Failed to add {player.first_name} {player.last_name} to Team "
                        f"{team_name}. This player's practice info is incompatible with the team's "
                        f"practice info:\n{player}\n{teams[team_name]}.\nTry checking the practice "
                        "day and location before correcting this in the input csv and retrying."
                    )
                league.apply_moves([move])

        return league

    def to_csv(self, player_csv: str) -> None:
        teams = []
        players = []
        for team in self.teams:
            team_dict = asdict(team)
            del team_dict["players"]
            teams.append(team_dict)
            for player in team.players:
                players.append(asdict(player) | {"team": team.name})

        for player in self.available_players:
            players.append(asdict(player))

        print(f"Saving player information to {player_csv}")
        pd.DataFrame.from_records(players).to_csv(player_csv, index=False)

    def __repr__(self):
        s = f"{len(self.teams)} Teams:\n"
        for team in self.teams:
            s += f"{team}\n"
        s += f"{len(self.available_players)} players available for assignment"
        return s
