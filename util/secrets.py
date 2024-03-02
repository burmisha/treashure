from dataclasses import dataclass, field
import json
import os

from typing import Any

from library.files import Location


import logging
log = logging.getLogger(__name__)

@dataclass
class SecretsStorage:
    filename: str
    data: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_file(cls, filename: str):
        log.info(f'Loading secrets from {filename}')
        with open(filename) as f:
            data = json.load(f)
            return cls(filename=filename, data=data)

    def get(self, key: str) -> str:
        value = self.__data[key]
        
        if len(value) <= 20:
            hidden = '*' * len(value)
        else:
            hidden = f'***...*** of len {len(value)}'
        log.warn(f'Secret for {key!r}: {hidden}')
        return value

SECRETS = SecretsStorage(os.path.join(Location.YandexDisk, 'secrets.json'))
