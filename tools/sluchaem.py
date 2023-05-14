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


def parse_rows(rows: list):
    for row in rows:
        donation = row['donation']
        username = row['user_name']
        likes_line = '❤️' * row['likes_count']

        log.info(f'\t{donation}\t{username}\t{likes_line}')
        for child in row.get('children', []):
            child_name = child['user_name']
            child_body = child['body']
            log.info(f'\t\t{child_name}\t{child_body}')


def get_rows(resource_id: int) -> list:
    total_count = get_response(resource_id=resource_id, limit=1, offset=0)['meta']['total']
    log.info(f'Event https://sluchaem.ru/event/{resource_id} has {total_count} rows')
    limit = 20
    offset = 0
    rows = []
    while offset < total_count:
        log.debug(f'\tUsing offset {offset}')
        rows += get_response(resource_id=resource_id, limit=limit, offset=offset)['data']
        offset += limit
    log.info(f'Got {len(rows)} rows')
    assert len(rows) == total_count
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
