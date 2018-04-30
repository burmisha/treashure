#!/usr/bin/env python

import argparse
import collections
import md5sum
import os
import platform
import subprocess
import webbrowser

import logging
log = logging.getLogger('backend')


def walkFiles(dirname, extensions=[], dirsOnly=False):
    logName = 'dirs' if dirsOnly else 'files'
    log.info('Looking for {} of types {} in {}'.format(logName, extensions, dirname))
    count = 0
    for root, dirs, files in os.walk(str(dirname)):
        if dirsOnly:
            for directory in dirs:
                count += 1
                yield os.path.join(root, directory)
        else:
            for filename in files:
                if not extensions or any(filename.endswith(extension) for extension in extensions):
                    count += 1
                    yield os.path.join(root, filename)
    log.info('Found {} {} in {}'.format(count, logName, dirname))


def openDir(dirname):
    if os.path.isdir(dirname):
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', dirname + '/'])
        else:
            log.warn('Could not open path, only OS X is supported')
    else:
        raise RuntimeError('No dir {!r}'.format(dirname))


def checkGarmin(args):
    srcPath = args.garmin
    dstPath = args.tracks
    onDevice = {}
    for filename in walkFiles(srcPath, extensions=['.FIT']):
        onDevice[md5sum.Md5Sum(filename)] = filename

    processed = {}
    for filename in walkFiles(dstPath, extensions=['.FIT']):
        processed[md5sum.Md5Sum(filename)] = filename

    deviceStats = collections.defaultdict(int)
    for md5value, track in sorted(
        onDevice.iteritems(),
        key=lambda x: os.path.getmtime(x[1])
    ):
        sameImported = processed.get(md5value)
        if sameImported is None:
            deviceStats['not_imported'] += 1
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
        if deviceStats['not_imported']:
            log.info('Import new tracks manually')
            openDir(srcPath)
            openDir(dstPath)
            url = 'https://www.strava.com/upload/select'
            webbrowser.open(, new=2)
        if deviceStats['success'] and deviceStats['success'] == deviceStats['total']:
            log.info('Clean tracks from device manually')
            openDir(srcPath)


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
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    log.setLevel(logging.DEBUG if args.debug else logging.INFO)
    args.func(args)
