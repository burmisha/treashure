from collections import defaultdict
from dataclasses import dataclass, field

from tools.charity.joiner import JsonJoiner, Method

from typing import Iterable

import logging
log = logging.getLogger(__name__)


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
        return [
            d for d in self.donations
            if d.status == 'success'
        ]

    @property
    def total_sum(self) -> int:
        return sum(d.sum for d in self.successful_donations)

    @property
    def short_description(self) -> str:
        prefix = '✅' if self.is_active else '❌'
        return f'{prefix} {self.name:40}\t{self.total_sum:6d} ({len(self.successful_donations)})\t{self.url}'


def get_regular_funds(*, is_active: bool) -> Iterable[Fund]:
    active = 'true' if is_active else 'false'
    joiner = JsonJoiner(
        url='https://my.nuzhnapomosh.ru/api/v1/subscriptions/load',
        method=Method.POST,
        post_suffix=f'&name=&currency=rub&active={active}&card_id=&bundles=0'
    )

    for row in joiner.get_data():
        donations = [
            Donation(
                donation_id=donation['id'],
                sum=donation['sum'],
                date=donation['date'],
                status=donation['status'],
                status_name=donation['status_name'],
            ) for donation in row['donations']
        ]
        yield Fund(
            name=row['case']['name'],
            url=row['case']['url'],
            is_active=is_active,
            donations=donations,
        )


def get_single_funds() -> Iterable[Fund]:
    joiner = JsonJoiner(
        url='https://my.nuzhnapomosh.ru/api/v1/payments/load',
        method=Method.POST,
        post_suffix=f'&filter=all&type=1&only_signup=false&search=',
    )

    for row in joiner.get_data():
        donation = Donation(
            donation_id=row['id'],
            sum=row['sum'],
            date=row['date'],
            status=row['status'],
            status_name=row['status_title'],
        )
        yield Fund(
            name=row['case_name'],
            url=row['case_url'],
            is_active=row['is_paid'],
            donations=[donation],
        )


def group_funds(funds: list[Fund]) -> list[Fund]:
    result: dict[str, Fund] = {}
    for fund in funds:
        if fund.name in result:
            result[fund.name].donations.extend(fund.donations)
        else:
            result[fund.name] = fund

    return list(result.values())


def get_funds(
    with_regular: bool=False,
    with_single: bool=True,
):
    funds = []
    if with_regular:
        funds.extend(list(get_regular_funds(is_active=True)))
        funds.extend(list(get_regular_funds(is_active=False)))
    if with_single:
        funds.extend(group_funds(list(get_single_funds())))

    for fund in funds:
        log.info(f'{fund.short_description}')
        for donation in fund.donations:
            log.info(f'\t{donation.short_description}')

    total_count = sum(len(f.successful_donations) for f in funds)
    total_sum = sum(f.total_sum for f in funds)
    log.info(f'Total: {total_sum} ({total_count})')


def run_donations(args):
    get_funds(
        with_regular=args.with_regular,
        with_single=args.with_single,
    )


def populate_parser(parser):
    parser.set_defaults(func=run_donations)
    parser.add_argument('-r', '--with-regular', help='Get regular donations', action='store_true')
    parser.add_argument('-s', '--with-single', help='Get single donations', action='store_true')
