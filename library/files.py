import enum
import os
import platform
import subprocess
import json

from typing import List, Optional

import logging
log = logging.getLogger(__name__)


class Platform(str, enum.Enum):
    Windows = 'win'
    macOS = 'osx'


def _get_platform() -> Platform:
    system = platform.system()
    if system == 'Windows':
        return Platform.Windows
    elif system == 'Darwin':
        return Platform.macOS
    else:
        raise RuntimeError(f'Invalid platform system {system!r}')


class Location:
    Home = os.environ['HOME']
    Dropbox = os.path.join(Home, 'Dropbox')
    Downloads = os.path.join(Home, 'Downloads')
    YandexDisk = {
        Platform.Windows: os.path.join('D:' + os.sep, 'YandexDisk'),
        Platform.macOS: os.path.join(Home, 'Yandex.Disk.localized'),
    }[_get_platform()]


def walk(dirname, extensions=[], dirsOnly=False):
    dirName = str(dirname)
    logName = 'dirs' if dirsOnly else 'files'
    log.debug('Looking for %s of types %r in %s', logName, extensions, dirName)

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

    log.debug('Found %d %s in %s', count, logName, dirName)


def open_dir(location):
    if os.path.exists(location):
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', location])
        else:
            log.warn('Could not open location, only macOS is supported for now')
    else:
        raise RuntimeError('No location {!r}'.format(location))


def get_filenames(
    *,
    dirs: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    skip_paths: Optional[List[str]] = None,
):
    filenames_count = 0

    for filename in files:
        filenames_count += 1
        yield filename

    skip_set = set(skip_paths) if skip_paths else set()
    for dir_name in dirs:
        for root, _, files in os.walk(dir_name):
            if any(path in root for path in skip_set):
                log.info(f'{root} is excluded')
                continue

            files = sorted(list(files))
            log.info(f'Found {len(files)} files in {root}')
            for filename in files:
                filenames_count += 1
                yield os.path.join(root, filename)
                if filenames_count % 500 == 0:
                    log.info(f'Yielded {filenames_count} photo files')

    log.info(f'Yielded {filenames_count} photo files')


def save_json(filename: str, data):
    with open(filename, 'w') as f:
        f.write(json.dumps(
            data,
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        ))
