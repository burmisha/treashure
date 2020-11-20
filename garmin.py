#!/usr/bin/env python

import argparse
import collections
import datetime
import os
import shutil
import time
import webbrowser

import tools
import library

import logging
log = logging.getLogger('treashure.garmin')


def loadFitFiles(dirname):
    hashsums = {}
    for filename in library.files.walk(dirname, extensions=['.FIT']):
        hashsums[library.md5sum.Md5Sum(filename)] = filename
    return hashsums


def runImport(args):
    srcPath = args.garmin
    dstPath = args.tracks

    onDevice = None
    while not onDevice:
        onDevice = loadFitFiles(srcPath)
        sleepTime = 5
        if not onDevice:
            log.info('Sleeping for %r seconds', sleepTime)
            time.sleep(sleepTime)
    processed = loadFitFiles(dstPath)

    deviceStats = collections.Counter()
    latest_file = None
    for md5value, src_file in sorted(
        onDevice.items(),
        key=lambda x: os.path.getmtime(x[1])
    ):
        fit_parser = tools.gpxparser.FitParser(src_file)
        tools.speed.analyze_track(fit_parser)
        ts = datetime.datetime.fromtimestamp(fit_parser.FirstTimestamp)
        dst_file = os.path.basename(src_file)
        dst_file = os.path.join(dstPath, ts.strftime('%Y'), ts.strftime('%F_%T_{}'.format(dst_file)).replace(':', '-'))
        latest_file = dst_file

        sameImported = processed.get(md5value)
        if sameImported is None:
            deviceStats['not_imported'] += 1
            log.info('Copy %s -> %s', src_file, dst_file)
            if args.copy:
                shutil.copy(src_file, dst_file)
            else:
                log.info('Skipping copy')
        else:
            if os.path.basename(src_file) not in os.path.basename(sameImported):
                log.warn('Broken name: %r -> %r', src_file, sameImported)
                deviceStats['broken_name'] += 1
            else:
                deviceStats['success'] += 1
                log.debug('Success: %r -> %r', src_file, sameImported)            
        deviceStats['total'] += 1

    log.info('Device files stats: %r', dict(deviceStats))

    if args.open:
        library.files.open_dir(latest_file)
        url = 'https://www.strava.com/upload/select'
        controller = webbrowser.get(args.browser)
        controller.open_new_tab(url)

    for md5value in sorted(set(onDevice) & set(processed)):
        src_file = onDevice[md5value]
        log.info('Can delete %s', src_file)
        if args.delete:
            os.remove(src_file)


def CreateArgumentsParser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser('Check Garmin tracks', formatter_class=formatter_class)
    parser.add_argument('--debug', help='Debug logging', action='store_true')
    subparsers = parser.add_subparsers()

    importParser = subparsers.add_parser('import', help='Import tracks from device', formatter_class=formatter_class)
    importParser.add_argument('--tracks', help='All tracks', default=os.path.join(library.files.Location.Dropbox, 'running'))
    importParser.add_argument('--garmin', help='Json file to store all data', default='/Volumes/GARMIN/GARMIN/ACTIVITY')
    importParser.add_argument('-o', '--open', help='Open webbrowser and dir', action='store_true')
    importParser.add_argument('-c', '--copy', help='Copy files in auto mode', action='store_true')
    importParser.add_argument('-d', '--delete', help='Delete copied files', action='store_true')
    importParser.add_argument('--browser', help='Default browser to use', default='Firefox')
    importParser.set_defaults(func=runImport)

    joinParser = subparsers.add_parser('join', help='Join old tracks into one')
    tools.gpxparser.populate_parser(joinParser)

    analyzeParser = subparsers.add_parser('analyze', help='Analyze files')
    tools.speed.populate_parser(analyzeParser)

    return parser


if __name__ == '__main__':
    parser = CreateArgumentsParser()
    args = parser.parse_args()

    logFormat='%(asctime)s  %(levelname)-8s %(message)s'
    logLevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=logLevel, format=logFormat, datefmt='%H:%M:%S')

    start_time = time.time()
    args.func(args)
    finish_time = time.time()
    duration = finish_time  - start_time
    if duration >= 2:
        log.info('Completed in %.2f seconds', duration)
