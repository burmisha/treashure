import library.photo.photo_file
import library.files
import attr

import logging
log = logging.getLogger(__name__)

PARSE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'dng'}
SKIP_EXTENSIONS = {
    'ds_store', 'ini', # ok
    'mp4', 'mov', 'nar', 'icon', 'gif', # TODO
    'aae',
}


def process_dirs(args):
    photo_files = []
    for filename in library.files.get_filenames(
        dirs=args.dir,
        files=args.file,
        skip_paths=args.skip,
    ):
        extension = filename.split('.')[-1].lower()

        if extension in SKIP_EXTENSIONS:
            continue

        if extension not in PARSE_EXTENSIONS:
            library.files.open_dir(filename)
            raise RuntimeError(f'Unknown file extension: {filename!r}: {extension!r}')

        photo_files.append(library.photo.photo_file.PhotoFile(filename))

    data = [attr.asdict(photo_file.photo_info) for photo_file in photo_files]

    library.files.save_json(args.json_file, data)


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.add_argument('--dir', help='Add dir to parsing', action='append', default=[])
    parser.add_argument('--skip', help='Exclude paths from parsing', action='append', default=[])
    parser.add_argument('--file', help='Add file to parsing', action='append', default=[])
    parser.set_defaults(func=process_dirs)
