import os
import datetime
import pprint

from typing import List, Optional


from tools.gpxwriter import GpxWriter
from tools.fitreader import FitReader

import fitparse
import gpxpy

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



def join_tracks(source_files: List[str], resultFile: str):
    log.info(f'Joining tracks {source_files} to {resultFile}',)
    gpxWriter = GpxWriter()

    for source_file in source_files:
        fitParser = FitParser(source_file)
        gpxWriter.AddPoints(fitParser.Load())

    if gpxWriter.HasPoints():
        gpxWriter.Save(resultFile)


def run(args):
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
    parser.set_defaults(func=run)
