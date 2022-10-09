import datetime
from tools import fitreader
from tools.gpxwriter import GpxWriter
from tools import model
import math
import os

import geopy
import geopy.distance

import library

import logging
log = logging.getLogger(__name__)


def tsToHr(timestamp, fmt='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime(fmt)


def valueToStr(value, threshold=None):
    return u'\u2591' * min(int(value), threshold) + u'\u2592' * max(max(int(value), threshold) - threshold, 0)


def speed_to_pace(speed):
    pace = 1000. / speed
    minutes = int((pace + 0.5) / 60)
    seconds = int((pace + 0.5) - minutes * 60)
    return '%d:%02d' % (minutes, seconds)


class Segment(object):
    def __init__(self, first, second):
        self.First = first
        self.Second = second
        self.Distance = geopy.distance.distance(
            (self.First.latitude, self.First.longitude),
            (self.Second.latitude, self.Second.longitude),
        ).km
        self.StartTimestamp = self.First.timestamp
        self.FinishTimestamp = self.Second.timestamp
        self.Duration = self.FinishTimestamp - self.StartTimestamp
        if self.Duration > 0:
            self.Speed = 1000 * self.Distance / self.Duration  # meters per second
        else:
            log.debug('Zero duration: %s at %s', 1000 * self.Distance, self.StartTimestamp)
            self.Speed = 0

    def __add__(self, that):
        assert self.Second.latitude == that.First.latitude
        assert self.Second.longitude == that.First.longitude
        assert self.FinishTimestamp == that.StartTimestamp
        return Segment(self.First, that.Second)

    def WarningRating(self, averageSpeed):
        rating = self.Speed / averageSpeed
        if self.Duration == 1:
            rating /= math.log(self.Duration + 1)
        return rating


class Track(object):
    def __init__(self, points, description=None, source_file=None):
        self.__Points = list(points)
        self.__Description = description or ''
        self.__SourceFile = source_file
        self.__OriginalDistance = None
        self.__Patched = []
        self.__Init()

    def __Init(self):
        self.__TotalDistance = 0
        self.__TotalTime = 0
        try:
            self.__StartTimestamp = self.__Points[0].timestamp
            self.__FinishTimestamp = self.__Points[-1].timestamp
        except:
            log.error('Failed on %s', self.__SourceFile)
            raise
        self.__Segments = []

    def __BuildSegments(self):
        if not self.__Segments:
            for index in range(len(self.__Points) - 1):
                segment = Segment(self.__Points[index], self.__Points[index + 1])
                self.__Segments.append(segment)

    def __CalcStats(self):
        self.__BuildSegments()
        for segment in self.__Segments:
            if segment.Duration < 120:
                self.__TotalDistance += segment.Distance
                self.__TotalTime += segment.Duration
        self.__AverageSpeed = 1000 * self.__TotalDistance / self.__TotalTime

    def TotalDistance(self):
        if self.__TotalDistance:
            return self.__TotalDistance

        self.__CalcStats()
        return self.__TotalDistance

    def Clean(self):
        cleaned = True
        while cleaned:
            self.__BuildSegments()
            self.__CalcStats()
            cleaned = self.__Clean()

    def __Clean(self):
        assert len(self.__Segments) == len(self.__Points) - 1
        if self.__OriginalDistance is None:
            self.__OriginalDistance = self.TotalDistance()

        point_warnings = [False for _ in self.__Points]
        log.debug('point ### \tprev_sp\tnext_sp\tp_durtn\tn_durtn\tp_dist\tn_dist\trating')
        for index, point in enumerate(self.__Points):
            has_warning = False
            prev_segment = self.__Segments[index - 1] if index >= 1 else None
            next_segment = self.__Segments[index] if index < len(self.__Segments) else None

            if not prev_segment and next_segment.WarningRating(self.__AverageSpeed) >= 2:
                has_warning = True
            if not next_segment and prev_segment.WarningRating(self.__AverageSpeed) >= 2:
                has_warning = True
            if prev_segment and next_segment:
                joined_segment = prev_segment + next_segment
                if prev_segment.Distance > 0 or next_segment.Distance > 0:
                    rating = (prev_segment.Distance + next_segment.Distance - joined_segment.Distance) / (prev_segment.Distance + next_segment.Distance)
                else:
                    rating = 0

                if (
                    rating >= 5
                    or (
                        prev_segment.WarningRating(self.__AverageSpeed) >= 3
                        or next_segment.WarningRating(self.__AverageSpeed) >= 3
                    )
                ):
                    has_warning = True

                log.debug(
                    'point %03d:\t%.2f\t%.2f\t%d\t%d\t%.2f\t%.2f\t%.3f\t%.3f\t%.3f\t%s%s',
                    index,
                    prev_segment.Speed,
                    next_segment.Speed,
                    prev_segment.Duration,
                    next_segment.Duration,
                    prev_segment.Distance * 1000,
                    next_segment.Distance * 1000,
                    prev_segment.WarningRating(self.__AverageSpeed),
                    next_segment.WarningRating(self.__AverageSpeed),
                    rating,
                    valueToStr(rating * 50, 5),
                    ' << deleting' if has_warning else '',
                )

            if index <= 10 and next_segment and next_segment.WarningRating(self.__AverageSpeed) >= 10:
                log.debug('Cut early start errors')
                for i in range(index):
                    point_warnings[i] = True

            point_warnings[index] = has_warning

        if not any(point_warnings):
            return False
        else:
            log.debug('Deleting %d points', sum(point_warnings))
            self.__Patched.append(sum(point_warnings))

        self.__Points = [point for point, warning in zip(self.__Points, point_warnings) if not warning]
        self.__Init()
        return True

    def __str__(self):
        if self.TotalDistance() >= 3 and 10 >= self.__AverageSpeed >= 4:
            track_type = 'cycling'
        elif self.__AverageSpeed <= 4:
            track_type = 'running'
        else:
            track_type = 'other'
        return u'Track %s: %s-%s\t%.3f km at %s (%.2f m/sec) %s%s%s' % (
            self.__Description,
            tsToHr(self.__StartTimestamp, fmt='%Y-%m-%d %H:%M'),
            tsToHr(self.__FinishTimestamp, fmt='%H:%M'),
            self.TotalDistance(),
            speed_to_pace(self.__AverageSpeed),
            self.__AverageSpeed,
            track_type,
            u', patches size: %r' % self.__Patched if self.__Patched else '',
            u', original distance: %.3f km' % self.__OriginalDistance if self.__Patched else '',
        )

    def IsPatched(self):
        return self.__Patched

    def SourceFilename(self):
        return self.__SourceFile

    def StartTimestamp(self):
        return self.__StartTimestamp

    def Points(self):
        return self.__Points



def analyze_track(fit_track):
    track = Track(
        fit_track.points,
        description=fit_track.description,
        source_file=fit_track.filename,
    )
    original_points = fit_track.points

    track.Clean()

    patched_points = list(track.Points())

    return track, original_points, patched_points


def analyze(args):
    files = []
    dirnames = []
    for year in range(2013, 2022):
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

    fitTracks = []
    for file in files:
        track = fitreader.read_fit_file(file, raise_on_error=False)
        if track.is_valid:
            fitTracks.append(track)
            log.info(f'Got {track}, {track.points[0].yandex_maps_link}')
        else:
            log.error(f'Skipping {track}')

    fitTracks.sort(key=lambda i: i.start_timestamp)
    for fitTrack in fitTracks:
        track, original_points, patched_points = analyze_track(fitTrack)
        log.debug(f'Track is patched: {track.IsPatched()}')
        if args.write and track.IsPatched():
            log.info('Compare tracks at https://www.mygpsfiles.com/app/')
            for points, suffix in [
                (original_points, 'original'),
                (patched_points, 'patched'),
            ]:
                parts = track.SourceFilename().split('.')
                parts[-2] = parts[-2] + '_' + suffix
                parts[-1] = 'gpx'
                gpx_writer = GpxWriter('.'.join(parts))
                gpx_writer.AddPoints(points)
                if gpx_writer.HasPoints():
                    gpx_writer.Save()


def populate_parser(parser):
    parser.add_argument('--filter', help='Find files containg this substring')
    parser.add_argument('--write', help='Write patched files', action='store_true')
    parser.add_argument('--add-travel', help='Add travel files', action='store_true')
    parser.set_defaults(func=analyze)
