from dataclasses import asdict, dataclass, field
from typing import List, Optional, Set

import pandas as pd


@dataclass(frozen=True)
class Player:
    id: int
    first_name: str
    last_name: str
    grade: int
    skill: int
    unavailable_days: str
    latitude: float
    longitude: float

    def __repr__(self) -> str:
        return (
            f"<{self.first_name} {self.last_name} "
            f"s={self.skill} g={self.grade} {self.unavailable_days}>"
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


class League:
    def __init__(self, teams: List[Team]) -> None:
        self.teams = teams

    def apply_moves(self, moves: List[Move]) -> None:
        for move in moves:
            if move.team_from is not None:
                move.team_from.remove_player(move.player)
            if move.team_to is not None:
                move.team_to.add_player(move.player)

    def undo_moves(self, moves: List[Move]) -> None:
        for move in moves:
            if move.team_to is not None:
                move.team_to.remove_player(move.player)
            if move.team_from is not None:
                move.team_from.add_player(move.player)

    @classmethod
    def from_csvs(cls, player_csv: str, team_csv: str) -> "League":
        player_info = pd.read_csv(player_csv)
        team_info = pd.read_csv(team_csv)
        teams = {}
        for i, row in team_info.iterrows():
            teams[row["name"]] = Team(**row.to_dict())

        for i, row in player_info.iterrows():
            player_dict = row.to_dict()
            team = player_dict.pop("team", None)
            if team is not None:
                teams[team].add_player(Player(**player_dict))
            else:
                print(Player(**player_dict))

        return cls(list(teams.values()))

    def to_csvs(self, player_csv: str, team_csv: str) -> None:
        teams = []
        players = []
        for team in self.teams:
            team_dict = asdict(team)
            del team_dict["players"]
            # TODO: print stats? notably sheets won't be linked though...
            teams.append(team_dict)
            for player in team.players:
                players.append(asdict(player) | {"team": team.name})

        print(f"Saving player information to {player_csv}")
        pd.DataFrame.from_records(players).to_csv(player_csv, index=False)

        print(f"Saving team information to {team_csv}")
        pd.DataFrame.from_records(teams).to_csv(team_csv, index=False)

    def __repr__(self):
        s = f"{len(self.teams)} Teams:\n"
        for team in self.teams:
            s += f"{team}\n"
        return s
