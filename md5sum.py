import os
import hashlib
import platform
import subprocess

import logging
log = logging.getLogger(__file__)

def Md5Sum(filename):
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(2 ** 16), b''):
            hash_md5.update(chunk)
    md5sum = hash_md5.hexdigest()
    log.info('Md5sum of {!r} is {}'.format(filename, md5sum))
    return md5sum


def openDir(location):
    # if os.path.isdir(dirname):
    if os.path.exists(location):
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', location])
        else:
            log.warn('Could not open location, only OS X is supported')
    else:
        raise RuntimeError('No location {!r}'.format(location))
