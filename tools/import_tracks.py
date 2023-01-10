import library
import os
import shutil
import time
import webbrowser

from functools import cached_property
from typing import Dict, List

import attr
import tools

import logging
log = logging.getLogger(__name__)


DEFAULT_SLEEP_TIME = 5  # seconds
DEFAULT_URL = 'https://www.strava.com/upload/select'
DEFAULT_BROWSER = 'Firefox'


def populate_parser(parser):
    parser.add_argument('--tracks', help='Result tracks dirname', default=tools.model.SYNC_LOCAL_DIR)
    parser.add_argument('--garmin', help='Garmin dirname', default=tools.model.GARMIN_DEVICE_DIR)
    parser.add_argument('-o', '--open', help='Open webbrowser and dir', action='store_true')
    parser.add_argument('-c', '--copy', help='Copy files in auto mode', action='store_true')
    parser.add_argument('-d', '--delete', help='Delete copied files', action='store_true')
    parser.add_argument('--browser', help='Default browser to use', default=DEFAULT_BROWSER)
    parser.add_argument('--url', help='Default url to open', default=DEFAULT_URL)
    parser.add_argument('--sleep-time', help='Seconds to wait before tries', type=int, default=DEFAULT_SLEEP_TIME)
    parser.set_defaults(func=run_from_args)


@attr.s
class SrcFile:
    filename: str = attr.ib()

    @cached_property
    def md5sum(self) -> str:
        return library.md5sum.Md5Sum(self.filename)

    @cached_property
    def mtime(self) -> str:
        return os.path.getmtime(self.filename)


def get_fit_files(dirname) -> List[SrcFile]:
    return [
        SrcFile(filename)
        for filename in library.files.walk(dirname, extensions=['.FIT', '.fit'])
    ]


def wait_fit_files(dirname: str, sleep_time: int) -> List[SrcFile]:
    files = []
    while not files:
        files = get_fit_files(dirname)
        if files:
            return files
        else:
            log.info(f'Sleeping for {sleep_time} seconds: no files in {dirname}')
            time.sleep(sleep_time)


@attr.s
class Stats:
    copy: int = attr.ib(default=0)
    skip_copy: int = attr.ib(default=0)
    broken_name: int = attr.ib(default=0)
    success: int = attr.ib(default=0)
    total: int = attr.ib(default=0)


@attr.s
class ImportConfig:
    source_dir: str = attr.ib()
    destination_dir: str = attr.ib()
    sleep_time: int = attr.ib()
    copy_files: bool = attr.ib()
    delete_copied_files: bool = attr.ib()

    open_browser: bool = attr.ib()
    url: str = attr.ib()
    browser: str = attr.ib()


def run_from_args(args):
    import_config = ImportConfig(
        source_dir=args.garmin,
        destination_dir=args.tracks,
        sleep_time=args.sleep_time,
        copy_files=args.copy,
        delete_copied_files=args.delete,
        open_browser=args.open,
        url=args.url,
        browser=args.browser,
    )
    run_import(import_config)


def run_import(import_config: ImportConfig):
    device_files = get_fit_files(import_config.source_dir)
    processed_files = {
        fit_file.md5sum: fit_file
        for fit_file in wait_fit_files(import_config.destination_dir, sleep_time=import_config.sleep_time)
    }

    device_files.sort(key=lambda fit_file: fit_file.mtime)
    for f in device_files:
        f.md5sum  # cache

    stats = Stats()
    for src_file in device_files:
        track = tools.fitreader.read_fit_file(src_file.filename, raise_on_error=False)
        log.info(track)
        # if track.is_valid:
        #     tools.speed.analyze_track(track)
        dst_file = os.path.join(import_config.destination_dir, track.year_dir, track.canonic_basename)

        imported_file = processed_files.get(src_file.md5sum)
        if imported_file is None:
            if import_config.copy_files:
                stats.copy += 1
                log.debug(f'Copy: {src_file.filename} -> {dst_file}')
                shutil.copy(src_file.filename, dst_file)
            else:
                stats.skip_copy += 1
                log.debug(f'Skip copy: {src_file} -> {dst_file}')
        else:
            if os.path.basename(src_file.filename) not in os.path.basename(imported_file.filename):
                stats.broken_name += 1
                log.warn(f'Broken name: {src_file} -> {imported_file.filename}')
            else:
                stats.success += 1
                log.debug(f'Success: {src_file} -> {imported_file.filename}')

    stats.total = stats.copy + stats.skip_copy + stats.broken_name + stats.success
    log.info(f'Device files stats: {stats}')

    if import_config.open_browser and device_files:
        library.files.open_dir(device_files[-1].filename)
        controller = webbrowser.get(import_config.browser)
        controller.open_new_tab(import_config.url)

    for fit_file in device_files:
        if fit_file.md5sum in processed_files:
            log.info(f'Can delete {fit_file}')
            if import_config.delete_copied_files:
                os.remove(fit_file.filename)
