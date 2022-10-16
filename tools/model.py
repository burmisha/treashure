from typing import List, Optional
import attr
import datetime
import library
import os
from functools import cached_property
import re

@attr.s
class GeoPoint:
    longitude: Optional[float] = attr.ib(default=None)
    latitude: Optional[float] = attr.ib(default=None)
    altitude: Optional[float] = attr.ib(default=None)
    timestamp: Optional[int] = attr.ib(default=None)
    cadence: Optional[int] = attr.ib(default=None)
    heart_rate: Optional[int] = attr.ib(default=None)
    distance_m: Optional[float] = attr.ib(default=None)
    speed: Optional[float] = attr.ib(default=None)

    @property
    def datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.timestamp)

    @property
    def long_lat(self) -> List[float]:
        return [self.longitude, self.latitude]

    @property
    def lat_long(self) -> List[float]:
        return [self.latitude, self.longitude]

    @property
    def is_ok(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def yandex_maps_link(self):
        text = f'{self.latitude}%2C{self.longitude}'
        ll = f'{self.longitude}%2C{self.latitude}'
        return f'https://yandex.ru/maps/?ll={ll}&mode=search&sll={ll}&text={text}&z=15'


class ErrorThreshold:
    MIN_COUNT = 50
    SHARE = 0.9


VIEW_MARGIN = 0.01


@attr.s
class Track:
    filename: str = attr.ib()
    points: List[GeoPoint] = attr.ib()
    correct_crc: Optional[bool] = attr.ib(default=None)
    activity_timezone: Optional[datetime.timezone] = attr.ib(default=None)

    @property
    def start_timestamp(self) -> float:
        if self.points:
            return self.points[0].timestamp
        basename = os.path.basename(self.filename).split('.')[0]
        try:
            dt = datetime.datetime.strptime(basename, '%Y-%m-%d-%H-%M-%S')
            return (dt - datetime.datetime(1970, 1, 1)).total_seconds()
        except ValueError:
            return 0.0

        return 0.0

    @property
    def start_point(self) -> GeoPoint:
        return self.points[0]

    @property
    def finish_point(self) -> GeoPoint:
        return self.points[-1]

    @property
    def start_ts(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.start_timestamp)

    @cached_property
    def max_lat(self) -> float:
        return max(point.latitude for point in self.points)

    @cached_property
    def max_long(self) -> float:
        return max(point.longitude for point in self.points)

    @cached_property
    def min_lat(self) -> float:
        return min(point.latitude for point in self.points)

    @cached_property
    def min_long(self) -> float:
        return min(point.longitude for point in self.points)

    @cached_property
    def min_long_view(self) -> float:
        return self.min_long - (self.max_long - self.min_long) * VIEW_MARGIN

    @cached_property
    def max_long_view(self) -> float:
        return self.max_long + (self.max_long - self.min_long) * VIEW_MARGIN

    @cached_property
    def min_lat_view(self) -> float:
        return self.min_lat - (self.max_lat - self.min_lat) * VIEW_MARGIN

    @cached_property
    def max_lat_view(self) -> float:
        return self.max_lat + (self.max_lat - self.min_lat) * VIEW_MARGIN

    @cached_property
    def middle_lat(self) -> float:
        return (self.max_lat + self.min_lat) / 2

    @cached_property
    def middle_long(self) -> float:
        return (self.max_long + self.min_long) / 2

    @cached_property
    def min_max_lat_long(self) -> List[List[float]]:
        return [
            [self.min_lat_view, self.min_long_view],
            [self.max_lat_view, self.max_long_view],
        ]

    @cached_property
    def year_dir(self) -> str:
        return self.start_ts.strftime('%Y')

    @cached_property
    def basename(self):
        return os.path.basename(self.filename)

    @cached_property
    def canonic_filename(self):
        return os.path.join(os.path.dirname(self.filename), self.canonic_basename)

    @cached_property
    def canonic_basename(self):
        basename, extension = self.basename.split('.')
        basename = basename.replace(' ', '-').replace('--', '-').replace('--', '-')
        assert extension.upper() == 'FIT'
        date_str = self.start_ts.strftime('%Y-%m-%d-%H-%M-%S')
        if re.match(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\w{8}$', basename):
            new_basename = basename.replace('_', '-', 1)
        elif re.match(r'^\d{4}-\d{2}-\d{2}[-_]\d{2}-\d{2}-\d{2}$', basename):
            new_basename = basename.replace('_', '-')
        elif re.match(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$', basename):
            new_basename = basename[20:]
        elif re.match(r'^\w{8}$', basename):
            new_basename = f'{date_str}_{basename.upper()}'
        elif re.match(r'^\w{8}-\w+$', basename):
            parts = basename.split('-')
            parts[0] = parts[0].upper()
            new_basename = f'{date_str}_' + '-'.join(parts)
        else:
            raise RuntimeError(f'Invalid {basename} for {self}')

        return f'{new_basename}.FIT'

    @cached_property
    def failures_count(self) -> int:
        return len([point for point in self.points if not point.is_ok])

    @cached_property
    def ok_count(self) -> int:
        return len([point for point in self.points if point.is_ok])

    @cached_property
    def is_valid(self):
        if self.ok_count < ErrorThreshold.MIN_COUNT:
            return False

        if (self.failures_count > ErrorThreshold.SHARE * self.ok_count):
            return False

        return True

    @property
    def status(self) -> str:
        msg = 'is ok' if self.is_valid else 'has many errors'
        if not self.correct_crc:
            msg += ' (with FitCRCError)'
        return msg

    def __str__(self):
        ok_count = len(self.points)
        msg = f'track {self.filename} {self.status}: {self.ok_count} points'
        if self.failures_count:
            msg += f' and {self.failures_count} failures'
        return msg


SYNC_LOCAL_DIR = os.path.join(library.files.Location.Dropbox, 'running')
DEFAULT_TRACKS_LOCATION = os.path.join(SYNC_LOCAL_DIR, 'tracks')
GARMIN_DEVICE_DIR = os.path.join(os.sep, 'Volumes', 'GARMIN', 'GARMIN', 'Activity')
