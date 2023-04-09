import subprocess
import time
from typing import List

import logging
log = logging.getLogger(__name__)


def now_ts():
    return time.time()


def run(command: List[str], cwd=None):
    str_command = ' '.join(command)
    start = now_ts()
    result = subprocess.run(command, capture_output=True, cwd=cwd)
    end = now_ts()
    delta = f'{end - start:.3f}'
    if result.returncode == 0:
        log.debug(f'Completed {str_command} in {delta} seconds')
    else:
        log.debug(f'Failed {str_command} in {delta} seconds')
        raise RuntimeError(f'Command failed with code {result.returncode}, command: {str_command!r}')
    return result
