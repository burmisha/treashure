import collections
import datetime
import library
import os
import shutil
import time
import webbrowser

import tools

import logging
log = logging.getLogger(__name__)


SYNC_LOCAL_DIR = os.path.join(library.files.Location.Dropbox, 'running')
GARMIN_DEVICE_DIR = '/Volumes/GARMIN/GARMIN/Activity'


def populate_parser(parser):
    parser.add_argument('--tracks', help='All tracks', default=SYNC_LOCAL_DIR)
    parser.add_argument('--garmin', help='Json file to store all data', default=GARMIN_DEVICE_DIR)
    parser.add_argument('-o', '--open', help='Open webbrowser and dir', action='store_true')
    parser.add_argument('-c', '--copy', help='Copy files in auto mode', action='store_true')
    parser.add_argument('-d', '--delete', help='Delete copied files', action='store_true')
    parser.add_argument('--browser', help='Default browser to use', default='Firefox')
    parser.set_defaults(func=runImport)



def loadFitFiles(dirname):
    hashsums = {}
    for filename in library.files.walk(dirname, extensions=['.FIT', '.fit']):
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
            log.info(f'Sleeping for {sleepTime} seconds: no files in {srcPath}')
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
