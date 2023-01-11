from tools.running.fitreader import read_fit_file
from tools.running.gpxwriter import save_gpx, to_gpx
from tools.running.segment import Segment
from tools import model
from tools.running.track import Track

import library

import datetime
import math
import os

import logging
log = logging.getLogger(__name__)

from typing import List

DEFAULT_SPEED_LIMIT = 2
DEFAULT_DISTANCE_LIMIT = 5

ACTIVE_YEARS = list(range(2013, 2024))


def speed_rating(segment: Segment, average_speed: float) -> float:
    rating = segment.speed / average_speed
    rating /= math.log(segment.duration + 2)
    return rating


def distance_rating(first: Segment, second: Segment) -> float:
    joined = Segment(start=first.start, finish=second.finish)
    if first.distance or second.distance:
        return (first.distance + second.distance - joined.distance) / (first.distance + second.distance)
    else:
        return 0


SHIFTS = [-3, -2, -1, 0, 1, 2, 3]


def clean(
    track: Track,
    speed_limit: int=None,
    distance_limit: int=None,
) -> Track:
    log.info(f'cleaning {track}')
    is_ok = []
    for index, point in enumerate(track.ok_points):
        point_segments = {}
        for shift in SHIFTS:
            start_index = index + shift
            finish_index = start_index + 1
            if 0 <= start_index and finish_index < len(track.ok_points):
                segment = Segment(track.ok_points[start_index], track.ok_points[finish_index])
                point_segments[shift] = segment

        if not point_segments:
            raise RuntimeError(f'No segments for {index}: {point}')

        point_is_ok = True
        segments_values = point_segments.values()
        max_speed_rating = max(speed_rating(segment, track.average_speed) for segment in segments_values)
        if speed_limit <= max_speed_rating:
            point_is_ok = False

        if point_segments.get(-1) and point_segments.get(0):
            if distance_limit <= distance_rating(point_segments[-1], point_segments[0]):
                point_is_ok = False

        log.debug(
            'point %03d: %s',
            index,
            '\t'.join([
                ' '.join(f'{segment.speed:.2f}' for segment in segments_values),
                ' '.join(f'{segment.duration}' for segment in segments_values),
                ' '.join(f'{segment.distance * 1000:.2f}' for segment in segments_values),
                ' '.join(f'{speed_rating(segment, track.average_speed):.2f}' for segment in segments_values),
                ' << deleting' if not point_is_ok else '',
            ]),
        )

        if index <= 10 and max_speed_rating >= 10:
            log.debug('Cut early start errors')
            for previous_index in range(index):
                is_ok[previous_index] = False

        is_ok.append(point_is_ok)

    new_track = Track(
        filename=track.filename,
        points=[point for point, point_is_ok in zip(track.ok_points, is_ok) if point_is_ok],
        correct_crc=track.correct_crc,
        activity_timezone=track.activity_timezone,
    )
    log.info(f'cleaned {new_track}')
    return new_track


def analyze_track(
    track: Track,
    speed_limit: int = DEFAULT_SPEED_LIMIT,
    distance_limit: int = DEFAULT_DISTANCE_LIMIT,
) -> Track:
    new_track = None
    old_track = track
    while (new_track is None) or (new_track.ok_count < old_track.ok_count):
        new_track = clean(old_track, speed_limit=speed_limit, distance_limit=distance_limit)
        old_track = new_track

    return new_track


def get_filenames(dirnames: List[str], flt):
    log.info(f'Checking {len(dirnames)} dirs:')

    files = []
    for dirname in dirnames:
        log.info(f'    {dirname}')
        for file in library.files.walk(dirname, extensions=['.FIT', '.fit']):
            files.append(file)

    for filename in sorted(files):
        if (not flt) or (flt in filename):
            yield filename


def get_dirnames(
    years: List[int],
    add_travel: bool,
):
    for year in years:
        yield os.path.join(model.SYNC_LOCAL_DIR, str(year))

    if add_travel:
        yield model.DEFAULT_TRACKS_LOCATION


def analyze(args):
    dirnames = list(get_dirnames(ACTIVE_YEARS, args.add_travel))
    filenames = list(get_filenames(dirnames, args.filter))

    log.info(f'Analyzing {len(filenames)} files')
    for filename in filenames:
        log.info(f'Analyzing {filename}')
        track = read_fit_file(filename, raise_on_error=False)
        if not track.is_valid:
            log.error(f'Skipping {track}')
            continue

        log.info(track)

        clean_track = analyze_track(track)
        log.info(clean_track.explain)

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
        #         if points:
        #             save_gpx(to_gpx(points), filename)
        #         else:
        #             log.info(f'No points to save: {filename}')


def populate_parser(parser):
    parser.add_argument('--filter', help='Find files containg this substring')
    parser.add_argument('--write', help='Write patched files', action='store_true')
    parser.add_argument('--add-travel', help='Add travel files', action='store_true')
    parser.set_defaults(func=analyze)
