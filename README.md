# CYS League Formation

`cyslf` automatically assigns players to teams based on registration data, coach evaluations, and parent requests.

For each league, there are two parts: (1) get all the raw form data into standard player and team csvs. (2) form teams from these standardized csvs!


# Quickstart
#### 0. Install [Python](https://www.python.org/downloads/) and open command prompt to run the following lines.
#### 1. Install `cyslf` by running `pip install cyslf`
#### 2. Prepare a standard player csv from registration data. Example:
```
prepare-player-data --div "Boys Grade 3-4" --old_reg  Spring2022-registrations.csv --reg 3-4boys-sample-22registration.csv -o b34
```
* This command takes raw form data and converts it into the standard player csv format (see example data below). Players on teams from the prior season will be fixed to those teams by default.
* After completion, you should probably manually inspect the results and make any adjustments necessary (eg read through the comments and place players on teams)
* `--div` sets the division. It's used for looking up the division in the old registration data
* `--old_reg`  sets the past data csv. This needs to have names, coach evaluations, and teams for each player.
* `---reg` sets the current registration csv. This should have all other player-relevant data.
* `-o` sets the output file prefix. `b34` means this will write to `b34-players.csv`
#### 3. Prepare a standard team csv
* These should have team name, practice day, and practice location (see example data below)
#### 4. Make teams! Example:
```
make-teams -i b34 -o b34-result
```
* This command reads the player and team csvs, assigns available players, and outputs the results as standard player and team csvs.
* `-i` sets the input file prefixes. `b34` means read `b34-players.csv` and `b34-teams.csv`
* `-o` sets the output file prefixes. `b34-result` means write to `b34-result-players.csv` and `b34-result-teams.csv`
* `-c` can optionally be used to set a config file to control scoring weights (see below).
5. Review!
* Load the player csv and see if any adjustments need to be made.
* If you want to re-run league formation, unfreeze players and remove their team values, download and run step 4 again.

# Example Data
The `make-teams` command reads files in the standard format and outputs files in the standard format. This means you should be able to open these in google sheets / excel and move players around easily.
See [this google sheets example](https://docs.google.com/spreadsheets/d/1jplZgVjpE15p7ttRaTPetmnemrGZ8TJ_etgD3tVFBwU/edit#gid=1433571872).
### Standard player csv
The standard player csv is expected to have the following columns:
* `id`: a unique player ID number
* `last_name`: player last name
* `first_name`: player first name
* `grade`: player grade number
* `team`: assigned team (if any)
* `coach_skill`: coach evaluated skill (1 = good, 10 = bad)
* `parent_skill`: parent evaluated skill (used when coach evaluation is missing)
* `longitude`: player's home longitude
* `latitude`: player's home latitude
* `preferred_days`: days player prefers to have practice. must be a string of characters from "MTWRF". For example, "MTR" means the player prefers to practice on Monday, Tuesday, or Thursday.
* `unavailable_days`: days player is not able to practice. similar format as above.
* `frozen`: `TRUE` or `FALSE`.
* `school`: school name
* `comment`: special requests from the registration form
### Standard team csv
The standard player csv is expected to have the following columns:
* `name`: team name
* `practice_day`: one of `M`, `T`, `W`, `R`, `F` (Monday, Tuesday, Wednesday, Thursday, Friday)
* `latitude`: practice field latitude
* `longitude`: practice field longitude

# Algorithm
This implementation uses a greedy algorithm. We order players by skill then go through and assign them to the team that gives the best overall league score.

To assign a specific player, we try placing them on each team and keep track of which arrangement produces the highest score. We also try placing them on each team and having that team "trade" a player to another team (again looking for the highest scoring player arrangement). Some arrangements are invalid -- for example if a player can't practice on Wednesday, they can't be placed on a team that practices Wednesday.

More optimal algorithms exist, but this algorithm is one of the most straightforward to understand. It also lends itself well to as a "recommended assignment" tool if we ever want to have the library give suggestions one player at a time.


# Scoring
The score of a particular arrangement of players is composed of a bunch of independent scores. The independent scores are combined with a weighted sum. These weights can be controlled by passing a config file to `make-teams` (eg `make-teams -c weights.cfg ...`). Example weights file (put in `weights.cfg`):
```
[weights]
skill = 30          # balance average team skill
grade = 30          # balance average team grade
size = 15           # balance average team size
elite = 15          # balance # of top tier players
location = 5        # minimize player distance to practice field
practice_day = 5    # maximize # of players' practicing on their preferred day
```
If you run formation and teams aren't as good as you'd like for some score type, try increasing the weight. (For example if you really really cared giving players a nearby practice field, you could set `location = 100`).
