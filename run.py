import argparse
import configparser

from tqdm import tqdm

from cyslf.models import League
from cyslf.optimize import find_best_moves


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


if __name__ == "__main__":
    args = parser.parse_args()

    league = League.from_csvs(
        f"{args.input_stem}-players.csv", f"{args.input_stem}-teams.csv"
    )

    weights = None
    if args.config is not None:
        config = configparser.ConfigParser()
        config.read(args.config)
        weights = {}
        for key in config["weights"].keys():
            weights[key] = float(config["weights"][key])

    for i in tqdm(range(len(league.available_players))):
        player = league.get_next_player()
        best_moves = find_best_moves(player, league, depth=1, weights=weights)
        league.apply_moves(best_moves)
    league.details()

    # TODO: add override check
    league.to_csvs(f"{args.output_stem}-players.csv", f"{args.output_stem}-teams.csv")
