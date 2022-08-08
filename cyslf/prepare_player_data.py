import argparse
import logging

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
import numpy as np
import pandas as pd
from tqdm import tqdm


# Prepare location finding
geolocator = Nominatim(user_agent="cyslf")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1 / 2)

tqdm.pandas()

pd.set_option("display.max_rows", None)

parser = argparse.ArgumentParser(
    description="Process raw registration forms into a standardized csv."
)
parser.add_argument(
    "--division",
    "--div",
    "-d",
    type=str,
    help="division without season (e.g. 'Boys Grades 3-4'). Spelling needs to match form data.",
)
parser.add_argument(
    "--old_registration",
    "--old_reg",
    type=str,
    help="Old registration csv. Where to pull coach evals + past teams from.",
)
parser.add_argument(
    "--registration", "--reg", type=str, help="Current registration csv."
)
parser.add_argument(
    "--output_stem",
    "-o",
    type=str,
    help="output csv stem. write outputs to '{stem}-players.csv'",
)


def _load_existing_player_data(filename: str, division: str):
    print("=====")
    print(f"Reading {filename}.")
    existing_players_raw = pd.read_csv(filename)
    # Only keep teams if the players were in the relevant division.
    # This is because a Spring 2nd-grader on Red shouldn't stay on Red, but
    # we do want to know their skill score.
    in_division = existing_players_raw["Division"].str.contains(division)
    existing_players_raw.loc[~in_division, "Assigned Team"] = np.nan

    column_map = {
        "Player rating - Effectiveness": "coach_skill",
        "Lastname": "last_name",
        "Firstname": "first_name",
        "Assigned Team": "team",
    }
    existing_players = existing_players_raw.rename(columns=column_map)[
        column_map.values()
    ]

    # Extract skill
    existing_players["coach_skill"] = (
        existing_players["coach_skill"]
        .str.extract("(\d+)", expand=False)  # noqa: W605
        .astype(float)
    )

    # Construct name for matching to current registration.
    full_name = existing_players["first_name"] + existing_players["last_name"]
    normalized_name = full_name.str.lower().str.replace("[^a-zA-Z]", "", regex=True)
    existing_players["name_key"] = normalized_name
    existing_players = (
        existing_players.drop(columns=["first_name", "last_name"])
        # there seemed to be duplicate rows (with missing skill scores) so
        # let's take the highest score for each name. Note this assumes
        # that kids have unique name keys
        .sort_values(by="coach_skill").drop_duplicates("name_key")
    )

    print(f"Loaded {len(existing_players)} existing players for skill/team lookup.")
    print(f"{in_division.sum()} were found in division: {division}")
    print(existing_players.head())
    print("=====")
    return existing_players


def _lookup_location(address):
    # If an address is poorly formed, geopy gives sad-looking warnings,
    # so let's temporarily disable this.
    logging.getLogger("geopy").setLevel(logging.ERROR)
    location = geocode(address)
    logging.getLogger("geopy").setLevel(logging.WARNING)
    if location:
        return location.latitude, location.longitude
    else:
        print(f"Failed to find address: {address}")
        return np.nan, np.nan


def _load_registration_data(filename):
    print("=====")
    print(f"Reading {filename}")
    registrations_raw = pd.read_csv(filename)

    # Join the two school columns
    has_other_school = ~pd.isnull(registrations_raw["School Name other:"])
    registrations_raw.loc[has_other_school, "School Name"] = registrations_raw[
        has_other_school
    ]["School Name other:"]

    # Look up player latitude / longitude
    print("Looking up latitude/longitude from addresses.")
    registrations_raw["Postal Code"] = registrations_raw["Postal Code"].astype(str)
    registrations_raw["Address"] = registrations_raw[
        ["Street", "City", "Region", "Postal Code"]
    ].agg(", ".join, axis=1)
    registrations_raw["Location"] = registrations_raw["Address"].progress_apply(
        _lookup_location
    )
    registrations_raw["latitude"] = registrations_raw["Location"].apply(lambda x: x[0])
    registrations_raw["longitude"] = registrations_raw["Location"].apply(lambda x: x[1])

    column_map = {
        "Player Last Name": "last_name",
        "Player First Name": "first_name",
        "Current Grade": "grade",
        "Parental assessment of player ability/athleticism:": "parent_skill",
        "School Name": "school",
        "Special Requests": "comment",
        "longitude": "longitude",
        "latitude": "latitude",
        "Teammate Request": "requested_teammate",
    }
    registrations = registrations_raw.rename(columns=column_map)[column_map.values()]

    # Extract grade
    registrations["grade"] = (
        registrations["grade"]
        .str.extract("(\d+)", expand=False)  # noqa: W605
        .astype(int)
    )

    # Extract skill
    registrations["parent_skill"] = (
        registrations["parent_skill"]
        .str.extract("(\d+)", expand=False)  # noqa: W605
        .astype(float)
    )
    registrations["parent_skill"] = (
        11 - registrations["parent_skill"]
    )  # These have the opposite order of coach skill, so invert.

    # Construct name for matching to current registration.
    full_name = registrations["first_name"] + registrations["last_name"]
    normalized_name = full_name.str.lower().str.replace("[^a-zA-Z]", "", regex=True)
    registrations["name_key"] = normalized_name

    print(f"Found {len(registrations)} registrations")
    print(registrations.head())
    print("=====")
    return registrations


