#!/usr/bin/env python3

import argparse
import time

import tools

import logging
log = logging.getLogger('treashure')


def create_arguments_parser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser('Common runner', formatter_class=formatter_class)
    parser.add_argument('--debug', help='Debug logging', action='store_true')

    subparsers = parser.add_subparsers()

    def add_subparser(cmd: str, desc: str, populate_func):
        subparser = subparsers.add_parser(cmd, help=desc, formatter_class=formatter_class)
        populate_func(subparser)

    add_subparser('import', 'Import tracks from device', tools.import_tracks.populate_parser)
    add_subparser('join', 'Join old tracks into one', tools.join_tracks.populate_parser)
    add_subparser('analyze', 'Analyze files', tools.speed.populate_parser)
    add_subparser('photo-parse', 'Parse mobile photos', tools.mobile.analyze.populate_parser)
    add_subparser('photo-analyze', 'Analyze mobile photos', tools.mobile.mobile.populate_parser)
    add_subparser('photo-calc', 'Run calc', tools.photo.compare.populate_calc_parser)
    add_subparser('photo-compare', 'Run compare', tools.photo.compare.populate_compare_parser)
    add_subparser('flickr-parse', 'Prepare photos', tools.photo.parse.populate_parser)

    return parser


if __name__ == '__main__':
    parser = create_arguments_parser()
    args = parser.parse_args()

    logFormat='%(asctime)s  %(levelname)-8s %(message)s'
    logLevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=logLevel, format=logFormat, datefmt='%H:%M:%S')

    start_time = time.time()
    try:
        args.func(args)
    except Exception as e:
        log.exception(f'Error: {e}')
        raise
    finally:
        finish_time = time.time()
        duration = finish_time  - start_time
        log.info(f'Completed in {duration:.3f} seconds', )
