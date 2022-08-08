import argparse
import configparser

from tqdm import tqdm

from cyslf.models import League
from cyslf.optimize import find_best_moves
from cyslf.scorers import DEFAULT_WEIGHTS


parser = argparse.ArgumentParser(description="Assign players to teams")
parser.add_argument(
    "--input_stem",
    "-i",
    type=str,
    help="input csv stem. read '{stem}-players.csv' and '{stem}-teams.csv'",
)
parser.add_argument(
    "--output_stem",
    "-o",
    type=str,
    help="output csv stem. write outputs to '{stem}-players.csv' and '{stem}-teams.csv'",
)
parser.add_argument(
    "--config",
    "-c",
    type=str,
    help="config file with scorer weights.",
)


def main():
    args = parser.parse_args()

    player_input_file = f"{args.input_stem}-players.csv"
    team_input_file = f"{args.input_stem}-teams.csv"
    print(
        f"Loading league from {player_input_file} (players) and {team_input_file} (teams)"
    )
    league = League.from_csvs(player_input_file, team_input_file)

    weights = None
    if args.config is not None:
        config = configparser.ConfigParser()
        config.read(args.config)
        weights = {}
        for key in config["weights"].keys():
            weights[key] = float(config["weights"][key])
    else:
        weights = DEFAULT_WEIGHTS
    print(f"Using weights {weights}.")

    print(f"Starting to assign {len(league.available_players)} available players.")
    for i in tqdm(range(len(league.available_players))):
        player = league.get_next_player()
        best_moves = find_best_moves(player, league, depth=2, weights=weights)
        league.apply_moves(best_moves)
    league.details()

    # TODO: add override check
    player_output_file = f"{args.output_stem}-players.csv"
    team_output_file = f"{args.output_stem}-teams.csv"

    league.to_csvs(player_output_file, team_output_file)


if __name__ == "__main__":
    main()
