from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from xsense import XSense
from xsense.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired


def build_snapshot(username: str, password: str) -> Dict[str, List[Dict[str, Any]]]:
    api = XSense()
    api.init()
    api.login(username, password)
    api.load_all()

    stations: List[Dict[str, Any]] = []
    for house in api.houses.values():
        try:
            api.get_house_state(house)
        except NotFoundError:
            pass

        for station in house.stations.values():
            try:
                api.get_station_state(station)
            except NotFoundError:
                pass

            try:
                api.get_state(station)
            except APIFailure:
                pass
            except SessionExpired:
                raise

            stations.append(
                {
                    "houseId": house.house_id,
                    "houseName": house.name,
                    "stationId": station.entity_id,
                    "stationName": station.name,
                    "deviceSN": station.sn,
                    "type": station.type,
                    "values": dict(station.data),
                }
            )

    return {"stations": stations}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username")
    parser.add_argument("--password")
    args = parser.parse_args()

    username = args.username or os.getenv("XSENSE_USERNAME")
    password = args.password or os.getenv("XSENSE_PASSWORD")

    if not username or not password:
        print("XSense credentials not provided", file=sys.stderr)
        return 2

    try:
        snapshot = build_snapshot(username, password)
    except (AuthFailed, APIFailure, SessionExpired, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    json.dump(snapshot, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
