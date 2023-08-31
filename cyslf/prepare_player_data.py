import argparse
import logging
import os

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
import numpy as np
import pandas as pd
from thefuzz import fuzz
from tqdm import tqdm
from cyslf.utils import handle_error

from cyslf.utils import DAY_MAP, FIELD_LOCATIONS, FIELD_MAP, get_dist
from cyslf.validation import request_validation, validate_file


geolocator = Nominatim(user_agent="cyslf")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1 / 2)
tqdm.pandas()
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
    "--folder",
    "-f",
    type=str,
    help="Folder containing coach evaluations, parent requests, and registrations",
    default=None,
)

parser.add_argument(
    "--coach_evals",
    "-ce",
    type=str,
    default=None,
    help="Old registration csv. Where to pull coach evals + past teams from.",
)

parser.add_argument(
    "--parent_requests",
    "--par",
    type=str,
    default=None,
    help="Parent request form (practice preferences / teammate requests)",
)

parser.add_argument(
    "--registration", "--reg", type=str, help="Current registration csv.", default=None
)

parser.add_argument(
    "---matches",
    "-m",
    default=5,
    type=int,
    help="Number of potential name matches to display",
)

parser.add_argument(
    "--output_file",
    "-o",
    type=str,
    help="output csv file. eg 'b34-players.csv'",
)

parser.add_argument(
    "--replace",
    "-r",
    action="store_true",
    help="Overwrite the output file if it exists",
)


def _extract_num(column, dtype=float):
    """Extract numbers from a string column."""
    return column.str.extract("(\d+)", expand=False).astype(dtype)  # noqa: W605


def _extract_grade(column):
    """Extract the grade number from columns, setting P to -1 and K to 0"""
    grade = column.fillna("").astype(str).str[0]
    grade = grade.str.replace("P", "-1", regex=False)
    grade = grade.str.replace("K", "0", regex=False)
    return grade.astype(float)  # Allow missing grade for now


def _normalize_str(column):
    """Normalize string by removing non-alpha and lowercasing (partciularly for name matching)."""
    return column.str.lower().str.replace("[^a-zA-Z]", "", regex=True)


def _get_names(df):
    return ", ".join(df[["first_name", "last_name"]].agg(" ".join, axis=1))


# read coach eval file
def _load_existing_player_data(filename: str, division: str):
    print(f"\n===Reading existing player data from {filename}===")
    existing_players_raw = pd.read_csv(filename)
    print(f"{len(existing_players_raw)} players found in previous registration data.")
    # Only keep teams if the players were in the relevant division.
    # This is because a Spring 2nd-grader on Red shouldn't stay on Red, but
    # we do want to know their skill score.
    in_division = existing_players_raw["division"].str.contains(division)
    print(f"{in_division.sum()} were found in division: {division}")
    if in_division.sum() == 0:
        request_validation(
            "WARNING: Please confirm that the division is spelled correctly before proceeding"
        )
    existing_players_raw.loc[~in_division, "team"] = np.nan

    # changed to match coach evals
    column_map = {
        "rating_overall (1 is high)": "coach_skill",
        "rating_goalie": "goalie_skill",
        "lastname": "last_name",
        "firstname": "first_name",
        "team": "team",
    }
    for key, _ in column_map.items():
        if key not in existing_players_raw.columns:
            handle_error(f"Coach evals file is missing the \"{key}\" column.", True)
    existing_players = existing_players_raw.rename(columns=column_map)[
        column_map.values()
    ]

    # Players not already in the current division are coming from a younger division. Since they're
    # younger, we'll make their skill one point worse. In the future, maybe we can pick a more
    # principled offset
    print(
        "Lowering player skill by 1 for players that weren't previously in this division"
    )
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

    return existing_players

def _translate_practice_days(row, match1):
    ans = [day for day in DAY_MAP.values() if row[day] == match1]
    return "".join(ans)

def _translate_locations(row, match):
    # TODO: optimize
    ans = ""
    if row["east"] == match:
        for location in FIELD_MAP["East"]:
            ans += location + ", "
    if row["central"] == match:
        for location in FIELD_MAP["Central"]:
            ans += location + ", "
    if row["cambridgeport"] == match:
        for location in FIELD_MAP["Cambridgeport"]:
            ans += location + ", "
    if row["west"] == match:
        for location in FIELD_MAP["West"]:
            ans += location + ", "
    if row["north"] == match:
        for location in FIELD_MAP["North"]:
            ans += location + ", "
    if len(ans) > 0: ans = ans[:-2]
    return ans


