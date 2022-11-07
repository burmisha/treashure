import fitparse
import datetime

import os

from typing import Tuple, List, Optional
from tools.model import GeoPoint, Track

import logging
log = logging.getLogger(__name__)


RECORD_MESSAGE = 'record'
ACTIVITY_MESSAGE = 'activity'


class InvalidTimezone(Exception):
    pass


def __from_semicircles(value: float) -> float:
    # https://forums.garmin.com/forum/developers/garmin-developer-information/60220-
    return float(value) * 180 / (2 ** 31)


def get_point(values: dict) -> GeoPoint:
    timestamp = int((values['timestamp'] - datetime.datetime(1970, 1, 1)).total_seconds())
    assert 1000000000 < timestamp < 2000000000

    longitude = values.get('position_long')
    if longitude is not None:
        longitude = __from_semicircles(longitude)
        longitude = float(f'{longitude:.9f}')

    latitude = values.get('position_lat')
    if latitude is not None:
        latitude = __from_semicircles(latitude)
        latitude = float(f'{latitude:.9f}')

    altitude = values.get('altitude')
    if 'enhanced_altitude' in values:
        assert values['enhanced_altitude'] == altitude
    if altitude is not None:
        altitude = float(f'{altitude:.3f}')

    speed = values.get('speed')
    if 'enhanced_speed' in values:
        assert values['enhanced_speed'] == speed
    if speed is not None:
        speed = float(f'{speed:.3f}')

    distance_m = values['distance']
    if distance_m is not None:
        distance_m = float(f'{distance_m:.2f}')

    cadence = values.get('cadence')
    if cadence is not None:
        cadence = int(cadence)

    heart_rate = values.get('heart_rate')
    if heart_rate is not None:
        heart_rate = int(heart_rate)

    return GeoPoint(
        longitude=longitude,
        latitude=latitude,
        altitude=altitude,
        cadence=cadence,
        heart_rate=heart_rate,
        timestamp=timestamp,
        speed=speed,
        distance_m=distance_m,
    )


def get_activity_timezone(fit_file: fitparse.FitFile) -> Optional[datetime.timezone]:
    activity_messages = list(fit_file.get_messages(ACTIVITY_MESSAGE))
    assert len(activity_messages) == 1
    activity_values = activity_messages[0].get_values()
    timestamp = activity_values['timestamp']
    local_timestamp = activity_values.get('local_timestamp')
    if local_timestamp is not None:

        timedelta = local_timestamp - timestamp
        if timedelta not in [
            datetime.timedelta(seconds=10800),
            datetime.timedelta(seconds=14400),
        ]:
            raise InvalidTimezone(f'Invalid timezone: {timedelta}')

        return datetime.timezone(timedelta)
    else:
        return None


def read_fit_file(filename, raise_on_error=True) -> Track:
    try:
        fit_file = fitparse.FitFile(filename, check_crc=True)
        crc_ok = True
    except fitparse.utils.FitCRCError:
        fit_file = fitparse.FitFile(filename, check_crc=False)
        crc_ok = False

    activity_timezone = get_activity_timezone(fit_file)
    points = [
        get_point(message.get_values())
        for message in fit_file.get_messages(name=RECORD_MESSAGE)
    ]

    track = Track(
        filename=filename,
        points=points,
        activity_timezone=activity_timezone,
        correct_crc=crc_ok,
    )

    if raise_on_error and not track.is_valid:
        log.error(f'{track!r}')
        raise RuntimeError(f'{track} is invalid')
    return track
