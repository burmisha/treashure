from tools.running.fitreader import read_fit_file
from tools.running.gpxwriter import save_gpx, to_gpx
from tools.running.segment import Segment
from tools.running import dirname
from tools.running.track import Track

import library.files

import datetime
import math
import os
import attr

import logging
log = logging.getLogger(__name__)

from typing import List, Tuple


@attr.s
class Limits:
    triangle: float = attr.ib()
    speed: int = attr.ib()
    distance: int = attr.ib()


DefaultLimits = Limits(speed=20, distance=0.1, triangle=0.9)
MinLimits = Limits(speed=1, distance=0., triangle=0.)
MaxLimits = Limits(speed=20, distance=1., triangle=1.)
Steps = Limits(speed=1, distance=0.05, triangle=0.02)


ACTIVE_YEARS = list(range(2013, datetime.datetime.now().year + 1))


def clean(
    track: Track,
    limits: Limits,
) -> Tuple[Track, list]:
    is_ok = []
    points = track.ok_points

    assert len(points) >= 3

    previous_ok_point = None
    for index, point in enumerate(points):
        point_is_ok = True
        next_point = points[index + 1] if index + 1 < len(points) else None

        prev_segment = Segment(previous_ok_point, point) if (previous_ok_point and point) else None
        next_segment = Segment(point, next_point) if (point and next_point) else None
        joined_segment = Segment(previous_ok_point, next_point) if (previous_ok_point and next_point) else None

        if prev_segment and next_segment and joined_segment:
            triangle_rating = 1 - (joined_segment.distance / (prev_segment.distance + next_segment.distance))
        else:
            triangle_rating = None

        reason = None
        if prev_segment and (prev_segment.speed >= limits.speed):
            reason = f'speed: {prev_segment.speed} >= {limits.speed}'
        elif triangle_rating and (triangle_rating >= limits.triangle):
            reason = f'triangle: {triangle_rating} >= {limits.triangle}'
        elif prev_segment and next_segment and (prev_segment.distance >= limits.distance) and (next_segment.distance >= limits.distance):
            reason = f'two distances: {prev_segment.distance}, {next_segment.distance} >= {limits.distance}'

        if reason:
            log.info(f'{index}@{point.timestamp} is broken by {reason}')
            point_is_ok = False
        else:
            previous_ok_point = point

        is_ok.append(point_is_ok)


    ok_points = [point for point, point_is_ok in zip(points, is_ok) if point_is_ok]
    broken_points = [point for point, point_is_ok in zip(points, is_ok) if not point_is_ok]

    new_track = Track(
        filename=track.filename,
        points=ok_points,
        correct_crc=track.correct_crc,
        activity_timezone=track.activity_timezone,
    )
    return new_track, broken_points


def analyze_track(
    track: Track,
    limits: Limits,
) -> Tuple[Track, list]:
    all_broken_points = []
    while True:
        log.info(f'Clean {track} with {limits}')
        track, broken_points = clean(track, limits)
        all_broken_points += broken_points
        if not broken_points:
            return track, all_broken_points


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
        yield os.path.join(dirname.SYNC_LOCAL_DIR, str(year))

    if add_travel:
        yield dirname.TRACKS_DIR


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

        clean_track, _ = analyze_track(track, DefaultLimits)
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
