from .models import League


def breaks_schedule_constraint(league: League):
    """True if schedule constraint is broken. False if it's fine."""
    for team in league.teams:
        for player in team.players:
            if team.practice_day in player.unavailable_days:
                return True
    return False
