from typing import List, Optional
import attr
import datetime
import os
from functools import cached_property
import re

import logging
log = logging.getLogger(__name__)

from tools.running import trackpoint
from tools.running import segment


SEGMENT_DURATION_THRESHOLD = 10000


class ErrorThreshold:
    MIN_COUNT = 2
    SHARE = 0.7


VIEW_MARGIN = 0.01


def points_to_segments(points: List[trackpoint.TrackPoint]) -> List[segment.Segment]:
    return [
        segment.Segment(points[index], points[index + 1])
        for index in range(len(points) - 1)
    ]


def speed_to_pace(speed: float) -> str:
    pace = 1000. / speed
    minutes = int((pace + 0.5) / 60)
    seconds = int((pace + 0.5) - minutes * 60)
    return '%d:%02d' % (minutes, seconds)


@attr.s
class Track:
    filename: str = attr.ib()
    points: List[trackpoint.TrackPoint] = attr.ib()
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
    def start_point(self) -> trackpoint.TrackPoint:
        return self.ok_points[0]

    @property
    def finish_point(self) -> trackpoint.TrackPoint:
        return self.ok_points[-1]

    @property
    def start_ts(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.start_timestamp)

    @cached_property
    def ok_points(self) -> List[trackpoint.TrackPoint]:
        return [point for point in self.points if point.is_ok]

    @cached_property
    def max_lat(self) -> float:
        result = max(point.latitude for point in self.ok_points)
        if result is None:
            raise RuntimeError('No max_lat')
        return result

    @cached_property
    def max_long(self) -> float:
        result = max(point.longitude for point in self.ok_points)
        if result is None:
            raise RuntimeError('No max_long')
        return result

    @cached_property
    def min_lat(self) -> float:
        result = min(point.latitude for point in self.ok_points)
        if result is None:
            raise RuntimeError('No min_lat')
        return result

    @cached_property
    def min_long(self) -> float:
        result = min(point.longitude for point in self.ok_points)
        if result is None:
            raise RuntimeError('No min_long')
        return result

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
        return len(self.points) - self.ok_count

    @cached_property
    def ok_count(self) -> int:
        return len(self.ok_points)

    @cached_property
    def is_valid(self):
        log.debug(f'ok: {self.ok_count}, failures: {self.failures_count}')
        if self.ok_count < ErrorThreshold.MIN_COUNT:
            return False

        # if (self.failures_count > ErrorThreshold.SHARE * self.ok_count):
        #     return False

        return True

    @property
    def status(self) -> str:
        msg = 'is ok' if self.is_valid else 'has many errors'
        if not self.correct_crc:
            msg += ' (with FitCRCError)'
        return msg

    def __str__(self):
        ok_count = len(self.points)
        basename = os.path.basename(self.filename)
        msg = f'track {basename} {self.status}: {self.ok_count} points'
        if self.failures_count:
            msg += f' and {self.failures_count} failures'
        return msg

    @cached_property
    def segments(self) -> List[segment.Segment]:
        segments = points_to_segments(self.ok_points)
        for segment in segments:
            if segment.duration >= SEGMENT_DURATION_THRESHOLD:
                log.warning(f'Strange duration: {segment.duration}')
        return segments

    @cached_property
    def total_distance(self):
        return sum(
            segment.distance
            for segment in self.segments
            if segment.duration < SEGMENT_DURATION_THRESHOLD
        )

    @cached_property
    def total_duration(self) -> int:
        return sum(
            segment.duration
            for segment in self.segments
            if segment.duration < SEGMENT_DURATION_THRESHOLD
        )

    @cached_property
    def average_speed(self):
        if self.total_duration > 0:
            return 1000 * self.total_distance / self.total_duration
        else:
            return 0

    @property
    def track_type(self) -> str:
        if self.total_distance >= 3 and 10 >= self.average_speed >= 4:
            return 'cycling'
        elif self.average_speed <= 4:
            return 'running'
        else:
            return 'other'

    @property
    def explain(self) -> str:
        if self.activity_timezone is not None:
            start_str = datetime.datetime.fromtimestamp(self.start_point.timestamp, self.activity_timezone).strftime('%Y-%m-%d %H:%M')
            finish_str = datetime.datetime.fromtimestamp(self.finish_point.timestamp, self.activity_timezone).strftime('%H:%M')
        else:
            start_str = datetime.datetime.utcfromtimestamp(self.start_point.timestamp).strftime('%Y-%m-%d %H:%M')
            finish_str = datetime.datetime.utcfromtimestamp(self.finish_point.timestamp).strftime('%H:%M')
        return ' '.join([
            f'Track: {self.filename}: {start_str}-{finish_str}',
            f'\t{self.total_distance:.3f} km',
            f'at {speed_to_pace(self.average_speed)}',
            f'({self.average_speed:.2f} m/sec)',
            self.track_type,
            f', patches count: {self.failures_count}' if self.failures_count else '',
        ]).replace(' ,', ',')
