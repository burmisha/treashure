from typing import Optional

import json
import os

import library
import attr

import logging
log = logging.getLogger(__name__)

PARSE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'dng'}
SKIP_EXTENSIONS = {
    'ds_store', 'ini', # ok
    'mp4', 'mov', 'nar', 'icon', 'gif', # TODO
    'aae',
}


def to_photo_file(filename) -> Optional[library.photo.photo_file.PhotoFile]:
    extension = os.path.basename(filename).split('.')[-1].lower().strip()
    if extension in PARSE_EXTENSIONS:
        return library.photo.photo_file.PhotoFile(filename)
    elif extension in SKIP_EXTENSIONS:
        log.debug(f'Skipping {filename}')
        return None
    else:
        log.error(f'Unknown file extension: {filename!r}: {extension!r}')
        library.files.open_dir(filename)
        raise RuntimeError('Unknown file extension')


def get_filenames(dirs, files, skip_paths):
    filenames_count = 0

    for filename in files:
        filenames_count += 1
        yield filename

    for dir_name in dirs:
        for root, _, files in os.walk(dir_name):
            if any(path in root for path in skip_paths):
                log.info(f'{root} is excluded')
                continue
            files = sorted(list(files))
            log.info(f'Found {len(files)} files in {root}')
            for filename in files:
                filenames_count += 1
                yield os.path.join(root, filename)
                if filenames_count % 500 == 0:
                    log.info(f'Yielded {filenames_count} photo files')

    log.info(f'Yielded {filenames_count} photo files')


def process_dirs(args):
    photo_files = [
        to_photo_file(filename)
        for filename in get_filenames(args.dir, args.file, args.skip)
    ]

    data = [attr.asdict(photo_file.photo_info) for photo_file in photo_files if photo_file]

    with open(args.json_file, 'w') as f:
        f.write(json.dumps(
            data,
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        ))


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.add_argument('--dir', help='Add dir to parsing', action='append', default=[])
    parser.add_argument('--skip', help='Exclude paths from parsing', action='append', default=[])
    parser.add_argument('--file', help='Add file to parsing', action='append', default=[])
    parser.set_defaults(func=process_dirs)
