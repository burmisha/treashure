from dataclasses import dataclass, field

from tools.charity.joiner import JsonJoiner

import logging
log = logging.getLogger(__name__)


@dataclass
class ResultLine:
    donation: str
    username: str
    likes_count: int
    children: list = field(default_factory=list)
    
    @property
    def description(self) -> str:
        likes_line = '❤️' * self.likes_count
        msg = f'\t{self.donation}\t{self.username}\t{likes_line}'
        for child in self.children:
            child_name = child['user_name']
            child_body = child['body']
            msg += f'\n\t\t{child_name}\t{child_body}'
        
        return msg


def download_sluchaem(resource_id: int) -> list[ResultLine]:
    joiner = JsonJoiner(
        url='https://api.sluchaem.ru/api/v2/comments',
        method='get',
        get_update={
            'project': 'ps',
            'resource_type': 'collection',
            'resource_id': resource_id,
            'parent_only': '1',
            'children_limit': '2',
        },
    )
    rows = joiner.get_data()

    return [
        ResultLine(
            donation=row['donation'],
            username=row['user_name'],
            likes_count=row['likes_count'],
            children=row.get('children') or [],
        ) for row in rows
    ]


def run_sluchaem(args):
    for resource_id in args.resource:
        results = download_sluchaem(
            resource_id=resource_id,
        )
        log.info(f'Event https://sluchaem.ru/event/{resource_id} has {len(results)} entries')
        for result_line in results:
            log.info(result_line.description)


def populate_parser(parser):
    parser.add_argument('-r', '--resource', help='Resource id', required=True, type=int, action='append', default=[])
    parser.set_defaults(func=run_sluchaem)
