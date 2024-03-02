from dataclasses import dataclass, field
import os
import requests

from library.files import Location
from util.cache import Cache
from util.secrets import SECRETS

import logging
log = logging.getLogger(__name__)

CACHE = Cache(os.path.join(Location.YandexDisk, 'cache.json'))


@dataclass
class JsonJoiner:
    url: str
    method: str
    post_suffix: str = ''
    get_update: dict = field(default_factory=dict)
    limit: int = 20

    def _get_total_count(self, response) -> int:
        if self.method == 'post':
            return response['count']  
        else:
            return response['meta']['total']

    def _make_one_request(self, *, offset: int):
        if self.method == 'post':
            data = f'offset={offset}&limit={self.limit}{self.post_suffix}'
            key = f'POST__{self.url}__{data}'
        else:
            params = {
                'limit': self.limit,
                'offset': offset,
            }
            params.update(self.get_update)
            key = f'POST__{self.url}__{params}'

        result = CACHE.get(key)

        if result is None:
            if self.method == 'post':
                XSRF_TOKEN = SECRETS.get('nuzhnapomosh.xsrf')
                NP_ACCESS = SECRETS.get('nuzhnapomosh.np_access')
                headers = {
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'cookie': f'np_access={NP_ACCESS}; XSRF-TOKEN={XSRF_TOKEN}',
                }
                response = requests.post(self.url, data=data, headers=headers)
            else:
                response = requests.get(self.url, params=params)
            assert response.status_code == 200
            result = response.json()
            CACHE.set(key, result)

        return result

    def get_data(self) -> list[dict]:
        assert 1 <= self.limit <= 20

        offset = 0
        total_count = None

        rows = []
        while (total_count is None) or (len(rows) < total_count):
            response = self._make_one_request(offset=offset)
            total_count = self._get_total_count(response)

            if offset == 0:
                log.info(f'Getting {total_count} rows at {self.url!r}, requesting by {self.limit}')

            offset += self.limit
            rows.extend(response['data'])

        if len(rows) != total_count:
            raise ValueError(f'Expected {total_count} rows, got {len(rows)}')

        return rows
