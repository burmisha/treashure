# -*- coding: utf-8 -*-

import math
import os
import gpxparser
import datetime

import geopy
import geopy.distance

import library

import logging
log = logging.getLogger(__name__)

def tsToHr(timestamp, fmt='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime(fmt)


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


class Track(object):
    def __init__(self, points, description=None, source_file=None):
        self.__Points = list(points)
        self.__Description = description or ''
        self.__SourceFile = source_file
        self.__Patched = False
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
                # print segment.Duration
        # print self.__TotalDistance, self.__TotalTime
        self.__AverageSpeed = 1000 * self.__TotalDistance / self.__TotalTime

    def TotalDistance(self):
        if self.__TotalDistance:
            return self.__TotalDistance

        self.__CalcStats()
        return self.__TotalDistance

    def Clean(self):
        self.__BuildSegments()
        self.__CalcStats()
        cleaned = True
        while cleaned:
            speed_warnings = []
            for index, segment in enumerate(self.__Segments):
                rating = segment.Speed / self.__AverageSpeed
                if segment.Duration == 1:
                    rating /= math.log(segment.Duration + 1)
                speed_warnings.append(rating)
                log.debug(
                    u'Speeds: %03d speed/avg: %.2f on %s: %s',
                    index,
                    rating,
                    tsToHr(segment.FinishTimestamp),
                    u'\u2591' * min(int(5 * rating), 15) + u'\u2592' * max(max(int(5 * rating), 15) - 15, 0),
                )
                

            strange_count = sum(1 for w in speed_warnings if w >= 3)
            if strange_count:
                log.debug('%s: %d out of %d segments look strange', self.__Description, strange_count, len(speed_warnings))
                cleaned = self.__Clean(speed_warnings)
            else:
                cleaned = False


    def __Clean(self, segment_warnings):
        assert len(segment_warnings) == len(self.__Segments) == len(self.__Points) - 1
        if all(w <= 5 for w in segment_warnings):
            log.debug('Nothing to clean: %s', max(segment_warnings))
            return False

        point_warnings = [False for _ in self.__Points]
        for index, point in enumerate(self.__Points):
            has_warning = False
            prev_segment_index = index - 1
            next_segment_index = index
            prev_segment = self.__Segments[prev_segment_index] if prev_segment_index >= 0 else None
            next_segment = self.__Segments[next_segment_index] if next_segment_index < len(self.__Segments) else None

            if not prev_segment and segment_warnings[next_segment_index] >= 3:
                has_warning = True
            if not next_segment and segment_warnings[prev_segment_index] >= 3:
                has_warning = True
            if prev_segment and next_segment:
                log.debug('point %03d: %.2f, %.2f', index, prev_segment.Speed, next_segment.Speed)
                if segment_warnings[next_segment_index] >= 3 and segment_warnings[prev_segment_index] >= 3:
                    has_warning = True

            if index <= 10 and segment_warnings[next_segment_index] >= 10:
                for i in range(index):
                    point_warnings[i] = True

            point_warnings[index] = has_warning

        if not any(point_warnings):
            log.warn('Could not clean')
            return False
        else:
            log.debug('Deleting %d points', sum(point_warnings))
            self.__Patched = True

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
        return u'Track %s: %s-%s\t%.3f km at %s (%.2f m/sec) %s%s' % (
            self.__Description,
            tsToHr(self.__StartTimestamp, fmt='%Y-%m-%d %H:%M'),
            tsToHr(self.__FinishTimestamp, fmt='%H:%M'),
            self.TotalDistance(),
            speed_to_pace(self.__AverageSpeed),
            self.__AverageSpeed,
            track_type,
            ', patched' if self.__Patched else '',
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

        if args.write and track.IsPatched():
            patchedFile = track.SourceFilename().replace(
                os.path.basename(track.SourceFilename()),
                '%s_%s_patched.gpx' % (
                    tsToHr(track.StartTimestamp(), fmt='%Y-%m-%d_%H-%M-%S'),
                    os.path.basename(track.SourceFilename()).split('.')[0],
                )
            )
            gpxWriter = gpxparser.GpxWriter()
            gpxWriter.AddPoints(track.Points())
            if gpxWriter.HasPoints():
                gpxWriter.Save(patchedFile)

            originalFile = track.SourceFilename().replace(
                os.path.basename(track.SourceFilename()),
                '%s_%s_original.gpx' % (
                    tsToHr(track.StartTimestamp(), fmt='%Y-%m-%d_%H-%M-%S'),
                    os.path.basename(track.SourceFilename()).split('.')[0],
                )
            )
            gpxWriter = gpxparser.GpxWriter()
            gpxWriter.AddPoints(original_points)
            if gpxWriter.HasPoints():
                gpxWriter.Save(originalFile)



def populate_parser(parser):
    parser.add_argument('--filter', help='Find files containg this substring')
    parser.add_argument('--write', help='Write patched files', action='store_true')
    parser.set_defaults(func=analyze)
