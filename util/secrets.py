import json
import os

from library.files import Location


import logging
log = logging.getLogger(__name__)


class SecretsStorage:
    def __init__(self):
        filename = os.path.join(Location.YandexDisk, 'secrets.json')
        log.info(f'Loading secrets from {filename}')
        with open(filename) as f:
            self.__data = json.load(f)

    def get(self, key: str) -> str:
        value = self.__data[key]
        
        if len(value) <= 20:
            hidden = '*' * len(value)
        else:
            hidden = f'***...*** of len {len(value)}'
        log.warn(f'Secret for {key!r}: {hidden}')
        return value

SECRETS = SecretsStorage()
