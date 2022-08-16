import argparse
import configparser
import os
import sys

from tqdm import tqdm

from cyslf.models import League
from cyslf.optimize import find_best_moves
from cyslf.scorers import DEFAULT_WEIGHTS
from cyslf.validation import validate_file


parser = argparse.ArgumentParser(description="Assign players to teams")
parser.add_argument(
    "--input_player_csv",
    "-i",
    type=str,
    help="input player csv. eg 'boys34-players.csv'",
)
parser.add_argument(
    "--output_player_csv",
    "-o",
    type=str,
    help="output player csv. eg 'boys34-results.csv'",
)
parser.add_argument(
    "--team_csv",
    "-t",
    type=str,
    help="team csv. should contain team information (name, location, etc)",
)
parser.add_argument("--config", "-c", type=str, help="config file with scorer weights.")
parser.add_argument("--depth", "-d", type=int, default=2, help="search depth")
parser.add_argument(
    "--replace",
    "-r",
    action="store_true",
    help="Overwrite the output file if it exists",
)


def main():
    args = parser.parse_args()

    validate_file(args.input_player_csv)
    validate_file(args.team_csv)

    if not args.replace and os.path.exists(args.output_player_csv):
        print(
            f"Warning: {args.output_player_csv} already exists. Use `-r` to replace it"
        )
        sys.exit()

    print(
        f"Loading league from {args.input_player_csv} (players) and {args.team_csv} (teams)"
    )
    league = League.from_csvs(args.input_player_csv, args.team_csv)

    weights = None
    if args.config is not None:
        validate_file(args.config)
        config = configparser.ConfigParser(inline_comment_prefixes="#")
        config.read(args.config)
        weights = {}
        for key in config["weights"].keys():
            weights[key] = float(config["weights"][key])
    else:
        weights = DEFAULT_WEIGHTS
    print(f"Using weights {weights}")
    print(f"Using depth {args.depth}")
    print(f"Starting to assign {len(league.available_players)} available players.")
    for i in tqdm(range(len(league.available_players))):
        player = league.get_next_player()
        best_moves = find_best_moves(player, league, depth=args.depth, weights=weights)
        league.apply_moves(best_moves)
    league.details()

    league.to_csv(args.output_player_csv)


if __name__ == "__main__":
    main()
