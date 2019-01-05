#!/usr/bin/env python

import argparse
import collections
import md5sum
import os
import webbrowser

import logging
log = logging.getLogger('treashure.garmin')


def walkFiles(dirname, extensions=[], dirsOnly=False):
    dirName = str(dirname)
    logName = 'dirs' if dirsOnly else 'files'
    log.info('Looking for %s of types %r in %s', logName, extensions, dirName)
    count = 0
    if not os.path.exists(dirName):
        log.error('Path %r is missing', dirName)
    for root, dirs, files in os.walk(dirName):
        if dirsOnly:
            for directory in dirs:
                count += 1
                yield os.path.join(root, directory)
        else:
            for filename in files:
                if not extensions or any(filename.endswith(extension) for extension in extensions):
                    count += 1
                    yield os.path.join(root, filename)
    log.info('Found %d %s in %s', count, logName, dirName)


def loadFitFiles(dirname):
    onDevice = {}
    for filename in walkFiles(dirname, extensions=['.FIT']):
        onDevice[md5sum.Md5Sum(filename)] = filename
    return onDevice


def checkGarmin(args):
    srcPath = args.garmin
    dstPath = args.tracks

    onDevice = loadFitFiles(srcPath)
    processed = loadFitFiles(dstPath)

    deviceStats = collections.defaultdict(int)
    srcFile = None
    for md5value, track in sorted(
        onDevice.iteritems(),
        key=lambda x: os.path.getmtime(x[1])
    ):
        sameImported = processed.get(md5value)
        if sameImported is None:
            deviceStats['not_imported'] += 1
            if not srcFile:
                srcFile = track
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
        if srcFile:
            log.info('Import new tracks manually')
            md5sum.openDir(srcFile)
            md5sum.openDir(dstPath)
            url = 'https://www.strava.com/upload/select'
            webbrowser.open(url, new=2)
        if deviceStats['success'] and deviceStats['success'] == deviceStats['total']:
            log.info('Clean tracks from device manually')
            md5sum.openDir(srcPath)


def CreateArgumentsParser():
    parser = argparse.ArgumentParser('Check GARMIN tracks', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--debug', help='Debug logging', action='store_true')
    parser.add_argument('--tracks', help='All tracks', default='/Volumes/Macintosh HD/Users/burmisha/Dropbox/running')
    parser.add_argument('--garmin', help='Json file to store all data', default='/Volumes/GARMIN/GARMIN/ACTIVITY')
    parser.add_argument('--open', help='Open webbrowser and dirs', action='store_true')
    parser.set_defaults(func=checkGarmin)
    return parser


if __name__ == '__main__':
    parser = CreateArgumentsParser()
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s  %(levelname)-8s %(message)s')
    log.setLevel(logging.DEBUG if args.debug else logging.INFO)
    args.func(args)
