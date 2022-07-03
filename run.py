#!/usr/bin/env python3

import argparse
import time

import tools
import library

import logging
log = logging.getLogger('treashure')



def CreateArgumentsParser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser('Check Garmin tracks', formatter_class=formatter_class)
    parser.add_argument('--debug', help='Debug logging', action='store_true')

    subparsers = parser.add_subparsers()

    importParser = subparsers.add_parser('import', help='Import tracks from device', formatter_class=formatter_class)
    tools.import_tracks.populate_parser(importParser)

    joinParser = subparsers.add_parser('join', help='Join old tracks into one')
    tools.gpxparser.populate_parser(joinParser)

    analyzeParser = subparsers.add_parser('analyze', help='Analyze files')
    tools.speed.populate_parser(analyzeParser)

    tofmal_parser = subparsers.add_parser('tofmal', help='Download tofmal', formatter_class=formatter_class)
    tools.tofmal.populate_parser(tofmal_parser)

    return parser


if __name__ == '__main__':
    parser = CreateArgumentsParser()
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
        log.info('Completed in %.2f seconds', duration)