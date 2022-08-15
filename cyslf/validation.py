from typing import TYPE_CHECKING

from .utils import DAY_MAP, FIELD_MAP


if TYPE_CHECKING:
    from .models import Player


def validate_strs(player: "Player"):
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


def validate_ints(player: "Player"):
    for key in ["grade", "skill", "goalie_skill"]:
        value = player.__getattribute__(key)
        if not isinstance(value, int) and not isinstance(value, float):
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. Expected a "
                f"number but found {key}={value} ({type(value)}) instead. Please correct this in "
                "the input csv and retry"
            )
        if value < 1 or value > 10:
            raise ValueError(
                f"Failed to create player {player.first_name} {player.last_name}. {key} ({value}) "
                "is unexpectedly < 1 or > 10. Please correct this in the input csv and retry."
            )


def validate_days(player: "Player"):
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


def validate_locations(player: "Player"):
    valid_locations = set()
    for region, fields in FIELD_MAP.items():
        valid_locations.update(fields)

    # TODO: figure out how to strip strings to make the parsing more forgiving
    disallowed_locations = player.disallowed_locations.split(", ")
    preferred_locations = player.preferred_locations.split(", ")
    for loc in disallowed_locations + preferred_locations:
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
