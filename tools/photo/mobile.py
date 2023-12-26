import json
import os

import library
import attr

import logging
log = logging.getLogger(__name__)


class Processor(object):
    def __init__(self):
        self.ParseExtensions = [ 'jpg', 'jpeg', 'png', 'dng' ]
        self.SkipExtensions = [
            'ds_store', 'ini', # ok
            'mp4', 'mov', 'nar', 'icon', 'gif', # TODO
        ]
        self.OpenedDir = False

    def __call__(self, filename):
        extension = os.path.basename(filename).split('.')[-1].lower().strip()
        photoFile = None
        if extension in self.ParseExtensions:
            return PhotoFile(filename)
        elif extension in self.SkipExtensions:
            log.debug(f'Skipping {filename}')
            return None
        else:
            log.error(f'Unknown file extension: {filename!r}: {extension!r}')
            if not self.OpenedDir:
                self.OpenedDir = True
                library.files.open_dir(filename)
            # raise RuntimeError()


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


def processDirs(args):
    photo_files = []
    processor = Processor()
    for filename in get_filenames(args.dir, args.file, args.skip):
        photo_file = processor(filename)
        if photo_file is not None:
            photo_files.append(photo_file)

    with open(args.json_file, 'w') as f:
        f.write(json.dumps(
            [attr.asdict(photo_file.photo_info) for photo_file in photo_files],
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        ))


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.add_argument('--dir', help='Add dir to parsing', action='append', default=[])
    parser.add_argument('--skip', help='Exclude paths from parsing', action='append', default=[])
    parser.add_argument('--file', help='Add file to parsing', action='append', default=[])
    parser.set_defaults(func=processDirs)
