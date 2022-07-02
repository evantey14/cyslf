from functools import cache


@cache
def get_distance(lat1, long1, lat2, long2):
    return ((lat1 - lat2) ** 2 + (long1 - long2) ** 2) ** 0.5


practice_fields = [  # latitude longitude
    (42.38980588369338, -71.13301159861518),  # danehy
    (42.37292538868882, -71.08361099742957),  # gsm
    (42.376852476244125, -71.12084010564928),  # common
]

# Maximum distance between fields. Natural length scale for scoring
max_distance = 0.052205081257465445
