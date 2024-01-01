import collections
import json

from typing import DefaultDict, List

from library.photo.photo_file import PhotoInfo

import logging
log = logging.getLogger(__name__)


def run_deduplicate(args):
    json_file = args.json_file
    with open(json_file) as f:
        photo_files_json = json.load(f)

    photos_by_md5sum: DefaultDict[str, List[PhotoInfo]] = collections.defaultdict(list)
    for row in photo_files_json:
        photo = PhotoInfo.from_dict(row)
        photos_by_md5sum[photo.md5sum].append(photo)

    collisions_count = 0
    for md5sum, photos in photos_by_md5sum.items():
        if len(photos) > 1:
            names = '\n  '.join(photo.path for photo in photos)
            log.info(f'Duplicates: {md5sum}\n  {names}')
            collisions_count += 1
    
    if collisions_count:
        log.info(f'Found {collisions_count} duplicates {json_file!r}')
    else:
        log.info(f'No duplicates were found in {json_file!r}')


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.set_defaults(func=run_deduplicate)
