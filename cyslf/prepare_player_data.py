import argparse

import numpy as np
import pandas as pd

from cyslf.utils import DAY_MAP, FIELD_MAP


pd.set_option("display.max_rows", None)

parser = argparse.ArgumentParser(
    description="Process raw registration forms into a standard csv."
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
    "--parent_requests",
    "--par",
    type=str,
    help="Parent request form (practice preferences / teammate requests)",
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


def _extract_num(column, dtype):
    """Extract numbers from a string column."""
    return column.str.extract("(\d+)", expand=False).astype(dtype)  # noqa: W605


def _normalize_str(column):
    """Normalize string by removing non-alpha and lowercasing (partciularly for name matching)."""
    return column.str.lower().str.replace("[^a-zA-Z]", "", regex=True)


def _load_existing_player_data(filename: str, division: str):
    print("=====")
    print(f"Reading {filename}")
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

    # Extract coach skill
    existing_players["coach_skill"] = _extract_num(
        existing_players["coach_skill"], float
    )
    # Players not already in the current division are coming from a younger division. Since they're
    # younger, we'll make their skill one point worse. In the future, maybe we can pick a more
    # principled offset
    existing_players.loc[~in_division, "coach_skill"] += 1

    # Construct name for matching to current registration
    full_name = existing_players["first_name"] + existing_players["last_name"]
    existing_players["name_key"] = _normalize_str(full_name)

    # Handle duplicates by taking the highest score for a given name
    existing_players = (
        existing_players.drop(columns=["first_name", "last_name"])
        .sort_values(by="coach_skill")
        .drop_duplicates("name_key")
    )

    print(f"Loaded {len(existing_players)} existing players for skill/team lookup.")
    print(f"{in_division.sum()} were found in division: {division}")
    print(existing_players.head())
    print("=====")
    return existing_players


def _extract_locations(locations_str):
    field_set = set()
    if pd.isnull(locations_str):
        return ""
    for region, fields in FIELD_MAP.items():
        # TODO: Ensure users can't type plaintext into locations_str
        if region in locations_str:
            field_set.update(fields)
    return ", ".join(list(field_set))


def _load_parent_requests(filename):
    print(f"Reading {filename}")
    parent_reqs = pd.read_csv(filename)
    parent_reqs.head()
    column_map = {
        "Player First Name": "first_name",
        "Player Last Name": "last_name",
        "Preferred practice day(s)": "preferred_days",
        "Unavailable practice day(s)": "unavailable_days",
        "Preferred Practice Location(s)": "preferred_locations",
        "Disallowed Practice Location(s)": "disallowed_locations",
        "Teammate Request 1": "teammate_req1",
        "Teammate Request 2": "teammate_req2",
    }
    parent_reqs = parent_reqs.rename(columns=column_map)[column_map.values()]

    parent_reqs["name_key"] = _normalize_str(
        parent_reqs["first_name"] + parent_reqs["last_name"]
    )
    parent_reqs["preferred_days"] = (
        parent_reqs["preferred_days"]
        .replace(DAY_MAP, regex=True)
        .replace(", ", "", regex=True)
    )
    parent_reqs["unavailable_days"] = (
        parent_reqs["unavailable_days"]
        .replace(DAY_MAP, regex=True)
        .replace(", ", "", regex=True)
    )
    parent_reqs["teammate_requests"] = (
        parent_reqs["teammate_req1"] + ", " + parent_reqs["teammate_req2"]
    )

    parent_reqs["preferred_locations"] = parent_reqs["preferred_locations"].apply(
        _extract_locations
    )
    parent_reqs["disallowed_locations"] = parent_reqs["disallowed_locations"].apply(
        _extract_locations
    )

    parent_reqs = parent_reqs.drop(
        columns=["first_name", "last_name", "teammate_req1", "teammate_req2"]
    )
    parent_reqs.head()

    print(
        f"Loaded {len(parent_reqs)} practice day, practice location, and teammate requests"
    )
    print(parent_reqs.head())
    print("=====")
    return parent_reqs


def _load_registration_data(filename):
    print("=====")
    print(f"Reading {filename}")
    registrations_raw = pd.read_csv(filename)

    # Merge the two school columns
    has_other_school = ~pd.isnull(registrations_raw["School Name other:"])
    registrations_raw.loc[has_other_school, "School Name"] = registrations_raw[
        has_other_school
    ]["School Name other:"]

    column_map = {
        "Player Last Name": "last_name",
        "Player First Name": "first_name",
        "Current Grade": "grade",
        "Parental assessment of player ability/athleticism:": "parent_skill",
        "School Name": "school",
        "Special Requests": "comment",
    }
    registrations = registrations_raw.rename(columns=column_map)[column_map.values()]

    # Extract grade
    # TODO: handle K and PreK grades
    registrations["grade"] = _extract_num(registrations["grade"], int)

    # Extract parent skill (they have opposite order from coach skill, so invert)
    registrations["parent_skill"] = _extract_num(registrations["parent_skill"], float)
    registrations["parent_skill"] = 11 - registrations["parent_skill"]

    # Construct name for matching to current registration.
    full_name = registrations["first_name"] + registrations["last_name"]
    registrations["name_key"] = _normalize_str(full_name)

    print(f"Found {len(registrations)} registrations")
    print(registrations.head())
    print("=====")
    return registrations


def _merge_data(existing_players, parent_reqs, registrations):
    print("=====")
    print("Integrating old data, parent requests, and registrations.")

    existing_player_match = registrations["name_key"].isin(existing_players["name_key"])
    print(
        f"{existing_player_match.sum()} out of {len(registrations)} players were matched to "
        "existing player data."
    )
    print("The following players were NOT matched:")
    print(
        registrations[~existing_player_match][["first_name", "last_name"]].agg(
            " ".join, axis=1
        )
    )

    parent_req_match = registrations["name_key"].isin(parent_reqs["name_key"])
    print(
        f"{parent_req_match.sum()} out of {len(registrations)} players had matching parent requests"
    )
    print("The following players were NOT matched:")
    print(
        registrations[~parent_req_match][["first_name", "last_name"]].agg(
            " ".join, axis=1
        )
    )

    ordered_columns = [
        "id",
        "last_name",
        "first_name",
        "grade",
        "team",
        "coach_skill",
        "parent_skill",
        "preferred_days",
        "unavailable_days",
        "preferred_locations",
        "disallowed_locations",
        "teammate_requests",
        "frozen",
        "school",
        "comment",
    ]
    players = registrations.merge(existing_players, how="left", on="name_key").merge(
        parent_reqs, how="left", on="name_key"
    )
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
    print("=====")
    return players


def _validate_players(players):
    print("=====")
    print("Running verification checks:")

    normalized_name = _normalize_str(players["first_name"] + players["last_name"])
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
        print(
            f"{missing_skill.sum()} players don't have a coach or parent skill. We'll manually "
            "assign them a skill of 5."
        )
        print(
            players[missing_skill][
                ["id", "first_name", "last_name", "coach_skill", "parent_skill"]
            ]
        )
        print()

        players.loc[missing_skill, "parent_skill"] = 10


def main():
    args = parser.parse_args()

    # Pull team and coach score from spring 2022
    existing_players = _load_existing_player_data(args.old_registration, args.division)

    # Load parent requests
    parent_reqs = _load_parent_requests(args.parent_requests)

    # Load current registrations
    registrations = _load_registration_data(args.registration)

    # Merge the old data into the current registration data.
    players = _merge_data(existing_players, parent_reqs, registrations)

    # Validate the player list
    _validate_players(players)

    print("=====")
    player_outfile = f"{args.output_stem}-players.csv"
    print(f"Saving to {player_outfile}")
    players.to_csv(player_outfile, index=False)

    print(
        "All done! Please load into Excel/Google Sheets and read through any comments making "
        "adjustments to cells as necessary."
    )


if __name__ == "__main__":
    main()
