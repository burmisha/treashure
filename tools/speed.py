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


def valueToStr(value, threshold=None) -> str:
    return '\u2591' * min(int(value), threshold) + '\u2592' * max(max(int(value), threshold) - threshold, 0)


def speed_to_pace(speed: float) -> str:
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
    track: model.Track = attr.ib()
    is_ok: List[bool] = attr.ib()

    @cached_property
    def clean_points(self) -> List[model.GeoPoint]:
        return [
            point
            for point, point_is_ok in zip(self.track.points, self.is_ok)
            if point_is_ok
        ]

    @cached_property
    def segments(self) -> List[Segment]:
        clean_points = self.clean_points
        segments = []
        for index in range(len(clean_points) - 1):
            segment = Segment(clean_points[index], clean_points[index + 1])
            if segment.duration >= SEGMENT_DURATION_THRESHOLD:
                log.warning(f'Strange duration: {segment.duration}')
            segments.append(segment)
        return segments

    @cached_property
    def original_distance(self) -> float:
        points = self.track.points
        segments = [
            Segment(points[index], points[index + 1])
            for index in range(len(points) - 1)
        ]
        return sum(segment.distance for segment in segments)

    @cached_property
    def patches_count(self) -> int:
        return len([1 for point_is_ok in self.is_ok if not point_is_ok])

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
        if self.total_duration > 0:
            return 1000 * self.total_distance / self.total_duration
        else:
            return 0

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
        start_str = datetime.datetime.fromtimestamp(self.track.start_point.timestamp, self.track.activity_timezone).strftime('%Y-%m-%d %H:%M')
        finish_str = datetime.datetime.fromtimestamp(self.track.finish_point.timestamp, self.track.activity_timezone).strftime('%H:%M')
        return 'Clean track: %s-%s\t%.3f km at %s (%.2f m/sec) %s%s%s' % (
            start_str,
            finish_str,
            self.total_distance,
            speed_to_pace(self.average_speed),
            self.average_speed,
            self.track_type,
            f', patches count: {self.patches_count}' if self.patches_count else '',
            f', original distance: {self.original_distance:.3f} km' if self.patches_count else '',
        )


def clean(
    clean_track: CleanTrack,
    one_side_speed=2,
    both_side_speed=3,
    distance_limit=5,
) -> CleanTrack:
    is_ok = []
    log.debug('\t'.join([
        'point ### ',
        'prev_sp',
        'next_sp',
        'p_durtn',
        'n_durtn',
        'p_dist',
        'n_dist',
        'pr_sp_r',
        'n_sp_r',
        'rating',
    ]))
    for index, point in enumerate(clean_track.track.points):
        prev_segment = clean_track.segments[index - 1] if index >= 1 else None
        next_segment = clean_track.segments[index] if index < len(clean_track.segments) else None
        prev_speed_rating = speed_rating(prev_segment, clean_track.average_speed) if prev_segment else 0
        next_speed_rating = speed_rating(next_segment, clean_track.average_speed) if next_segment else 0

        point_is_ok = True
        if not prev_segment:
            if next_speed_rating >= one_side_speed:
                point_is_ok = False
        elif not next_segment:
            if prev_speed_rating >= one_side_speed:
                point_is_ok = False
        else:
            rating = distance_rating(prev_segment, next_segment)
            if rating >= distance_limit or prev_speed_rating >= both_side_speed or next_speed_rating >= both_side_speed:
                point_is_ok = False

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
                ' << deleting' if not point_is_ok else '',
            )

        if index <= 10 and next_speed_rating >= 10:
            log.debug('Cut early start errors')
            for i in range(index):
                is_ok[i] = False

        is_ok.append(point_is_ok)

    return CleanTrack(track=clean_track.track, is_ok=is_ok)


def analyze_track(track: model.Track) -> CleanTrack:
    log.debug('Cleaning track')
    old_track = CleanTrack(
        track=track,
        is_ok=[True for _ in track.points]
    )
    new_track = None
    while (new_track is None) or (new_track.patches_count > old_track.patches_count):
        new_track = clean(old_track)
        old_track = new_track

    return new_track


def get_filenames(dirnames: List[str], flt):
    log.info(f'Checking {dirnames}')
    files = [
        file
        for d in dirnames
        for file in library.files.walk(d, extensions=['.FIT', '.fit'])
    ]
    files.sort()
    if flt:
        for filename in files:
            if flt in filename:
                yield filename
    else:
        for filename in files:
            yield filename


def get_dirnames(add_travel: bool) -> List[str]:
    dirnames = []
    for year in range(2013, 2023):
        dirname = os.path.join(model.SYNC_LOCAL_DIR, str(year))
        dirnames.append(dirname)

    if add_travel:
        dirnames.append(model.DEFAULT_TRACKS_LOCATION)

    return dirnames


def analyze(args):
    dirnames = get_dirnames(args.add_travel)
    filenames = get_filenames(dirnames, args.filter)
    tracks = [
        fitreader.read_fit_file(filename, raise_on_error=False)
        for filename in filenames
    ]
    tracks.sort(key=lambda track: track.start_timestamp)

    for track in tracks:
        if not track.is_valid:
            log.error(f'Skipping {track}')
            continue
        log.info(track)
        clean_track = analyze_track(track)
        log.info(clean_track)
        # if args.write and (clean_track.patches_count > 0):
        #     log.info('Compare tracks at https://www.mygpsfiles.com/app/')
        #     for points, suffix in [
        #         (original_track.points, 'original'),
        #         (clean_track.points, 'patched'),
        #     ]:
        #         parts = original_track.source_file.split('.')
        #         parts[-2] = parts[-2] + '_' + suffix
        #         parts[-1] = 'gpx'
        #         filename = '.'.join(parts)
        #         gpx_writer = GpxWriter(filename)
        #         gpx_writer.AddPoints(points)
        #         if gpx_writer.HasPoints():
        #             gpx_writer.Save()
        #         else:
        #             log.info(f'No points to save: {filename}')



def populate_parser(parser):
    parser.add_argument('--filter', help='Find files containg this substring')
    parser.add_argument('--write', help='Write patched files', action='store_true')
    parser.add_argument('--add-travel', help='Add travel files', action='store_true')
    parser.set_defaults(func=analyze)
