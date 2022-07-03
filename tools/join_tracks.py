import os
from typing import List

from tools.gpxwriter import GpxWriter
from tools.fitreader import read_fit_file

import library
from tools.model import DEFAULT_TRACKS_LOCATION

import logging
log = logging.getLogger(__name__)


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



def join_tracks(source_files: List[str], joined_file: str):
    log.info(f'Joining tracks {source_files} to {joined_file}',)

    gpxWriter = GpxWriter(joined_file)
    for source_file in source_files:
        fit_reader = FitReader(source_file)
        gpxWriter.AddPoints(fit_reader.Load())

    if gpxWriter.HasPoints():
        gpxWriter.Save()


def run(args):
    location = args.location
    for dirname in GPX_FOLDERS:
        assert os.path.basename(dirname) == dirname
        joined_file = os.path.join(location, dirname, f'{dirname}-joined.gpx')
        if os.path.exists(joined_file) and not args.force:
            log.info(f'Skipping {dirname}: result {joined_file} exists')
            continue

        source_files = list(library.files.walk(os.path.join(location, dirname), extensions=['.FIT']))
        if not source_files:
            log.info(f'Skipping {joined_file} for {dirname}: might be gpx')
            continue

        log.info(f'Creating {joined_file} for {dirname}')
        join_tracks(source_files, joined_file)


def populate_parser(parser):
    parser.add_argument('--location', help='Location to join tracks', default=DEFAULT_TRACKS_LOCATION)
    parser.add_argument('--force', help='Force generation for existing files', action='store_true')
    parser.set_defaults(func=run)
