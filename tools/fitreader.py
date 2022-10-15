import fitparse
import datetime

import os

from typing import Tuple, List
from tools.model import GeoPoint, Track

import logging
log = logging.getLogger(__name__)


RECORD_MESSAGE = 'record'
ACTIVITY_MESSAGE = 'activity'


class InvalidTimezone(Exception):
    pass


class InvalidPoint(Exception):
    pass


def __from_semicircles(value: float) -> float:
    # https://forums.garmin.com/forum/developers/garmin-developer-information/60220-
    return float(value) * 180 / (2 ** 31)


def get_point(values: dict) -> GeoPoint:
    timestamp = int((values['timestamp'] - datetime.datetime(1970, 1, 1)).total_seconds())
    assert 1000000000 < timestamp < 2000000000
    if 'enhanced_altitude' in values:
        assert values['enhanced_altitude'] == values['altitude']

    longitude = values.get('position_long')
    latitude = values.get('position_lat')
    if (longitude is None) or (latitude is None):
        raise InvalidPoint('No longitude on latitude')

    altitude = values['altitude']
    assert altitude is not None

    longitude = __from_semicircles(longitude)
    latitude = __from_semicircles(latitude)
    return GeoPoint(
        longitude=float(f'{longitude:.9f}'),
        latitude=float(f'{latitude:.9f}'),
        altitude=float(f'{altitude:.3f}'),
        cadence=values.get('cadence') or None,
        heart_rate=values.get('heart_rate') or None,
        timestamp=timestamp,
    )


def get_activity_timezone(fit_file: fitparse.FitFile) -> datetime.timezone:
    activity_messages = list(fit_file.get_messages(ACTIVITY_MESSAGE))
    assert len(activity_messages) == 1
    activity_values = activity_messages[0].get_values()
    timestamp = activity_values['timestamp']
    local_timestamp = activity_values['local_timestamp']

    timedelta = local_timestamp - timestamp
    if timedelta not in [
        datetime.timedelta(seconds=10800),
        datetime.timedelta(seconds=14400),
    ]:
        raise InvalidTimezone(f'Invalid timezone: {timedelta}')

    return datetime.timezone(timedelta)


def get_points_and_failures(fit_file: fitparse.FitFile) -> Tuple[List[GeoPoint], List[int]]:
    points = []
    failures = []
    for message_index, message in enumerate(fit_file.get_messages(name=RECORD_MESSAGE)):
        try:
            values = message.get_values()
            points.append(get_point(values))
        except InvalidPoint:
            failures.append(message_index)
        except:
            log.error(f'failed at {message_index}')
            raise

    return points, failures


def read_fit_file(filename, raise_on_error=True) -> Track:
    try:
        fit_file = fitparse.FitFile(filename, check_crc=True)
        crc_ok = True
    except fitparse.utils.FitCRCError:
        fit_file = fitparse.FitFile(filename, check_crc=False)
        crc_ok = False

    activity_timezone = get_activity_timezone(fit_file)
    points, failures = get_points_and_failures(fit_file)

    track = Track(
        filename=filename,
        points=points,
        failures=failures,
        activity_timezone=activity_timezone,
        correct_crc=crc_ok,
    )

    if raise_on_error and not track.is_valid:
        log.error(f'{track!r}')
        raise RuntimeError(f'{track} is invalid')
    return track
