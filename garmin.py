#!/usr/bin/env python

import argparse
import collections
import datetime
import os
import time
import webbrowser

import tools
import library

import logging
log = logging.getLogger('treashure.garmin')


def loadFitFiles(dirname):
    hashsums = {}
    for filename in library.files.walk(dirname, extensions=['.FIT']):
        hashsums[tools.md5sum.Md5Sum(filename)] = filename
    return hashsums


def getPathToOpen(path, srcFile):
    dirname = os.path.join(path, datetime.datetime.fromtimestamp(os.path.getmtime(srcFile)).strftime('%Y'))
    if not os.path.exists(dirname):
        log.warn('Create missing %s', dirname)
        return dirname
    else:
        filename = library.files.walk(dirname).next()
        return filename


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

    deviceStats = collections.defaultdict(int)
    sourceFiles = []
    for md5value, track in sorted(
        onDevice.iteritems(),
        key=lambda x: os.path.getmtime(x[1])
    ):
        sameImported = processed.get(md5value)
        if sameImported is None:
            deviceStats['not_imported'] += 1
            sourceFiles.append(track)
            log.warn('Not imported: %r', track)
        elif os.path.basename(sameImported) != os.path.basename(track):
            log.warn('Broken name: %r -> %r', track, sameImported)
            deviceStats['broken_name'] += 1
        else:
            log.info('Success: %r -> %r', track, sameImported)
            deviceStats['success'] += 1
        deviceStats['total'] += 1
    log.info('Device files stats: %r', dict(deviceStats))

    if args.open:
        if sourceFiles:
            log.info('Import new tracks manually')
            library.files.open_dir(sourceFiles[0])
            library.files.open_dir(getPathToOpen(dstPath, sourceFiles[0]))
            url = 'https://www.strava.com/upload/select'
            webbrowser.open(url, new=2)
        if deviceStats['success'] and deviceStats['success'] == deviceStats['total']:
            log.info('Clean tracks from device manually')
            library.files.open_dir(srcPath)


def CreateArgumentsParser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser('Check Garmin tracks', formatter_class=formatter_class)
    parser.add_argument('--debug', help='Debug logging', action='store_true')
    subparsers = parser.add_subparsers()

    importParser = subparsers.add_parser('import', help='Import tracks from device', formatter_class=formatter_class)
    importParser.add_argument('--tracks', help='All tracks', default='/Volumes/Macintosh HD/Users/burmisha/Dropbox/running')
    importParser.add_argument('--garmin', help='Json file to store all data', default='/Volumes/GARMIN/GARMIN/ACTIVITY')
    importParser.add_argument('--open', help='Open webbrowser and dirs', action='store_true')
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
