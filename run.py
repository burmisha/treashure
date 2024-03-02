#!/usr/bin/env python3

import argparse
import time

import tools
import tools.charity
import tools.charity.donations
import tools.charity.sluchaem
import tools.photo.calculate
import tools.running.process.sync
import tools.running.process.join
import tools.running.process.analyze
import tools.photo.deduplicate
import tools.photo.calculate
import tools.photo.compare
import tools.photo.parse
import tools.photo.renamer
import tools.photo.airdrop

import logging
log = logging.getLogger('treashure')


COMMANDS = [
    ('track-import', 'Import tracks from device', tools.running.process.sync.populate_parser),
    ('track-join', 'Join old tracks into one', tools.running.process.join.populate_parser),
    ('track-analyze', 'Analyze track files', tools.running.process.analyze.populate_parser),
    ('photo-deduplicate', 'Deduplicate mobile photos', tools.photo.deduplicate.populate_parser),
    ('photo-calculate', 'Calculate photos stats', tools.photo.calculate.populate_parser),
    ('photo-calc', 'Run calc', tools.photo.compare.populate_calc_parser),
    ('photo-compare', 'Run compare', tools.photo.compare.populate_compare_parser),
    ('flickr-parse', 'Prepare photos', tools.photo.parse.populate_parser),
    ('photo-rename', 'Rename vsco photos', tools.photo.renamer.populate_parser),
    ('airdrop-move', 'Move airdrop photos to one dir', tools.photo.airdrop.populate_parser),
    ('sluchaem', 'Print sluchaem data', tools.charity.sluchaem.populate_parser),
    ('donations', 'Print donations data', tools.charity.donations.populate_parser),
]


def create_arguments_parser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser('Common runner', formatter_class=formatter_class)
    parser.add_argument('--debug', help='Debug logging', action='store_true')

    subparsers = parser.add_subparsers()
    for cmd, desc, populate_func in COMMANDS:
        subparser = subparsers.add_parser(cmd, help=desc, formatter_class=formatter_class)
        populate_func(subparser)


    return parser


if __name__ == '__main__':
    parser = create_arguments_parser()
    args = parser.parse_args()

    logFormat=' '.join([
        '%(asctime)s.%(msecs)03d',
        # '%(name)20s:%(lineno)-4d',
        '%(levelname)-7s',
        ' %(message)s',
    ])
    logLevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=logLevel, format=logFormat, datefmt='%H:%M:%S')

    start_time = time.time()
    try:
        args.func(args)
    except Exception as e:
        finish_time = time.time()
        duration = finish_time  - start_time
        log.exception(f'Failed after {duration:.3f} seconds, exception: {e}')
        exit(1)
    else:
        finish_time = time.time()
        duration = finish_time  - start_time
        log.info(f'Completed in {duration:.3f} seconds', )
