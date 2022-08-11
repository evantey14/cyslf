import pandas as pd

from ..models import Player


example_player = Player(
    id=1,
    first_name="first",
    last_name="last",
    grade=3,
    skill=4,
    coach_skill=pd.NA,
    parent_skill=4,
    goalie_skill=6,
    unavailable_days="",
    preferred_days="MWR",
    disallowed_locations="Danehy",
    preferred_locations="Ahern,Donnelly",
    teammate_requests="Lionel Messi",
    frozen=True,
    school="school",
    comment=pd.NA,
)


def test_player_io():
    """Weakly test that we can read and write players."""
    # This is not a super detailed / rigorous test (particularly of all the validation) but it
    # should tell us naively whether or not reading / writing is stable
    assert example_player == Player.from_raw_dict(example_player.to_raw_dict())
