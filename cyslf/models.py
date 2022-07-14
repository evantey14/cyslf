from dataclasses import asdict, dataclass, field
from typing import List, Optional, Set

import pandas as pd

from .constraints import breaks_practice_constraint
from .utils import CENTROID_LAT, CENTROID_LONG


@dataclass(frozen=True)
class Player:
    id: int
    first_name: str
    last_name: str
    grade: int
    skill: int
    coach_skill: int
    parent_skill: int
    unavailable_days: str
    preferred_days: str
    latitude: float
    longitude: float
    frozen: bool
    school: str
    comment: str

    @classmethod
    def from_raw_dict(cls, raw_dict):
        """Preprocess a raw csv row in dictionary form to create a Player."""
        if pd.isnull(raw_dict["unavailable_days"]):
            raw_dict["unavailable_days"] = ""
        if pd.isnull(raw_dict["preferred_days"]):
            raw_dict["preferred_days"] = ""
        if pd.isnull(raw_dict["latitude"]):
            raw_dict["latitude"] = CENTROID_LAT
        if pd.isnull(raw_dict["longitude"]):
            raw_dict["longitude"] = CENTROID_LONG

        raw_dict["skill"] = raw_dict["coach_skill"]
        if pd.isnull(raw_dict["skill"]):
            raw_dict["skill"] = raw_dict["parent_skill"]

        return cls(**raw_dict)

    def to_raw_dict(self) -> dict:
        """Create a raw dict that can be saved to a csv."""
        raw_dict = asdict(self)
        del raw_dict["skill"]
        if raw_dict["latitude"] == CENTROID_LAT:
            raw_dict["latitude"] = pd.NA
        if raw_dict["longitude"] == CENTROID_LONG:
            raw_dict["longitude"] = pd.NA
        return raw_dict

    def __post_init__(self):
        """Validate player data."""
        for day in self.unavailable_days:
            if day in self.preferred_days:
                raise ValueError(
                    f"Failed to create player {self.first_name} {self.last_name} ({self.id}) "
                    f"due to invalid day preferences: {day} was marked as both unavailable "
                    f"({self.unavailable_days}) and preferred ({self.preferred_days}). "
                    "Please correct this in the csv and retry."
                )


@dataclass
class Team:
    name: str
    practice_day: str
    latitude: float
    longitude: float
    players: Set[Player] = field(default_factory=set)
    # TODO: practice time

    def add_player(self, player: Player) -> None:
        self.players.add(player)

    def remove_player(self, player: Player) -> None:
        self.players.remove(player)

    def get_skill(self) -> float:
        if len(self.players) == 0:
            return 0
        return sum([player.skill for player in self.players]) / len(self.players)

    def get_grade(self) -> float:
        if len(self.players) == 0:
            return 0
        return sum([player.grade for player in self.players]) / len(self.players)

    def __repr__(self):
        return (
            f"Team {self.name:11} "
            f"({self.practice_day} "
            f"size={len(self.players)}, "
            f"skill={self.get_skill():.2f}, "
            f"grade={self.get_grade():.2f})"
        )


@dataclass(frozen=True)
class Move:
    """A class representing moving a player from one team to another."""

    player: Player
    team_from: Optional[Team] = None
    team_to: Optional[Team] = None

    def __repr__(self):
        return (
            f"Move {self.player}\n"
            f"\t from: {self.team_from}\n"
            f"\t   to: {self.team_to}\n"
        )


@dataclass
class League:
    teams: List[Team]
    available_players: Set[Player]  # TODO: consider a PQ

    def __post_init__(self):
        self.ideal_team_grade = sum([p.grade for p in self.players]) / len(self.players)
        self.ideal_team_skill = sum([p.skill for p in self.players]) / len(self.players)
        self.ideal_team_size = len(self.players) / len(self.teams)
        self.size = len(self.players)

    @property
    def players(self) -> List[Player]:
        """Return all players in the league."""
        return [p for team in self.teams for p in team.players] + list(
            self.available_players
        )

    def get_next_player(self) -> Player:
        return max(self.available_players, key=lambda p: p.skill)

    def apply_moves(self, moves: List[Move]) -> None:
        for move in moves:
            if move.team_from is not None:
                move.team_from.remove_player(move.player)
            else:
                self.available_players.remove(move.player)
            if move.team_to is not None:
                move.team_to.add_player(move.player)
            else:
                self.available_players.add(move.player)

    def undo_moves(self, moves: List[Move]) -> None:
        for move in moves:
            if move.team_to is not None:
                move.team_to.remove_player(move.player)
            else:
                self.available_players.remove(move.player)
            if move.team_from is not None:
                move.team_from.add_player(move.player)
            else:
                self.available_players.add(move.player)

    def reset_league(self) -> None:
        for team in self.teams:
            for player in list(team.players):
                self.apply_moves([Move(player=player, team_from=team, team_to=None)])

    @classmethod
    def from_csvs(cls, player_csv: str, team_csv: str) -> "League":
        # TODO: check constraints here
        player_info = pd.read_csv(player_csv)
        team_info = pd.read_csv(team_csv)
        teams = {}
        available_players = set()
        for i, row in team_info.iterrows():
            teams[row["name"]] = Team(**row.to_dict())

        for i, row in player_info.iterrows():
            player_dict = row.to_dict()
            team = player_dict.pop("team", None)
            player = Player.from_raw_dict(player_dict)
            if not pd.isnull(team):
                move = Move(player=player, team_from=None, team_to=teams[team])
                if breaks_practice_constraint(move):
                    raise ValueError(
                        f"Failed to add {player} to Team {team}. The team's practice day "
                        f"({teams[team].practice_day}) is in the players unavailable days "
                        f"({player.unavailable_days}). Please correct this in the csv and retry."
                    )
                teams[team].add_player(player)
            else:
                available_players.add(player)

        return cls(teams=list(teams.values()), available_players=available_players)

    def to_csvs(self, player_csv: str, team_csv: str) -> None:
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

        print(f"Saving team information to {team_csv}")
        pd.DataFrame.from_records(teams).to_csv(team_csv, index=False)

    def __repr__(self):
        s = f"{len(self.teams)} Teams:\n"
        for team in self.teams:
            s += f"{team}\n"
        s += f"{len(self.available_players)} players available for assignment"
        return s