def _load_parent_requests(filename):
    print(f"\n===Reading parent requests from {filename}===")
    parent_reqs = pd.read_csv(filename)
    print(f"{len(parent_reqs)} parent requests found")

    column_map = {
        "Player First Name (as it is written in your CYS/Sports Connect account)": "first_name",
        "Player Last Name": "last_name",
        "Preferred practice day(s) [Monday]": "M",
        "Preferred practice day(s) [Tuesday]": "T",
        "Preferred practice day(s) [Wednesday]": "W", 
        "Preferred practice day(s) [Thursday]": "R",
        "Preferred practice day(s) [Friday]": "F",
        "Practice Location(s) [East]": "east",
        "Practice Location(s) [Central]": "central",
        "Practice Location(s) [Cambridgeport]": "cambridgeport",
        "Practice Location(s) [West]": "west",
        "Practice Location(s) [North]": "north",
        "Teammate Request 1 First Name": "teammate_req1_firstname",
        "Teammate Request 1 Last Name": "teammate_req1_lastname",
        "Teammate Request 2 First Name": "teammate_req2_firstname",
        "Teammate Request 2 Last Name": "teammate_req2_lastname",
        "Teammate Request 3 First Name": "teammate_req3_firstname",
        "Teammate Request 3 Last Name": "teammate_req3_lastname",
        "I am willing to ": "extra_comment",
    }

    # Account for missing columns

    if "Player First Name (as it is written in your CYS/Sports Connect account)" not in parent_reqs.columns:
        handle_error("Missing first name column in parent requests file. Make sure the column name matches the docs.", True)
        
    if "Player Last Name" not in parent_reqs.columns:
        handle_error("Missing last name column in parent requests file. Make sure the column name matches the docs.", True)
        
    for key, val in column_map.items():
        if key not in parent_reqs.columns:
            print(f"Parent request file is missing column {key}. An empty column was added.")
            parent_reqs[val] = ''

    parent_reqs = parent_reqs.rename(columns=column_map)[column_map.values()]

    parent_reqs["name_key"] = _normalize_str(
        parent_reqs["first_name"] + parent_reqs["last_name"]
    )
    
    parent_reqs["preferred_days"] = parent_reqs.apply(lambda row: _translate_practice_days(row, "Ideal"), axis=1)
    
    parent_reqs["unavailable_days"] = parent_reqs.apply(lambda row: _translate_practice_days(row, "Impossible"), axis=1) 


    # concat all teammate request names for easy search 
    parent_reqs["teammate_requests"] = (parent_reqs["teammate_req1_firstname"].fillna('') + " " +  
                                        parent_reqs["teammate_req1_lastname"].fillna('') + ", " + 
                                        parent_reqs["teammate_req2_firstname"].fillna('') + " " + 
                                        parent_reqs["teammate_req2_lastname"].fillna('') + ", " + 
                                        parent_reqs["teammate_req3_firstname"].fillna('') + " " + 
                                        parent_reqs["teammate_req3_lastname"].fillna(''))

    parent_reqs["preferred_locations"] =  parent_reqs.apply(lambda row: _translate_locations(row, "Ideal"), axis=1)

    parent_reqs["disallowed_locations"]  = parent_reqs.apply(lambda row: _translate_locations(row, "Impossible"), axis=1) 


    parent_reqs = parent_reqs.drop(
        columns=["first_name", "last_name", "teammate_req1_firstname", "teammate_req1_lastname", "teammate_req2_firstname", "teammate_req2_lastname", "M", "T", "W", "R", "F"]
    )

    # Keep most recent entry
    return parent_reqs.drop_duplicates("name_key", keep="last")


