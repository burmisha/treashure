import requests
from dataclasses import dataclass, field

from util.secrets import SECRETS

import logging
log = logging.getLogger(__name__)


XSRF_TOKEN = SECRETS.get('nuzhnapomosh.xsrf')
NP_ACCESS = SECRETS.get('nuzhnapomosh.np_access')


@dataclass
class Donation:
    donation_id: int
    sum: int
    date: str
    status: str
    status_name: str

    @property
    def short_description(self) -> str:
        return f'{self.date}\t{self.sum:4d}\t{self.status}'


@dataclass
class Fund:
    name: str
    url: str
    is_active: bool
    donations: list[Donation] = field(default_factory=list)

    @property
    def successful_donations(self) -> list[Donation]:
        return [d for d in self.donations if d.status == 'success']

    @property
    def total_sum(self) -> int:
        return sum(d.sum for d in self.successful_donations)

    @property
    def short_description(self) -> str:
        prefix = '✅' if self.is_active else '❌'
        return f'{prefix} {self.name:40}\t{self.total_sum:6d} ({len(self.successful_donations)})\t{self.url}'


def get_response(*, limit: int, offset: int, is_active: bool):
    assert 1 <= limit <= 20
    url = 'https://my.nuzhnapomosh.ru/api/v1/subscriptions/load'

    active = 'true' if is_active else 'false'
    data = f'offset={offset}&limit={limit}&name=&currency=rub&active={active}&card_id=&bundles=0'

    headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'cookie': f'np_access={NP_ACCESS}; XSRF-TOKEN={XSRF_TOKEN}',
    }

    response = requests.post(url, data=data, headers=headers)
    assert response.status_code == 200

    return response.json()


def get_rows(is_active: bool) -> list:
    limit = 20
    offset = 0
    total_count = None

    rows = []
    while (total_count is None) or (len(rows) < total_count):
        response = get_response(limit=limit, offset=offset, is_active=is_active)
        total_count = response['count']
        if offset == 0:
            log.info(f'Getting {total_count} donations, requesting by {limit}')
        rows += response['data']
        offset += limit

    if len(rows) != total_count:
        raise ValueError(f'Expected {total_count} rows, got {len(rows)}')

    return rows


def get_funds():
    for is_active in [
        True,
        False,
    ]:
        rows = get_rows(is_active=is_active)
        for row in rows:
            donations = [
                Donation(
                    donation_id=d['id'],
                    sum=d['sum'],
                    date=d['date'],
                    status=d['status'],
                    status_name=d['status_name'],
                ) for d in row['donations']
            ]
            yield Fund(
                name=row['case']['name'],
                url=row['case']['url'],
                is_active=is_active,
                donations=donations,
            )

            # del row['donations']
            # for k, v in row.items():
            #     print(k, v)


def download_donations():
    funds = list(get_funds())

    for fund in funds:
        log.info(f'{fund.short_description}')
        for donation in fund.donations:
            log.info(f'\t{donation.short_description}')

    total_count = sum(len(f.successful_donations) for f in funds)
    total_sum = sum(f.total_sum for f in funds)
    log.info(f'Total: {total_sum} ({total_count})')


def run_donations(args):
    download_donations()


def populate_parser(parser):
    parser.set_defaults(func=run_donations)
