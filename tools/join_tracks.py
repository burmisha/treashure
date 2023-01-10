import os
from typing import List

from tools.fitreader import read_fit_file
from tools.gpxwriter import save_gpx, to_gpx
from tools.model import DEFAULT_TRACKS_LOCATION
import library

import logging
log = logging.getLogger(__name__)


GPX_FOLDERS = [
    '2014.05 Baltic',
    '2014.07 Hungary',
    '2014.07 NNov',
    '2014.08 Moldova',
    '2014.11 Germany',
    '2014.12 Switzerland',
    '2015.01 Prague',
    '2015.05 Italy',
    '2015.07 Greece',
    '2015.07 Klyazma',
    '2015.08 Karelia',
    '2016.05 Montenegro',
    '2016.07 Baku',
    '2016.08 Georgia',
    '2017.09 Italy',
    '2017.11 Germany',
    '2017.12 Germany',
    '2018.04 Gent',
    '2018.12 Poland',
]


def process_dir(
    *,
    dirname: str,
    save: bool,
    overwrite: bool,
):
    base_dir = os.path.basename(dirname)
    joined_file = os.path.join(dirname, f'{base_dir} - joined.gpx')

    if os.path.exists(joined_file) and save and not overwrite:
        log.info(f'Skipping {dirname}: result {joined_file} exists')
        return

    source_files = list(library.files.walk(dirname, extensions=['.FIT']))
    if not source_files:
        log.info(f'Skipping {joined_file} for {base_dir}: might be gpx')
        return

    points = []
    log.info(f'Creating {joined_file!r} for {dirname!r} from {len(source_files)} files:')
    for index, source_file in enumerate(source_files, 1):
        log.info(f'    {index}/{len(source_files)}: {source_file}')
        points += read_fit_file(source_file).points

    if points:
        gpx = to_gpx(points)
        if save:
            save_gpx(gpx, joined_file)


def run(args):
    for dirname in GPX_FOLDERS:
        process_dir(
            dirname=os.path.join(args.location, dirname),
            save=args.save,
            overwrite=args.overwrite,
        )


def populate_parser(parser):
    parser.add_argument('--location', help='Location to join tracks', default=DEFAULT_TRACKS_LOCATION)
    parser.add_argument('--save', help='Do save', action='store_true')
    parser.add_argument('--overwrite', help='Overwrite existing files', action='store_true')
    parser.set_defaults(func=run)
