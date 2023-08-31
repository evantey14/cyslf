# CYS League Formation

`cyslf` automatically assigns players to teams based on registration data, coach evaluations, and parent requests.

For each league, there are two parts: (1) get all the raw form data into standard player and team csvs. (2) form teams from these standardized csvs!

Returning players are placed on their last season's team by default, then the remaining players are assigned while maintaining balanced teams and player convenience (see [Scoring](#scoring) for details).

# Quickstart
#### 0. Install [Python](https://www.python.org/downloads/) and open command prompt to run the following lines. (For Windows, try installing [Miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/windows.html) and using anaconda prompt instead.)
#### 1. Install `cyslf` by running `pip install cyslf`
#### 2. Convert addresses to coordinates. Example:

```

  convert-addresses --reg registrations.csv

  OR

  convert-addresses --folder ./girls5-6_data

```

* This command adds longitude and latitude columns to the registration csv containing the coordinates of the corresponding player's address. This step was originally part of the next step, but is now seperated out because the process of looking up addresses took the program a while. 
* The program may fail to find coordinates for some addresses, which is fine. This tends to happen when an address is mispelled somehow. In this case you can either fix the spelling in the registration file or fill in the latitude and longitude manually using Google Maps. 
* `--reg` sets the current registration csv. This should contain the player's address information seperated into columns `Street`, `City`, `Region`, and `Postal Code`. This should only contain players in one division, i.e. Boys Grades 3-4.
* `--folder` or `-f` can be used instead of `--reg` to provide the registration file. It sets the folder the registration file must exist in, and the file must be names `registration.csv`.

#### 3. Prepare a standard player csv from registration data. Example:

```
prepare-player-data --div "Boys Grades 3-4" --coach_evals coach-evaluations.csv --reg registrations.csv --par parent-requests.csv -o example-players.csv

OR

prepare-player-data --div "Girls Grades 7-8" --folder ./girls7-8_data -o prepared-player-data.csv

```
* This command takes raw form data and converts it into the standard player csv format (see example data below). It does a handful of things to clean up the data.
    * Players on teams from the prior season will be placed on those teams by default.
    * Players without skill are assigned a level of 5 (average)
    * Players without a goalie skill are assigned a level of 6 (does not play goalie)
    * Players coming from a lower division get their grades worsened by 1 point
    * Players are matched by names -- so if names are spelled differently on different forms, they won't get matched, so we'll print names that look similar and maybe should've been matched.
* After completion, open the csv and manually make adjustments.
    * Read the comments -- maybe parents are unable to reach certain fields
    * If you do edit cells, make sure the formatting is consistent. `Danehy` is not the same as
      `danehy`.
* `--div` sets the division. If your input is found in the "Division" column of the old registration data, that player is considered to be a continuing player in the division. You don't need to put the full division name. `"Boys Grades 3-4"` is good enough to match to `"Boys Grades 3-4 - Spring 2022 In-Town Soccer"` but you do need to be careful about spelling / upper case / lower case.
* `--coach_evals` sets the coach evaluations csv. This needs to have names, coach evaluations, and past teams for each player.
* `--par` sets the parent request csv. This should have practice location / day / teammate preferences.
* `--reg` sets the current registration csv. This should have all other player-relevant data. This should only contain players in one division, i.e. Boys Grades 3-4.
* `-m` sets the number of potential name matches to print. Default is `-m 5`.
* `-o` sets the output file.
* `-r` lets you replace the output file if it exists.
* `--folder`or `-f` can be used to replace `--coach_evals`, `--par`, and `--reg` by providing a directory that contains these three files. The names of the files must be `coach_evals.csv`, `parent_requests.csv`, and `registration.csv` (keep in mind parent requests is optional). Make sure the file names exactly match these names. Will atuomatically output a file names `prepared_player_data.csv`.
#### 4. Prepare a standard team csv
* These should have team name, practice day, and practice location (see example data below)
#### 5. Make teams! Example:
```
make-teams -i example-players.csv -t example-team.csv -o example-result.csv

OR

make-teams -f ./boys3-4_data -r
```
* This command reads the player and team csvs, assigns available players, and outputs the results as standard player and team csvs.
* `-i` sets the input player file.
* `-t` sets the team information file.
* `-o` sets the output player file.
* `-c` can optionally be used to set a config file to control scoring weights (see below).
* `-d` can optionally be used to set the search depth. This is how hard the algorithm tries to
  rearrange players. 4 or 5 will probably take too long to run, 2 or 3 are probably good enough.
