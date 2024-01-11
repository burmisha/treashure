from library.photo.photo_file import PhotoFile, PhotoInfo
from library.files import get_filenames, save_json, open_dir
import attr
import json

from tools.photo.deduplicate import Stats

import logging
log = logging.getLogger(__name__)

PARSE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'dng'}
SKIP_EXTENSIONS = {
    'ds_store', 'ini', # ok
    'mp4', 'mov', 'nar', 'icon', 'gif', # TODO
    'aae',
    'cr2',
    'heic',
}


def calculate(
    *,
    dirnames: list[str] = None,
    filenames: list[str] = None,
    skip_paths: list[str] = None,
    cached: bool = None,
    json_file: str = None,
):
    if not cached:
        photo_files = []
        for filename in get_filenames(
            dirs=dirnames,
            files=filenames,
            skip_paths=skip_paths,
        ):
            extension = filename.split('.')[-1].lower()

            if extension in SKIP_EXTENSIONS:
                continue

            if extension not in PARSE_EXTENSIONS:
                open_dir(filename)
                raise RuntimeError(f'Unknown file extension: {filename!r}: {extension!r}')

            photo_files.append(PhotoFile(filename))

        rows = [attr.asdict(photo_file.photo_info) for photo_file in photo_files]
        save_json(json_file, rows)

    with open(json_file) as f:
        photo_files_json = json.load(f)

    stats = Stats()
    for row in photo_files_json:
        stats.add_photo(PhotoInfo.from_dict(row))
    stats.process()


def run_calculate(args):
    calculate(
        dirnames=args.dir,
        filenames=args.file,
        skip_paths=args.skip,
        cached=args.cached,
        json_file=args.json_file,
    )


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.add_argument('--dir', help='Add dir to parsing', action='append', default=[])
    parser.add_argument('--skip', help='Exclude paths from parsing', action='append', default=[])
    parser.add_argument('--file', help='Add file to parsing', action='append', default=[])
    parser.add_argument('--cached', help='Use cached data file', action='store_true')
    parser.set_defaults(func=run_calculate)
