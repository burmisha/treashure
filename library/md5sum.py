import hashlib

import logging
log = logging.getLogger(__file__)


def Md5Sum(filename):
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(2 ** 16), b''):
            hash_md5.update(chunk)
    md5sum = hash_md5.hexdigest()
    log.debug(f'Md5sum of {md5sum!r} is {md5sum}')
    return md5sum
