# -*- coding: utf-8 -*-

import datetime
import gpxparser
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
            (self.First.Latitude, self.First.Longitude),
            (self.Second.Latitude, self.Second.Longitude),
        ).km
        self.StartTimestamp = self.First.Timestamp
        self.FinishTimestamp = self.Second.Timestamp
        self.Duration = self.FinishTimestamp - self.StartTimestamp
        self.Speed = 1000 * self.Distance / self.Duration  # meters per second
        assert self.Duration > 0

    def __add__(self, that):
        assert self.Second.Latitude == that.First.Latitude
        assert self.Second.Longitude == that.First.Longitude
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
        self.__StartTimestamp = self.__Points[0].Timestamp
        self.__FinishTimestamp = self.__Points[-1].Timestamp
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
                rating = (prev_segment.Distance + next_segment.Distance - joined_segment.Distance) / (prev_segment.Distance + next_segment.Distance)

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
        if self.TotalDistance() >= 3 and self.__AverageSpeed >= 4:
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
            ', patched %r' % self.__Patched if self.__Patched else '',
            ' original was %.3f km' % self.__OriginalDistance if self.__Patched else '',
        )

    def IsPatched(self):
        return self.__Patched

    def SourceFilename(self):
        return self.__SourceFile

    def StartTimestamp(self):
        return self.__StartTimestamp

    def Points(self):
        return self.__Points


def analyze(args):
    files = []
    for year in range(2013, 2021):
        dirname = os.path.join(library.files.Location.Dropbox, 'running', str(year))
        for file in library.files.walk(dirname, extensions=['FIT']):
            files.append(file)

    if args.filter:
        files = [f for f in files if args.filter in f]
        log.info('Got %d files matching filter %s', len(files), args.filter)

    fitTracks = []
    for file in files:
        fitParser = gpxparser.FitParser(file)
        if fitParser.IsValid:
            fitTracks.append(fitParser)

    fitTracks.sort(key=lambda i: i.FirstTimestamp)
    for fitTrack in fitTracks:
        track = Track(
            fitTrack.Load(raise_on_error=False),
            description=fitTrack.Description(),
            source_file=fitTrack.Filename(),
        )

        original_points = list(track.Points())

        track.Clean()
        log.info(u'%s', track)

        patched_points = list(track.Points())

        if args.write and track.IsPatched():
            log.debug('Compare tracks at https://www.mygpsfiles.com/app/')
            for points, suffix in [
                (original_points, 'original'),
                (patched_points, 'patched'),
            ]:
                filename = track.SourceFilename().replace(
                    os.path.basename(track.SourceFilename()),
                    '%s_%s_%s.gpx' % (
                        tsToHr(track.StartTimestamp(), fmt='%Y-%m-%d_%H-%M-%S'),
                        os.path.basename(track.SourceFilename()).split('.')[0],
                        suffix,
                    )
                )
                gpxWriter = gpxparser.GpxWriter()
                gpxWriter.AddPoints(points)
                if gpxWriter.HasPoints():
                    gpxWriter.Save(filename)


def populate_parser(parser):
    parser.add_argument('--filter', help='Find files containg this substring')
    parser.add_argument('--write', help='Write patched files', action='store_true')
    parser.set_defaults(func=analyze)
