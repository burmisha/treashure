from typing import List, Optional
import attr
import datetime
import library
import os

@attr.s
class GeoPoint:
    longitude: float = attr.ib(default=None)
    latitude: float = attr.ib(default=None)
    altitude: Optional[float] = attr.ib(default=None)
    timestamp: Optional[float] = attr.ib(default=None)
    cadence: Optional[float] = attr.ib(default=None)
    heart_rate: Optional[float] = attr.ib(default=None)

    @property
    def datetime(self):
        return datetime.datetime.fromtimestamp(self.timestamp)

    @property
    def yandex_maps_link(self):
        text = f'{self.latitude}%2C{self.longitude}'
        ll = f'{self.longitude}%2C{self.latitude}'
        return f'https://yandex.ru/maps/?ll={ll}&mode=search&sll={ll}&text={text}&z=15'


class ErrorThreshold:
    MIN_COUNT = 200
    SHARE = 0.9


@attr.s
class Track:
    filename: str = attr.ib()
    points: List[GeoPoint] = attr.ib()
    failures: List[int] = attr.ib()
    correct_crc: Optional[bool] = attr.ib(default=None)

    @property
    def start_timestamp(self):
        return self.points[0].timestamp if self.points else 0

    @property
    def is_valid(self):
        points_count = len(self.points)
        failures_count = len(self.failures)

        if points_count < ErrorThreshold.MIN_COUNT:
            return False

        if (failures_count > ErrorThreshold.SHARE * points_count):
            return False

        return True

    @property
    def description(self):
        return os.path.basename(self.filename)

    @property
    def status(self) -> str:
        msg = 'is ok' if self.is_valid else 'has many errors' 
        if not self.correct_crc:
            msg += ' (with FitCRCError)'
        return msg

    def __str__(self):
        if self.failures:
            msg = (
                f'track {self.filename} {self.status}: {len(self.points)} points and {len(self.failures)} failures, '
                f'{self.failures[:3]} (3 first ones)'
            )
            return msg
        else:
            return f'track {self.filename} {self.status}: {len(self.points)} points'


SYNC_LOCAL_DIR = os.path.join(library.files.Location.Dropbox, 'running')
DEFAULT_TRACKS_LOCATION = os.path.join(SYNC_LOCAL_DIR, 'tracks')
GARMIN_DEVICE_DIR = os.path.join(os.sep, 'Volumes', 'GARMIN', 'GARMIN', 'Activity')
