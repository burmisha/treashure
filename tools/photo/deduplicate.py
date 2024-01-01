import collections
import json
import os

from typing import DefaultDict, List, Dict, Tuple

from library.photo.photo_file import PhotoInfo

import logging
log = logging.getLogger(__name__)


SHARE = 0.7
TOTAL = 10


class Stats:
    def __init__(self):
        self.photos_by_path: Dict[str, PhotoInfo] = {}
        self.photos_by_md5sum: DefaultDict[str, List[PhotoInfo]] = collections.defaultdict(list)
        self.file_counters = collections.defaultdict(int)
        self.collision_counters = collections.defaultdict(int)
        self.matched_dirs: DefaultDict[Tuple[str, str], int] = collections.defaultdict(int)

    def add_photo(self, photo_info: PhotoInfo):
        if photo_info.path in self.photos_by_path:
            raise RuntimeError()

        self.photos_by_path[photo_info.path] = photo_info

        dir_name = os.path.dirname(photo_info.path)
        self.file_counters[dir_name] += 1

        has_collisions = False
        for same_photo in self.photos_by_md5sum[photo_info.md5sum]:
            d_name = os.path.dirname(same_photo.path)
            self.collision_counters[d_name] += 1
            has_collisions = True
            if dir_name < d_name:
                key = (dir_name, d_name)
            else:
                key = (d_name, dir_name)
            self.matched_dirs[key] += 1

        self.photos_by_md5sum[photo_info.md5sum].append(photo_info)
        if has_collisions:
            self.collision_counters[dir_name] += 1

    def process(self):
        for (first_dir, second_dir), matches in self.matched_dirs.items():
            first_count = self.file_counters[first_dir]
            second_count = self.file_counters[second_dir]
            first_share = matches / first_count
            second_share = matches / second_count
            if (first_share >= SHARE or second_share >= SHARE or matches >= TOTAL):
                log.info(f'Found almost the same dirs')
                log.info(f'First:  {first_dir}, share: {first_share}: {matches} of {first_count}')
                log.info(f'Second: {second_dir}, share: {second_share}: {matches} of {second_count}')


        # collisions_count = 0
        # for md5sum, photos in self.photos_by_md5sum.items():
        #     if len(photos) > 1:
        #         names = '\n  '.join(photo.path for photo in photos)
        #         log.info(f'Duplicates: {md5sum}\n  {names}')
        #         collisions_count += 1

        # if collisions_count:
        #     log.info(f'Found {collisions_count} duplicates')
        # else:
        #     log.info(f'No duplicates were found')


def run_deduplicate(args):
    json_file = args.json_file
    log.info(f'Reading {json_file!r}')
    with open(json_file) as f:
        photo_files_json = json.load(f)

    stats = Stats()
    for row in photo_files_json:
        stats.add_photo(PhotoInfo.from_dict(row))
    stats.process()


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.set_defaults(func=run_deduplicate)
