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


def populate_parser(parser):
    parser.add_argument('--tracks', help='All tracks', default=tools.model.SYNC_LOCAL_DIR)
    parser.add_argument('--garmin', help='Json file to store all data', default=tools.model.GARMIN_DEVICE_DIR)
    parser.add_argument('-o', '--open', help='Open webbrowser and dir', action='store_true')
    parser.add_argument('-c', '--copy', help='Copy files in auto mode', action='store_true')
    parser.add_argument('-d', '--delete', help='Delete copied files', action='store_true')
    parser.add_argument('--browser', help='Default browser to use', default='Firefox')
    parser.set_defaults(func=runImport)



def loadFitFiles(dirname) -> dict:
    return {
        library.md5sum.Md5Sum(filename): filename
        for filename in library.files.walk(dirname, extensions=['.FIT', '.fit'])
    }


def load_device_files(source_dir: str, sleep_time: int = 5) -> dict:
    onDevice = {}
    while not onDevice:
        onDevice = loadFitFiles(source_dir)
        if onDevice:
            return onDevice
        else:
            log.info(f'Sleeping for {sleep_time} seconds: no files in {source_dir}')
            time.sleep(sleep_time)


def runImport(args):
    src_dir = args.garmin
    dst_dir = args.tracks

    onDevice = load_device_files(src_dir)
    processed = loadFitFiles(dst_dir)

    deviceStats = collections.Counter()
    latest_file = None
    for md5value, src_file in sorted(
        onDevice.items(),
        key=lambda x: os.path.getmtime(x[1])
    ):
        track = tools.fitreader.read_fit_file(src_file)
        tools.speed.analyze_track(track)
        dst_file = os.path.join(dst_dir, track.start_ts.strftime('%Y'), track.canonic_basename)
        latest_file = dst_file

        sameImported = processed.get(md5value)
        if sameImported is None:
            deviceStats['not_imported'] += 1
            log.info(f'Copy {src_file} -> {dst_file}')
            if args.copy:
                shutil.copy(src_file, dst_file)
            else:
                log.info('Skipping copy')
        else:
            if os.path.basename(src_file) not in os.path.basename(sameImported):
                log.warn(f'Broken name: {src_file} -> {sameImported}')
                deviceStats['broken_name'] += 1
            else:
                deviceStats['success'] += 1
                log.debug(f'Success: {src_file} -> {sameImported}')
        deviceStats['total'] += 1

    log.info(f'Device files stats: {dict(deviceStats)}')

    if args.open and latest_file:
        library.files.open_dir(latest_file)
        url = 'https://www.strava.com/upload/select'
        controller = webbrowser.get(args.browser)
        controller.open_new_tab(url)

    for md5value in sorted(set(onDevice) & set(processed)):
        src_file = onDevice[md5value]
        log.info(f'Can delete {src_file}')
        if args.delete:
            os.remove(src_file)