# no change
def _load_registration_data(filename):
    print(f"\n===Reading registration data from {filename}===")
    registrations_raw = pd.read_csv(filename)

    if "latitude" not in registrations_raw.columns or "longitude" not in registrations_raw.columns:
        handle_error("Please use the convert addresses command before preparing player data. See documentation for more details.", True)
        
    
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
        "longitude": "longitude",
        "latitude": "latitude",
    }
    for key, _ in column_map.items():
        if key not in registrations_raw.columns:
            handle_error(f"Registration file doesn't contain the \"{key}\" column.", True)
            
    
    registrations = registrations_raw.rename(columns=column_map)[column_map.values()]

    # Extract grade
    registrations["grade"] = _extract_grade(registrations["grade"])

    # Extract parent skill (they have opposite order from coach skill, so invert)
    registrations["parent_skill"] = _extract_num(registrations["parent_skill"])
    registrations["parent_skill"] = 11 - registrations["parent_skill"]

    # deal with kickstart players being rated 0
    registrations["parent_skill"] = registrations["parent_skill"].replace(11, 5)



    # Construct name for matching to current registration.
    full_name = registrations["first_name"] + registrations["last_name"]
    registrations["name_key"] = _normalize_str(full_name)

    print(f"{len(registrations)} registrations found")
    return registrations


def _merge_data(existing_players, parent_reqs, registrations):
    print("\n===Merging data===")

    ordered_columns = [
        "id",
        "last_name",
        "first_name",
        "grade",
        "team",
        "coach_skill",
        "parent_skill",
        "goalie_skill",
        "preferred_days",
        "unavailable_days",
        "preferred_locations",
        "disallowed_locations",
        "backup_locations",
        "teammate_requests",
        "lock",
        "emailed_parents",
        "school",
        "comment",
    ]
    players = registrations.merge(existing_players, how="left", on="name_key").merge(
        parent_reqs, how="left", on="name_key"
    )
    players["id"] = players.index.values

    # Lock players to a team if they already have one
    players["lock"] = False
    # missing_team = pd.isnull(players.team)
    # players.loc[missing_team, "lock"] = False
    # print(f"{(~missing_team).sum()} players locked onto their teams from last season")

    players["emailed_parents"] = False

    # Set backup field preferences based on location
    # If parents didn't fill out the request form with a location preference, or if the preferred
    # locations don't provide enough options, we'd like to have a fallback based on home address.
    # Using geopy, we figure out the 3 closest fields not already covered by the
    # preferred / disallowed locations and stick those in a column.
    backup_locations = []
    for _, row in players.iterrows():
        lat, long = row[["latitude", "longitude"]]
        if pd.isnull(lat) or pd.isnull(long):
            backup_locations.append("")
            continue
        field_df = pd.DataFrame.from_dict(
            FIELD_LOCATIONS, orient="index", columns=["lat", "long"]
        )
        # Don't think about fields if they're already in preferred/disallowed locations
        mask = field_df.index.map(
            lambda f: f in row.fillna("")["preferred_locations"]
            or f in row.fillna("")["disallowed_locations"]
        ).values.astype(bool)
        field_df = field_df[~mask]
        if len(field_df) <= 3:
            backup_locations.append("")
            continue
        field_df["distance"] = field_df.apply(
            lambda r: get_dist(lat, long, r["lat"], r["long"]), axis=1
        )
        field_df = field_df.sort_values(by="distance")
        backup_locations.append(", ".join(field_df.head(3).index.values))
    players["backup_locations"] = backup_locations

    players["comment"] = (
        # players["comment"].fillna("") + " || " + players["extra_comment"].fillna("")
        players["extra_comment"].fillna("")
    )

    # Fill missing columns with nans
    for col in ordered_columns:
        if col not in players.columns:
            players[col] = np.nan

    players = players[ordered_columns]

    print(f"Finished merging. Total # of players: {len(players)}")
    return players


def _final_sweep(players):
    print("\n===Running final checks===")

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

    missing_first_name = pd.isnull(players.first_name)
    if missing_first_name.sum() > 0:
        print(f"{missing_first_name.sum()} players are missing a first name:")
        print(players[missing_first_name][["id", "first_name", "last_name"]])

    missing_grade = pd.isnull(players.grade)
    if missing_grade.sum() > 0:
        print(
            f"{missing_grade.sum()} players are missing a grade: "
            f"{_get_names(players[missing_grade])}"
        )

    missing_skill = pd.isnull(players.coach_skill) & pd.isnull(players.parent_skill)
    if missing_skill.sum() > 0:
        print(
            f"{missing_skill.sum()} players don't have a coach or parent skill. Automatically "
            "assigning them a skill of 5"
        )
        players.loc[missing_skill, "parent_skill"] = 5

    missing_goalie_skill = pd.isnull(players.goalie_skill)
    if missing_goalie_skill.sum() > 0:
        print(
            f"{missing_goalie_skill.sum()} players don't have a goalie skill. Automatically "
            "assigning them a skill of 6 (does not play goalie)."
        )
        players.loc[missing_goalie_skill, "goalie_skill"] = 6


