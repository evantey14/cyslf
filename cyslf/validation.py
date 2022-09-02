import os
from typing import TYPE_CHECKING

from .utils import DAY_MAP, FIELD_MAP


if TYPE_CHECKING:
    from .models import Player, Team


def validate_player_strs(player: "Player"):
    for key in ["first_name", "last_name"]:
        value = player.__getattribute__(key)
        if not isinstance(value, str):
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. Expected a "
                f"string but found {key}={value} ({type(value)}) instead. Please correct this in "
                "the input csv and retry"
            )
        if len(value) == 0:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. {key} has length "
                "0, but shouldn't be empty. Please correct this in the input csv and retry."
            )


def validate_player_ints(player: "Player"):
    for key, minimum, maximum in [
        ("grade", -1, 8),
        ("skill", 1, 10),
        ("goalie_skill", 1, 10),
    ]:
        value = player.__getattribute__(key)
        if not isinstance(value, int) and not isinstance(value, float):
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. Expected a "
                f"number but found {key}={value} ({type(value)}) instead. Please correct this in "
                "the input csv and retry"
            )
        if value < minimum or value > maximum:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. {key} ({value}) "
                f"is unexpectedly < {minimum} or > {maximum}. Please correct this in the input csv "
                "and retry."
            )


def validate_player_days(player: "Player"):
    valid_days = "".join(list(DAY_MAP.values()))
    for day in player.unavailable_days + player.preferred_days:
        if day not in valid_days:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name} due to invalid "
                f"day. {day}  is not a valid day ({valid_days}). Please correct this in the input "
                "csv and retry."
            )

    for day in player.unavailable_days:
        if day in player.preferred_days:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name} due to invalid "
                f"day preferences: {day} was marked as both unavailable ({player.unavailable_days})"
                f" and preferred ({player.preferred_days}). Please correct this in the csv and "
                "retry."
            )


def validate_player_bools(player: "Player"):
    for key in ["lock", "emailed_parents"]:
        value = player.__getattribute__(key)
        if not isinstance(value, bool):
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. Expected a "
                f"bool but found {key}={value} ({type(value)}) instead. Please correct this in "
                "the input csv and retry"
            )
    if player.emailed_parents and not player.lock:
        raise ValueError(
            f"Failed to create player {player.first_name} {player.last_name}. emailed_parents was "
            "set to True while lock was set to False. If parents have already been emailed, the "
            "player should be locked to their teams. Please correct this in the input csv and "
            "retry"
        )


def validate_player_locations(player: "Player"):
    valid_locations = set()
    for region, fields in FIELD_MAP.items():
        valid_locations.update(fields)

    # TODO: figure out how to strip strings to make the parsing more forgiving
    disallowed_locations = player.disallowed_locations.split(", ")
    preferred_locations = player.preferred_locations.split(", ")
    backup_locations = player.backup_locations.split(", ")
    for loc in disallowed_locations + preferred_locations + backup_locations:
        if len(loc) > 0 and loc not in valid_locations:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name} due to invalid "
                f"location. {loc} is not a valid location ({valid_locations}). Please correct in "
                "the input csv and retry."
            )

    for loc in disallowed_locations:
        if len(loc) > 0 and loc in player.preferred_locations:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name} ({player.id}) due "
                f"to invalid location preferences: {loc} was marked as both disallowed "
                f"({player.disallowed_locations}) and preferred ({player.preferred_locations}). "
                "Please correct this in the csv and retry."
            )


def validate_team_name(team: "Team"):
    if not isinstance(team.name, str):
        raise ValueError(
            f"Failed to create team {team}. Name should be a string, but was instead a "
            f"{type(team.name)}. Please correct the input csv and retry."
        )

    if len(team.name) == 0:
        raise ValueError(
            f"Failed to create team {team}. Name should not have length == 0. Please correct the "
            "input csv and retry."
        )


def validate_team_day(team: "Team"):
    valid_days = "".join(list(DAY_MAP.values()))
    if team.practice_day not in valid_days:
        raise ValueError(
            f"Failed to create team {team.name}. Practice day {team.practice_day} is not a valid "
            f"practice day ({valid_days}). Please orrect the input csv and retry."
        )


def validate_team_location(team: "Team"):
    valid_locations = set()
    for region, fields in FIELD_MAP.items():
        valid_locations.update(fields)

    if team.location not in valid_locations:
        raise ValueError(
            f"Failed to create team {team.name}. Location {team.location} is not in the valid "
            f"location list: {valid_locations}. Please check spelling, correct the input csv and "
            "retry"
        )


def validate_file(filename: str):
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Could not find file: {filename}. Please check that you spelled the file name "
            "correctly and are running the command from the correct directory."
        )


def request_validation(message: str):
    print(message)
    _ = input("Press Enter to continue, or ctrl+c to quit:")
