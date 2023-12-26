import re
import datetime
import pytz
from typing import Optional

import logging
log = logging.getLogger(__name__)


TIMESTAMP_RE = (
    r'('
    r'20\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r'([-_\.: ])?'
    r'\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r')'
)

TS_PREFIXES = [
    fr'^{TIMESTAMP_RE}[-_\.~ ]',
    fr'[a-zA-Z-_]{TIMESTAMP_RE}[-_\.~ ]',
    fr'^{TIMESTAMP_RE}\b',
    fr'[a-zA-Z-_]{TIMESTAMP_RE}\b',
]

MIN_OK_TIMESTAMP = 1100000000
MAX_OK_TIMESTAMP = 2000000000
SKIP_TIMESTAMP = 100000000


def parse_timestamp(basename: str) -> Optional[int]:
    for ts_re in TS_PREFIXES:
        res = re.search(ts_re, basename)
        if res:
            res = ''.join([l for l in res.group(1) if l.isdigit()])
            dt = datetime.datetime.strptime(res, '%Y%m%d%H%M%S')
            moscow_tz = pytz.timezone('Europe/Moscow')
            dt = moscow_tz.localize(dt).replace(tzinfo=None)
            timestamp = int(dt.timestamp())
            if MIN_OK_TIMESTAMP < timestamp < MAX_OK_TIMESTAMP:
                return timestamp
            elif timestamp < SKIP_TIMESTAMP:
                log.warn(f'Timestamp {timestamp} is too old, skippping')
                return None
            else:
                raise RuntimeError(f'Invalid timestamp {timestamp} from {basename!r}')

    if re.match(r'.*\d{4}.?\d{2}.?\d{2}.*\d{2}.?\d{2}.?\d{2}.*', basename):
        log.info(f'No dt in {basename}')

    return None