def cross_match_names(df1, df2, suffixes):
    # dfs are assumed to have name_key columns

    matched_names = np.intersect1d(df1["name_key"].values, df2["name_key"].values)
    unmatched_df1 = df1[~df1["name_key"].isin(matched_names)]
    unmatched_df2 = df2[~df2["name_key"].isin(matched_names)]
    cross = unmatched_df1.merge(unmatched_df2, how="cross", suffixes=suffixes)
    keys = [f"name_key{s}" for s in suffixes]
    if cross.shape[0] == 0: return cross
    cross["score"] = cross.apply(lambda r: fuzz.ratio(r[keys[0]], r[keys[1]]), axis=1)
    return cross.sort_values(by="score", ascending=False)[[keys[0], keys[1], "score"]]


def main():
    args = parser.parse_args()
    
    #TODO: make argument validating logic simpler/more seamless

    if not args.division:
        handle_error("No division provided.", True)
    
    if not args.registration: 
        if args.folder: 
            args.registration = args.folder + "/registration.csv"
        else: 
            handle_error("Please provide a registration file.", True)

    if not args.coach_evals: 
        if args.folder:
            args.coach_evals = args.folder + "/coach_evals.csv"
        else:
            raise handle_error("Please provide a coach evaluations file.", True)
        
    if not args.output_file: 
        if args.folder:
            args.output_file = args.folder + "/prepared_player_data.csv"
        else:
            handle_error("Please provide a valid output file path.", True)
        
    if not args.parent_requests and args.folder: 
        args.parent_requests = args.folder + "/parent_requests.csv" 
    
    try: 
        validate_file(args.registration)
    except:
        handle_error(f"Invalid registration file path {args.registration}.", True)
    try:   
        validate_file(args.coach_evals)
    except:
        handle_error(f"Invalid coach evaluations file path {args.coach_evals}.", True)

    try: 
        validate_file(args.parent_requests)
    except:
        args.parent_requests = None

    # Load current registrations
    registrations = _load_registration_data(args.registration)

    # Pull team and coach score from spring 2022
    existing_players = _load_existing_player_data(args.coach_evals, args.division)
    existing_player_match = existing_players["name_key"].isin(registrations["name_key"])
    lower_division_match = pd.isnull(existing_players["team"]) & existing_player_match
    print(
        f"{existing_player_match.sum()} / {len(registrations)} registrations were matched to "
        f"existing player data. {lower_division_match.sum()} came from a lower division."
    )
    cross = cross_match_names(registrations, existing_players, ("_reg", "_old"))
    print(
        "If names are spelled differently across forms, they can't be automatically matched. \n"
        f"Please check the following list of potential name matches (printing top {args.matches}):"
    )
    print(cross.head(args.matches))
    print("Please edit the forms so the names match or manually update the player csv")

    # Load parent requests
    if args.parent_requests is not None:
        print("Parent requests found")
        parent_reqs = _load_parent_requests(args.parent_requests)
        parent_req_match = registrations["name_key"].isin(parent_reqs["name_key"])
        print(
            f"{parent_req_match.sum()} / {len(registrations)} players had matching parent requests"
        )
        cross = cross_match_names(registrations, parent_reqs, ("_reg", "_parent"))
        print(
            "If names are spelled differently across forms, they can't be automatically matched. \n"
            "Please check the following list of potential name matches (printing top "
            f"{args.matches}):"
        )
        print(cross.head(args.matches))
        print(
            "Please edit the forms so the names match or manually update the player csv"
        )
    else:
        print("No parent requests provided.")
        parent_reqs = pd.DataFrame(
            columns=[
                "name_key",
                "disallowed_locations",
                "preferred_locations",
                "preferred_days",
                "unavailable_days",
                "extra_comment",
                "teammate_requests",
            ]
        )

    # Merge the old data into the current registration data.
    players = _merge_data(existing_players, parent_reqs, registrations)

    # Do a final cleaning pass
    _final_sweep(players)

    if not args.output_file and args.folder: args.output_file = args.folder + "/prepared_player_data.csv"

    if args.replace or not os.path.exists(args.output_file):
        print(f"Saving to {args.output_file}")
        players.to_csv(args.output_file, index=False)
    else:
        handle_error(f"Not saving. {args.output_file} already exists. Use -r to replace", True)


if __name__ == "__main__":
    main()
