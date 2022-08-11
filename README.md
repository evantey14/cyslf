# CYS League Formation

`cyslf` automatically assigns players to teams based on registration data, coach evaluations, and parent requests.

For each league, there are two parts: (1) get all the raw form data into standard player and team csvs. (2) form teams from these standardized csvs!

Returning players are placed on their last season's team by default, then the remaining players are assigned while maintaining balanced teams and player convenience (see [Scoring](#scoring) for details).

# Quickstart
#### 0. Install [Python](https://www.python.org/downloads/) and open command prompt to run the following lines.
#### 1. Install `cyslf` by running `pip install cyslf`
#### 2. Prepare a standard player csv from registration data. Example:
```
prepare-player-data --div "Boys Grade 3-4" --old_reg  old-registrations.csv --reg registrations.csv --par parent-requests.csv -o example
```
* This command takes raw form data and converts it into the standard player csv format (see example data below). It does a handful of things to clean up the data.
    * Players on teams from the prior season will be placed on those teams by default.
    * Players without skill are assigned a level of 5 (average)
    * Players without a goalie skill are assigned a level of 6 (does not play goalie)
    * Players coming from a lower division get their grades worsened by 1 point
* After completion, open the csv and manually make adjustments.
    * Read the comments -- maybe parents are unable to reach certain fields
    * If you do edit cells, make sure the formatting is consistent. `Danehy` is not the same as
      `danehy`.
* `--div` sets the division. It's used for looking up the division in the old registration data.
* `--old_reg`  sets the past data csv. This needs to have names, coach evaluations, and teams for each player.
* `--par` sets the parent request csv. This should have practice location / day / teammate preferences.
* `--reg` sets the current registration csv. This should have all other player-relevant data.
* `-o` sets the output file prefix. `example` means this will write to `example-players.csv`
#### 3. Prepare a standard team csv
* These should have team name, practice day, and practice location (see example data below)
#### 4. Make teams! Example:
```
make-teams -i example -o example-result
```
* This command reads the player and team csvs, assigns available players, and outputs the results as standard player and team csvs.
* `-i` sets the input file prefixes. `example` means read `example-players.csv` and `example-teams.csv`
* `-o` sets the output file prefixes. `example-result` means write to `example-result-players.csv` and `example-result-teams.csv`
* `-c` can optionally be used to set a config file to control scoring weights (see below).
* `-d` can optionally be used to set the search depth. This is how hard the algorithm tries to
  rearrange players. 4 or 5 will probably take too long to run, 2 or 3 are probably good enough.
#### 5. Review!
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
* `goalie_skill`: coach evaluated skill (1 = good, 6 = does not play goalie)
* `preferred_locations`: preferred practice field names
* `disallowed_locations`: practice fields that the player can't reach
* `preferred_days`: days player prefers to have practice. must be a string of characters from "MTWRF". For example, "MTR" means the player prefers to practice on Monday, Tuesday, or Thursday.
* `unavailable_days`: days player is not able to practice. similar format as above.
* `teammate_requests`: teammate names
* `frozen`: `TRUE` or `FALSE`.
* `school`: school name
* `comment`: special requests from the registration form
### Standard team csv
The standard player csv is expected to have the following columns:
* `name`: team name
* `practice_day`: one of `M`, `T`, `W`, `R`, `F` (Monday, Tuesday, Wednesday, Thursday, Friday)
* `location`: practice field name. Valid field names are listed below.

Valid field names
```
Ahern
Common
Danehy
Donnelly
Magazine
Maher
Pacific
Raymond
Russell
```

# Algorithm
This implementation uses a greedy algorithm. We order players by skill then go through and assign them to the team that gives the best overall league score.

To assign a specific player, we try placing them on each team and keep track of which arrangement produces the highest score. We also try placing them on each team and having that team "trade" a player to another team (again looking for the highest scoring player arrangement). We can continue trying to trade players and evaluating arrangements by increasing the `-d` argument to `make-teams` (`make-teams -d 4 ...` tells the algorithm to go 3 trades deep when conducting the search). Note that some arrangements are invalid -- for example if a player can't practice on Wednesday, they can't be placed on a team that practices Wednesday.

More optimal algorithms exist, but this algorithm is one of the most straightforward to understand. It also lends itself well to become a "recommended assignment" tool if we ever want to have the library give suggestions one player at a time.


# Scoring
The score of a particular arrangement of players is composed of a bunch of independent scores. The independent scores are combined with a weighted sum. These weights can be controlled by passing a config file to `make-teams` (eg `make-teams -c weights.cfg ...`). Example weights file (put in `weights.cfg`):
```
[weights]
skill = 10          # balance average team skill
grade = 10          # balance average team grade
size = 10           # balance average team size
elite = 10          # balance # of top tier players
goalie = 10         # balance goalie skill
location = 10       # minimize player distance to practice field
practice_day = 10   # maximize # of players' practicing on their preferred day
teammate = 10       # honor player teammate requests
```
If you run formation and teams aren't as good as you'd like for some score type, try increasing the weight. (For example if you really really care about giving players a nearby practice field, you could set `location = 1000`).
