def get_distance(p1, p2):
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5


practice_fields = [
    (42.38980588369338, -71.13301159861518),  # danehy
    (42.37292538868882, -71.08361099742957),  # gsm
    (42.376852476244125, -71.12084010564928),  # common
]

# Get a global distance scale
max_distance = 0
for location_i in practice_fields:
    for location_j in practice_fields:
        distance = get_distance(location_i, location_j)
        if distance > max_distance:
            max_distance = distance
