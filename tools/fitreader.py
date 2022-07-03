import fitparse
import datetime

import pprint
import os

from typing import Tuple, List, Optional
from tools.model import GeoPoint, Track

import logging
log = logging.getLogger(__name__)


def __from_semicircles(value):
    # https://forums.garmin.com/forum/developers/garmin-developer-information/60220-
    return float(value) * 180 / (2 ** 31)


def parse_values(values: dict) -> Optional[GeoPoint]:
    timestamp = int((values['timestamp'] - datetime.datetime(1970, 1, 1)).total_seconds())
    assert 1000000000 < timestamp < 2000000000
    if 'enhanced_altitude' in values:
        assert values['enhanced_altitude'] == values['altitude']

    longitude = values.get('position_long')
    latitude = values.get('position_lat')
    if (longitude is None) or (latitude is None):
        return None

    altitude = values['altitude']
    assert altitude is not None

    longitude = __from_semicircles(longitude)
    latitude = __from_semicircles(latitude)
    point = GeoPoint(
        longitude=float(f'{longitude:.9f}'),
        latitude=float(f'{latitude:.9f}'),
        altitude=float(f'{altitude:.3f}'),
        cadence=values.get('cadence') or None,
        heart_rate=values.get('heart_rate') or None,
        timestamp=timestamp,
    )
    return point



def get_points(filename, check_crc: bool) -> Tuple[List[GeoPoint], List[int]]:
    points = []
    failures = []

    fit_file = fitparse.FitFile(filename, check_crc=check_crc)
    for message_index, message in enumerate(fit_file.get_messages(name='record')):
        values = message.get_values()
        try:
            point = parse_values(values)
            if point:
                points.append(point)
            else:
                failures.append(message_index)
        except:
            log.error(f'failed at {message_index}')
            raise

    return Track(
        filename=filename,
        points=points,
        failures=failures,
    )


def read_fit_file(filename, raise_on_error=True) -> Track:
    log.debug(f'Loading {filename}')
    try:
        track = get_points(filename, check_crc=True)
        track.correct_crc = True
    except fitparse.utils.FitCRCError:
        log.debug(f'FitCRCError on {filename}')
        track = get_points(filename, check_crc=False)
        track.correct_crc = False

    if raise_on_error and not track.is_valid:
        log.error(f'{track!r}')
        raise RuntimeError(f'{track} is invalid')
    return track
