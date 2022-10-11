import datetime
from tools import fitreader
from tools.gpxwriter import GpxWriter
from tools import model
from functools import cached_property
import math
import os

import attr
import geopy
import geopy.distance

import library

import logging
log = logging.getLogger(__name__)

from typing import List

def tsToHr(timestamp, fmt='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime(fmt)


def valueToStr(value, threshold=None):
    return '\u2591' * min(int(value), threshold) + '\u2592' * max(max(int(value), threshold) - threshold, 0)


def speed_to_pace(speed: float):
    pace = 1000. / speed
    minutes = int((pace + 0.5) / 60)
    seconds = int((pace + 0.5) - minutes * 60)
    return '%d:%02d' % (minutes, seconds)


@attr.s
class Segment(object):
    start: model.GeoPoint = attr.ib()
    finish: model.GeoPoint = attr.ib()

    @cached_property
    def distance(self) -> float:
        return geopy.distance.distance(
            (self.start.latitude, self.start.longitude),
            (self.finish.latitude, self.finish.longitude),
        ).km

    @cached_property
    def duration(self) -> float:
        return self.finish.timestamp - self.start.timestamp

    @cached_property
    def speed(self) -> float:
        if self.duration > 0:
            return 1000 * self.distance / self.duration  # meters per second
        return 0


def speed_rating(segment: Segment, average_speed: float) -> float:
    rating = segment.speed / average_speed
    rating /= math.log(segment.duration + 1)
    return rating


def distance_rating(first: Segment, second: Segment) -> float:
    joined = Segment(start=first.start, finish=second.finish)
    if first.distance or second.distance:
        return (first.distance + second.distance - joined.distance) / (first.distance + second.distance)
    else:
        return 0


SEGMENT_DURATION_THRESHOLD = 120


@attr.s
class CleanTrack(object):
    points: List[model.GeoPoint] = attr.ib()
    description: str = attr.ib()
    source_file: str = attr.ib()

    original_distance: float = attr.field(default=0)
    patches_count: int = attr.ib(default=0)

    @cached_property
    def segments(self):
        segments = []
        for index in range(len(self.points) - 1):
            segment = Segment(self.points[index], self.points[index + 1])
            if segment.duration >= SEGMENT_DURATION_THRESHOLD:
                log.warning(f'Strange duration: {segment.duration}')
            segments.append(segment)
        return segments

    @cached_property
    def total_distance(self):
        return sum(
            segment.distance
            for segment in self.segments 
            if segment.duration < SEGMENT_DURATION_THRESHOLD
        )

    @cached_property
    def total_duration(self):
        return sum(
            segment.duration
            for segment in self.segments 
            if segment.duration < SEGMENT_DURATION_THRESHOLD
        )

    @cached_property
    def average_speed(self):
        return 1000 * self.total_distance / self.total_duration

    @property
    def start_timestamp(self):
        return self.points[0].timestamp

    @property
    def track_type(self) -> str:
        if self.total_distance >= 3 and 10 >= self.average_speed >= 4:
            return 'cycling'
        elif self.average_speed <= 4:
            return 'running'
        else:
            return 'other'

    def __str__(self):
        return 'Track %s: %s-%s\t%.3f km at %s (%.2f m/sec) %s%s%s' % (
            self.description,
            tsToHr(self.points[0].timestamp, fmt='%Y-%m-%d %H:%M'),
            tsToHr(self.points[-1].timestamp, fmt='%H:%M'),
            self.TotalDistance(),
            speed_to_pace(self.average_speed),
            self.average_speed,
            self.track_type,
            f', patches count: {self.patches_count}'if self.patches_count else '',
            f', original distance: {self.original_distance:.3f} km' if self.patches_count else '',
        )



def get_clean_track(track: CleanTrack) -> CleanTrack:
    track_copy = track
    new_track = None
    while not new_track or new_track.patches_count:
        new_track = clean(track_copy)
        track_copy = new_track

    return new_track


def clean(
    track: CleanTrack,
    one_side_speed=2,
    both_side_speed=3,
    distance_limit=5,
):
    point_warnings = []
    log.debug('point ### \tprev_sp\tnext_sp\tp_durtn\tn_durtn\tp_dist\tn_dist\trating')
    for index, point in enumerate(track.points):
        prev_segment = track.segments[index - 1] if index >= 1 else None
        next_segment = track.segments[index] if index < len(track.segments) else None
        prev_speed_rating = speed_rating(prev_segment, track.average_speed) if prev_segment else 0
        next_speed_rating = speed_rating(next_segment, track.average_speed) if next_segment else 0

        has_warning = False
        if not prev_segment:
            if next_speed_rating >= one_side_speed:
                has_warning = True
        elif not next_segment:
            if prev_speed_rating >= one_side_speed:
                has_warning = True
        else:
            rating = distance_rating(prev_segment, next_segment)
            if rating >= distance_limit or prev_speed_rating >= both_side_speed or next_speed_rating >= both_side_speed:
                has_warning = True

            log.debug(
                'point %03d:\t%.2f\t%.2f\t%d\t%d\t%.2f\t%.2f\t%.3f\t%.3f\t%.3f\t%s%s',
                index,
                prev_segment.speed,
                next_segment.speed,
                prev_segment.duration,
                next_segment.duration,
                prev_segment.distance * 1000,
                next_segment.distance * 1000,
                prev_speed_rating,
                next_speed_rating,
                rating,
                valueToStr(rating * 50, 5),
                ' << deleting' if has_warning else '',
            )

        if index <= 10 and next_speed_rating >= 10:
            log.debug('Cut early start errors')
            for i in range(index):
                point_warnings[i] = True

        point_warnings.append(has_warning)

    points = [
        point
        for point, warning in zip(track.points, point_warnings)
        if not warning
    ]
    return CleanTrack(
        points=points,
        description=track.description,
        source_file=track.source_file,
        original_distance=track.original_distance,
        patches_count=track.patches_count + len(track.points) - len(points),
    )


def analyze_track(fit_track: model.Track):
    original_track = CleanTrack(
        fit_track.points,
        description=fit_track.description,
        source_file=fit_track.filename,
    )
    clean_track = get_clean_track(original_track)

    return original_track, clean_track


def analyze(args):
    files = []
    dirnames = []
    for year in range(2013, 2023):
        dirname = os.path.join(model.SYNC_LOCAL_DIR, str(year))
        dirnames.append(dirname)

    if args.add_travel:
        dirnames.append(model.DEFAULT_TRACKS_LOCATION)

    log.info(f'Checking {dirnames}')
    files = [
        file
        for d in dirnames
        for file in library.files.walk(d, extensions=['.FIT', '.fit'])
    ]
    if args.filter:
        files = [f for f in files if args.filter in f]
        log.info(f'Got {len(files)} files matching filter {args.filter}')

    fit_tracks = []
    for file in files:
        track = fitreader.read_fit_file(file, raise_on_error=False)
        if track.is_valid:
            fit_tracks.append(track)
            log.info(f'Got {track}, {track.points[0].yandex_maps_link}')
        else:
            log.error(f'Skipping {track}')

    fit_tracks.sort(key=lambda track: track.start_timestamp)
    for fitTrack in fit_tracks:
        original_track, clean_track = analyze_track(fitTrack)
        if args.write and (clean_track.patches_count > 0):
            log.info('Compare tracks at https://www.mygpsfiles.com/app/')
            for points, suffix in [
                (original_track.points, 'original'),
                (clean_track.points, 'patched'),
            ]:
                parts = original_track.source_file.split('.')
                parts[-2] = parts[-2] + '_' + suffix
                parts[-1] = 'gpx'
                filename = '.'.join(parts)
                gpx_writer = GpxWriter(filename)
                gpx_writer.AddPoints(points)
                if gpx_writer.HasPoints():
                    gpx_writer.Save()
                else:
                    log.info(f'No points to save: {filename}')



def populate_parser(parser):
    parser.add_argument('--filter', help='Find files containg this substring')
    parser.add_argument('--write', help='Write patched files', action='store_true')
    parser.add_argument('--add-travel', help='Add travel files', action='store_true')
    parser.set_defaults(func=analyze)