def _merge_existing_data_with_registrations(existing_players, registrations):
    print("=====")
    print("Integrating old data with registrations.")
    existing_player_match = registrations["name_key"].isin(existing_players["name_key"])
    print(
        f"{existing_player_match.sum()} out of {len(registrations)} players were matched to "
        "existing player data."
    )
    print("The following players were NOT matched:")
    print(registrations[~existing_player_match])

    ordered_columns = [
        "id",
        "last_name",
        "first_name",
        "grade",
        "team",
        "coach_skill",
        "parent_skill",
        "longitude",
        "latitude",
        "preferred_days",
        "unavailable_days",
        "frozen",
        "school",
        "comment",
    ]
    players = registrations.merge(existing_players, how="left", on="name_key")
    players["id"] = players.index.values

    # Freeze players to a team if they already have one
    players["frozen"] = True
    missing_team = pd.isnull(players.team)
    players.loc[missing_team, "frozen"] = False

    # Fill missing columns with nans
    for col in ordered_columns:
        if col not in players.columns:
            players[col] = np.nan

    players = players[ordered_columns]

    print(
        f"Finished merging old data into registrations. Total # of players: {len(players)}"
    )
    print(players.head())
    print("=====")
    return players


def _validate_players(players):
    print("=====")
    print("Running verification checks:")

    full_name = players["first_name"] + players["last_name"]
    normalized_name = full_name.str.lower().str.replace("[^a-zA-Z]", "", regex=True)
    name_counts = normalized_name.value_counts()
    duplicate_names = name_counts[name_counts > 1].index.values
    has_duplicate = normalized_name.isin(duplicate_names)
    if has_duplicate.sum() > 0:
        print(
            f"{has_duplicate.sum()} rows have names that match other rows, so please check if "
            "they're duplicates:"
        )
        print(
            players[has_duplicate].sort_values(by="last_name")[
                ["id", "first_name", "last_name"]
            ]
        )

    missing_last_name = pd.isnull(players.last_name)
    if missing_last_name.sum() > 0:
        print(f"{missing_last_name.sum()} players are missing a last name:")
        print(players[missing_last_name][["id", "first_name", "last_name"]])
        print()

    missing_first_name = pd.isnull(players.first_name)
    if missing_first_name.sum() > 0:
        print(f"{missing_first_name.sum()} players are missing a first name:")
        print(players[missing_first_name][["id", "first_name", "last_name"]])
        print()

    missing_grade = pd.isnull(players.grade)
    if missing_grade.sum() > 0:
        print(f"{missing_grade.sum()} players are missing a grade:")
        print(players[missing_grade][["id", "first_name", "last_name", "grade"]])
        print()

    missing_skill = pd.isnull(players.coach_skill) & pd.isnull(players.parent_skill)
    if missing_skill.sum() > 0:
        print(f"{missing_skill.sum()} players don't have a coach or parent skill:")
        print(
            players[missing_skill][
                ["id", "first_name", "last_name", "coach_skill", "parent_skill"]
            ]
        )
        print()

        # For testing let's give them the worst score
        # I should ask Jason about this though
        players.loc[missing_skill, "parent_skill"] = 10

    print("Please manually fix any listed problems before making teams.^")


def main():
    args = parser.parse_args()

    # Pull team and coach score from spring 2022
    existing_players = _load_existing_player_data(args.old_registration, args.division)

    # Load current registrations
    registrations = _load_registration_data(args.registration)

    # Merge the old data into the current registration data.
    players = _merge_existing_data_with_registrations(existing_players, registrations)

    # Validate the player list
    _validate_players(players)

    print("=====")
    player_outfile = f"{args.output_stem}-players.csv"
    print(f"Saving to {player_outfile}")
    players.to_csv(player_outfile, index=False)


if __name__ == "__main__":
    main()
