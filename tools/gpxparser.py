import os
import datetime
import pprint

from typing import List, Optional


import fitparse
import gpxpy
import gpxpy.gpx

from xml.etree import ElementTree

import library
import attr
import logging
log = logging.getLogger(__name__)

DEFAULT_TRACKS_LOCATION = os.path.join(library.files.Location.Dropbox, 'running', 'tracks')

GPX_FOLDERS = [
    '2014-05-Baltic',
    '2014-07-Hungary',
    '2014-07-NNov',
    '2014-08-Moldova',
    '2014-11-Germany',
    '2014-12-Switzerland',
    '2015-01-Prague',
    '2015-05-Italy',
    '2015-07-Greece',
    '2015-07-Klyazma',
    '2015-08-Karelia',
    '2016-05-Montenegro',
    '2016-07-Baku',
    '2016-08-Georgia',
    '2017-09-Italy',
    '2017-11-Germany',
    '2017-12-Germany',
    '2018-04-Gent',
    '2018-12 Poland',
]


@attr.s
class GeoPoint(object):
    longitude: float = attr.ib(default=None)
    latitude: float = attr.ib(default=None)
    altitude: Optional[float] = attr.ib(default=None)
    timestamp: Optional[float] = attr.ib(default=None)
    cadence: Optional[float] = attr.ib(default=None)
    heart_rate: Optional[float] = attr.ib(default=None)

    @property
    def datetime(self):
        return datetime.datetime.fromtimestamp(self.timestamp)

    def __str__(self):
        return {
            'Lng': self.longitude,
            'Lat': self.latitude,
            'Alt': self.altitude,
            'Ts': self.timestamp,
            'Dt': self.datetime,
        }


class ErrorThreshold:
    MIN_COUNT = 200
    SHARE = 0.4


class FitParser(object):
    def __init__(self, filename):
        self.__Filename = filename
        self.__Points = []
        self.IsValid = True
        self.FirstTimestamp = None
        self.__LoadPoints()

    def Description(self):
        return os.path.basename(self.__Filename)

    def Filename(self):
        return self.__Filename

    def __FromSemicircles(self, value):
        # https://forums.garmin.com/forum/developers/garmin-developer-information/60220-
        return float(value) * 180 / (2 ** 31)

    def __LoadPoints(self):
        log.debug(f'Loading {self.__Filename}')
        try:
            fitFile = fitparse.FitFile(self.__Filename, check_crc=True)
        except fitparse.utils.FitCRCError:
            log.warning(f'FitCRCError on {self.__Filename}', )
            fitFile = fitparse.FitFile(self.__Filename, check_crc=False)
        fitFile.parse()

        count = 0
        failures = []
        for count, message in enumerate(fitFile.get_messages(name='record'), 1):
            values = message.get_values()
            timestamp = int((values['timestamp'] - datetime.datetime(1970, 1, 1)).total_seconds())
            if count == 1:
                log.debug('First timestamp: %s', values['timestamp'])
                self.FirstTimestamp = timestamp
            log.debug(f'Values: {values}')
            try:
                assert timestamp > 100000000
                if 'enhanced_altitude' in values:
                    assert values['enhanced_altitude'] == values['altitude']
                if values.get('position_long') is None or values.get('position_lat') is None:
                    failures.append(count)
                    continue
                geo_point = GeoPoint(
                    longitude=self.__FromSemicircles(values['position_long']),
                    latitude=self.__FromSemicircles(values['position_lat']),
                    altitude=values['altitude'],
                    cadence=values.get('cadence') or None,
                    heart_rate=values.get('heart_rate') or None,
                    timestamp=timestamp,
                )
                self.__Points.append(geo_point)
            except:
                log.exception('Complete failure on %s in file %s', count, self.__Filename)
                pprint.pprint(values)
                raise

        if len(failures) > ErrorThreshold.MIN_COUNT or len(failures) > ErrorThreshold.SHARE * count:
            self.IsValid = False

        ok_str = 'ok' if self.IsValid else 'not ok'
        if failures:
            log.info(
                f'File {self.__Filename} is {ok_str}: {count} points '
                f'and {len(failures)} failures, {failures[:3]} (3 first ones)', 
            )
        else:
            log.debug('File {self.__Filename} is {ok_str}: {count} points')

    def Load(self, raise_on_error=True):
        if raise_on_error and not self.IsValid:
            log.error('Error')
            raise RuntimeError('Too many failures')

        for point in self.__Points:
            yield point


class GpxWriter(object):
    def __init__(self):
        self.__Points = []

    def AddPoints(self, points):
        for point in points:
            gpxTrackPoint = gpxpy.gpx.GPXTrackPoint(
                latitude=point.Latitude,
                longitude=point.Longitude,
                elevation=point.Altitude,
                time=point.GetDatetime(),
            )
            count = 0
            namespace = '{gpxtpx}'
            extensionElement = ElementTree.Element(namespace + 'TrackPointExtension')
            for suffix, value in [
                ('hr', point.HeartRate),
                ('cad', point.Cadence),
            ]:
                if value:
                    count += 1
                    subElement = ElementTree.Element(namespace + suffix)
                    subElement.text = str(value)
                    extensionElement.insert(count, subElement)
            if count:
                gpxTrackPoint.extensions.append(extensionElement)
            self.__Points.append(gpxTrackPoint)

    def HasPoints(self):
        return len(self.__Points) > 0

    def ToXml(self):
        if not self.__Points:
            raise RuntimeError('No points')

        log.debug('Create GPX')
        gpx = gpxpy.gpx.GPX()
        gpx.nsmap = {
            'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
        }

        log.debug('Create first track in GPX')
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        log.debug('Create first segment in GPX track')
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        log.debug('Add points to segment in GPX track')
        self.__Points.sort(key=lambda point: point.time)
        gpx_segment.points.extend(self.__Points)

        return gpx.to_xml()

    def Save(self, filename):
        assert self.__Points
        log.info('Writing {} points to {}'.format(len(self.__Points), filename))
        with open(filename, 'w') as f:
            f.write(self.ToXml())


def join_tracks(source_files: List[str], resultFile: str):
    log.info(f'Joining tracks {source_files} to {resultFile}',)
    gpxWriter = GpxWriter()

    for source_file in source_files:
        fitParser = FitParser(source_file)
        gpxWriter.AddPoints(fitParser.Load())

    if gpxWriter.HasPoints():
        gpxWriter.Save(resultFile)


def parseFit(args):
    location = args.location
    for dirname in GPX_FOLDERS:
        log.info(f'Checking {dirname}')
        assert os.path.basename(dirname) == dirname
        resultFile = os.path.join(location, dirname, f'{dirname}-joined.gpx')
        if args.force or not os.path.exists(resultFile):
            source_files = list(library.files.walk(os.path.join(location, dirname), extensions=['.FIT']))
            join_tracks(source_files, resultFile)
        else:
            log.info(f'Skipping {dirname}: result {resultFile} exists')


def populate_parser(parser):
    parser.add_argument('--location', help='Location to join tracks', default=DEFAULT_TRACKS_LOCATION)
    parser.add_argument('--force', help='Force generation for existing files', action='store_true')
    parser.set_defaults(func=parseFit)
