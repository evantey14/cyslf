# Skill rating divisions
FIRST_ROUND_SKILL = 1
TOP_TIER_SKILLS = [2, 3]
MID_TIER_SKILLS = [4, 5, 6]
BOTTOM_TIER_SKILLS = [7, 8, 9, 10]

DAY_MAP = {
    "Monday": "M",
    "Tuesday": "T",
    "Wednesday": "W",
    "Thursday": "R",
    "Friday": "F",
}

FIELD_MAP = {
    "East": ["Ahern", "Donnelly"],
    "Central": ["Common", "Sacramento"],
    "Cambridgeport": ["Pacific", "Magazine"],
    "West": ["Danehy", "Raymond", "Maher"],
    "North": ["Danehy", "Raymond", "Russell"],
}


def get_dist(x1, y1, x2, y2):
    """Calculate the Euclidean distance between two points."""
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


# These locations were pulled from google maps (lat, long)
FIELD_LOCATIONS = {
    "Ahern": (42.368859176331476, -71.08647586593241),
    "Donnelly": (42.370366682994714, -71.0917891174976),
    "Common": (42.37671780489148, -71.12093358866208),
    "Pacific": (42.36053839550282, -71.10284706167454),
    "Magazine": (42.35548441752288, -71.11382685798023),
    "Danehy": (42.389099968964416, -71.13300644263798),
    "Raymond": (42.38671764378315, -71.12781645797926),
    "Maher": (42.38962880908857, -71.14937874050884),
    "Sacramento": (42.38317187834224, -71.11773101380282),
    "Russell": (42.39644583460877, -71.13739422914362),
}

# Threshold below which a player counts as a goalie
GOALIE_THRESHOLD = 3