* `-r` can be used to replace the output file when it already exists.
* `-f` can be used similarly to  `--folder` in the prepare player data step. Rather than providing files with `-i`, `-t`, `-o`, and `-c`, only provide the directory containing each of these files. The files must be named `prepared_player_data.csv`, `teams.csv`, and `final_results.csv` (which is automatically created if it doesn't already exist). You may also include a `weights.txt` file as the `-c` option. See the example for details on formatting.
#### 6. Review!
* Load the player csv and see if any adjustments need to be made.
* If you want to re-run league formation, unfreeze players and remove their team values, download and run step 4 again.

# Example Data
The `make-teams` command reads files in the standard format and outputs files in the standard format. This means you should be able to open these in google sheets / excel and move players around easily.
See [this google sheets example](TODO).
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
* `backup_locations`: practice fields determined automatically based on player's home address
* `disallowed_locations`: practice fields that the player can't reach
* `preferred_days`: days player prefers to have practice. must be a string of characters from "MTWRF". For example, "MTR" means the player prefers to practice on Monday, Tuesday, or Thursday.
* `unavailable_days`: days player is not able to practice. similar format as above.
* `teammate_requests`: teammate names
* `lock`: `TRUE` or `FALSE`. If a player is locked and already assigned to a compatible team before make_teams is called, they'll remain on that team. If they're unlocked (`lock` == `FALSE`) or the team they're assigned to isn't compatible (i.e. incompatible practice day/location) then they'll be assigned a new team.
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
Sennot
```

# Algorithm
This implementation uses a greedy algorithm. We order players by skill then go through and assign them to the team that gives the best overall league score.

To assign a specific player, we try placing them on each team and keep track of which arrangement produces the highest score. We also try placing them on each team and having that team "trade" a player to another team (again looking for the highest scoring player arrangement). We can continue trying to trade players and evaluating arrangements by increasing the `-d` argument to `make-teams` (`make-teams -d 4 ...` tells the algorithm to go 3 trades deep when conducting the search). Note that some arrangements are invalid -- for example if a player can't practice on Wednesday, they can't be placed on a team that practices Wednesday.

More optimal algorithms exist, but this algorithm is one of the most straightforward to understand. It also lends itself well to become a "recommended assignment" tool if we ever want to have the library give suggestions one player at a time.


# Scoring
The score of a particular arrangement of players is composed of a bunch of independent scores. The independent scores are combined with a weighted sum. These weights can be controlled by passing a config file to `make-teams` (eg `make-teams -c weights.txt ...`). Example weights file (put in `weights.txt`):
```
[weights]
skill = 1           # balance average team skill
grade = 1           # balance average team grade
size = 1            # balance average team size
first_round = 1     # balance # of top rank players (skill=1)
top = 1             # balance the # of top tier players (skill=2, 3)
mid = 1             # balance the # of mid tier players (skill=4, 5, 6)
bottom = 1          # balance the # of bottom tier players (skill=7, 8, 9, 10)
goalie = 1          # balance goalie skill
location = 1        # minimize player distance to practice field
practice_day = 1    # maximize # of players' practicing on their preferred day
teammate = 1        # honor player teammate requests
```
If you run formation and teams aren't as good as you'd like for some score type, try increasing the weight. (For example if you really really care about giving players a nearby practice field, you could set `location = 1000`).
