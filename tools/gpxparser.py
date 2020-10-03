import os
import datetime

import fitparse
import gpxpy
import gpxpy.gpx

from xml.etree import ElementTree

import library

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


class GeoPoint(object):
    def __init__(
        self,
        longitude=None,
        latitude=None,
        altitude=None,
        timestamp=None,
        cadence=None,
        heartRate=None
    ):
        self.Longitude = longitude
        self.Latitude = latitude
        self.Altitude = altitude
        self.Timestamp = timestamp
        self.Cadence = cadence
        self.HeartRate = heartRate

    def GetDatetime(self):
        return datetime.datetime.fromtimestamp(self.Timestamp)

    def __repr__(self):
        return str(self.__str__())

    def __str__(self):
        return {
            'Lng': self.Longitude,
            'Lat': self.Latitude,
            'Alt': self.Altitude,
            'Ts': self.Timestamp,
            'Dt': self.GetDatetime(),
        }


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
        fitFile = fitparse.FitFile(self.__Filename)
        fitFile.parse()

        count = 0
        failures = []
        for count, message in enumerate(fitFile.get_messages(name='record'), 1):
            values = message.get_values()
            timestamp = int((values['timestamp'] - datetime.datetime(1970, 1, 1)).total_seconds())
            if count == 1:
                log.debug('First timestamp: %s', values['timestamp'])
                self.FirstTimestamp = timestamp
            log.debug('Values: %s', values)
            try:
                assert timestamp > 100000000
                if 'enhanced_altitude' in values:
                    assert values['enhanced_altitude'] == values['altitude']
                if 'position_long' not in values:
                    failures.append(count)
                    continue
                self.__Points.append(GeoPoint(
                    longitude=self.__FromSemicircles(values['position_long']),
                    latitude=self.__FromSemicircles(values['position_lat']),
                    altitude=values['altitude'],
                    cadence=values['cadence'],
                    heartRate=values['heart_rate'],
                    timestamp=timestamp,
                ))
            except:
                log.exception('Complete failure on %s in file %s', count, self.__Filename)
                pprint.pprint(values)
                raise

        if len(failures) > 200 or len(failures) > 0.25 * count:
            self.IsValid = False
        if failures:
            log.info(
                'File %s is %s: %d points and %d failures, %r (3 first ones)', 
                self.__Filename, 
                'ok' if self.IsValid else 'not ok',
                count,
                len(failures),
                failures[:3],
            )
        else:
            log.info(
                'File %s is %s: %d points', 
                self.__Filename, 
                'ok' if self.IsValid else 'not ok',
                count,
            )

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
            if point.HeartRate:
                # https://stackoverflow.com/questions/48795435/gpxpy-how-to-extract-heart-rate-data-from-gpx-file
                # https://github.com/shaonianche/running-data-sync/blob/3d257799358e4d051cf9719af6ba0334aa414fdb/scripts/strava.py
                gpx_extension_hr = ElementTree.fromstring(
                    """<gpxtpx:TrackPointExtension xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">
                        <gpxtpx:hr>{}</gpxtpx:hr>
                        </gpxtpx:TrackPointExtension>
                    """.format(point.HeartRate)
                )
                gpxTrackPoint.extensions.append(gpx_extension_hr)
            self.__Points.append(gpxTrackPoint)

    def HasPoints(self):
        return len(self.__Points) > 0

    def ToXml(self):
        if not self.__Points:
            raise RuntimeError('No points')

        log.debug('Create GPX')
        gpx = gpxpy.gpx.GPX()

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


def joinTracks(source_files, resultFile):
    log.info('Joining tracks %s to %s', source_files, resultFile)

    gpxWriter = GpxWriter()

    for source_file in source_files:
        fitParser = FitParser(source_file)
        gpxWriter.AddPoints(fitParser.Load())

    if gpxWriter.HasPoints():
        gpxWriter.Save(resultFile)


def parseFit(args):
    location = args.location
    for dirname in GPX_FOLDERS:
        log.info('Checking %s', dirname)
        assert os.path.basename(dirname) == dirname
        resultFile = os.path.join(location, dirname, '{}-joined.gpx'.format(dirname))
        if args.force or not os.path.exists(resultFile):
            source_files = list(library.files.walk(os.path.join(location, dirname), extensions=['.FIT']))
            joinTracks(source_files, resultFile)
        else:
            log.info('Skipping %s: result %s exists', dirname, resultFile)


def populate_parser(parser):
    parser.add_argument('--location', help='Location to join tracks', default=DEFAULT_TRACKS_LOCATION)
    parser.add_argument('--force', help='Force generation for existing files', action='store_true')
    parser.set_defaults(func=parseFit)
