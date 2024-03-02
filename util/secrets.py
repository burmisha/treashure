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

    def __hide(self, value: str) -> str:
        if len(value) <= 20:
            return '*' * len(value)
        else:
            return f'***...*** of len {len(value)}'

    @classmethod
    def from_file(cls, filename: str):
        log.info(f'Loading secrets from {filename}')
        with open(filename) as f:
            data = json.load(f)
            return cls(filename=filename, data=data)

    def get(self, key: str) -> str:
        value = self.data[key]
        log.warn(f'Secret for {key!r}: {self.__hide(value)}')
        return value


SECRETS = SecretsStorage(os.path.join(Location.YandexDisk, 'secrets.json'))
