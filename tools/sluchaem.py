import requests

import logging
log = logging.getLogger(__name__)


def get_response(*, resource_id: int, limit: int, offset: int):
    assert 1 <= limit <= 20
    url = 'https://api.sluchaem.ru/api/v2/comments'
    params = {
        'project': 'ps',
        'resource_type': 'collection',
        'resource_id': resource_id,
        'parent_only': '1',
        'limit': limit,
        'offset': offset,
        'children_limit': '2',
    }
    response = requests.get(url, params=params)
    assert response.status_code == 200
    return response.json()


class ResultLine:
    def __init__(self, *, donation = None, username = None, likes_count = None, children = None):
        self.donation = donation
        self.username = username
        self.likes_count = likes_count
        self.children = children
    
    def __str__(self):
        likes_line = '❤️' * self.likes_count
        msg = f'\t{self.donation}\t{self.username}\t{likes_line}'
        for child in self.children:
            child_name = child['user_name']
            child_body = child['body']
            msg += f'\n\t\t{child_name}\t{child_body}'
        
        return msg


def parse_rows(rows: list):
    for row in rows[:3]:
        print(row)
        result_line = ResultLine(
            donation=row['donation'],
            username=row['user_name'],
            likes_count=row['likes_count'],
            children=row.get('children') or [],
        )
        log.info(f'{result_line}')


def get_rows(resource_id: int) -> list:
    limit = 20
    offset = 0
    total_count = None

    rows = []
    while (total_count is None) or (len(rows) < total_count):
        response = get_response(resource_id=resource_id, limit=limit, offset=offset)
        total_count = response['meta']['total']
        if offset == 0:
            log.info(f'Event https://sluchaem.ru/event/{resource_id} has {total_count} rows, requesting by {limit}')
        rows += response['data']
        offset += limit

    if len(rows) != total_count:
        raise ValueError(f'Expected {total_count} rows, got {len(rows)}')

    return rows


def download_sluchaem(resource_id: int):
    rows = get_rows(resource_id)
    parse_rows(rows)


def run_sluchaem(args):
    for resource_id in args.resource:
        download_sluchaem(
            resource_id=resource_id,
        )


def populate_parser(parser):
    parser.add_argument('-r', '--resource', help='Resource id', required=True, type=int, action='append', default=[])
    parser.set_defaults(func=run_sluchaem)
