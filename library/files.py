import os

import logging
log = logging.getLogger(__name__)


class Location(object):
    Dropbox = os.path.join(os.environ['HOME'], 'Dropbox')
    YandexDisk = os.path.join(os.environ['HOME'], 'Yandex.Disk.localized')


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
    # if os.path.isdir(dirname):
    if os.path.exists(location):
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', location])
        else:
            log.warn('Could not open location, only macOS is supported for now')
    else:
        raise RuntimeError('No location {!r}'.format(location))
