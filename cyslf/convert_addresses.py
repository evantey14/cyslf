import argparse
import logging
import os

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
import numpy as np
import pandas as pd
from thefuzz import fuzz
from tqdm import tqdm

from cyslf.utils import DAY_MAP, FIELD_LOCATIONS, FIELD_MAP, get_dist, handle_error
from cyslf.validation import request_validation, validate_file


geolocator = Nominatim(user_agent="cyslf")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1 / 2)
tqdm.pandas()
pd.set_option("display.max_rows", None)

parser = argparse.ArgumentParser(
    description="Process raw registration forms into a standard csv."
)

# keep
parser.add_argument(
    "--registration", "--reg", type=str, help="Current registration csv."
)

parser.add_argument(
    "--folder",
    "-f",
    type=str,
    help="Folder containing registrations",
    default=None,
)

def _lookup_location(address):
    # If an address is poorly formed, geopy gives sad-looking warnings,
    # so let's temporarily disable this.
    logging.getLogger("geopy").setLevel(logging.ERROR)
    location = geocode(address)
    logging.getLogger("geopy").setLevel(logging.WARNING)
    if location:
        return location.latitude, location.longitude
    else:
        print("\033[1m" + f"Failed to find address: {address}" + "\033[0m")
        return np.nan, np.nan

def _convert_addresses(filename):
    print(f"\n===Reading registration data from {filename}===")
    registrations_raw = pd.read_csv(filename)
    registrations_raw["Postal Code"] = registrations_raw["Postal Code"].apply(lambda x: "0" + str(x))

    # Look up player latitude / longitude
    print("Converting addresses to latitude / longitude")
    registrations_raw["Postal Code"] = registrations_raw["Postal Code"].astype(str)
    registrations_raw["Address"] = registrations_raw[
        ["Street", "City", "Region", "Postal Code"]
    ].agg(", ".join, axis=1)

    

    registrations_raw["Location"] = registrations_raw["Address"].progress_apply(
        _lookup_location
    )
    registrations_raw["latitude"] = registrations_raw["Location"].apply(lambda x: x[0])
    registrations_raw["longitude"] = registrations_raw["Location"].apply(lambda x: x[1])

    registrations_raw = registrations_raw.drop(
        columns=["Location", "Address"]
    )

    registrations_raw.to_csv(filename, index = False)

    return 

def main():
    args = parser.parse_args()
    if not args.registration: 
        if args.folder:
            args.registration = args.folder + "/registration.csv"
        else: 
            handle_error("Please provide a registration file.", True)
            
    try: 
        validate_file(args.registration)
    except:
        handle_error(f"Invalid registration file path {args.registration}.", True)

    _convert_addresses(args.registration)



if __name__ == "__main__":
    main()
