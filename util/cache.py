import os
import json

from typing import Any

from dataclasses import dataclass, field


import logging
log = logging.getLogger(__name__)


@dataclass
class Cache:
    filename: str
    data: dict[str, Any] = field(default_factory=dict)

    def _load(self):
        if not os.path.exists(self.filename):
            log.warn(f'Creating cache: {self.filename!r}')
            self._save()

        with open(self.filename) as f:
            self.__data = json.load(f)

    def _save(self):
        with open(self.filename, 'w') as f:
            f.write(json.dumps(
                self.__data,
                indent=4,
                sort_keys=True,
                ensure_ascii=False,
            ))

    def set(self, key: str, value):
        self.__data[key] = value
        self._save()
    
    def get(self, key: str):
        self._load()
        return self.__data.get(key)
        