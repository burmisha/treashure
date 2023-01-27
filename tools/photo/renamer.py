import library
import tools
import logging
import collections
import os

from typing import List, Dict

log = logging.getLogger(__name__)

NAME_FORMAT = '{dt:%Y-%m-%d %H-%M-%S}{suffix}.{extension}'


class FileMover:
    def __init__(self):
        self._move_list = []
        self._src_set = set()
        self._dst_set = set()

    def add(self, src, dst):
        if src == dst:
            log.debug(f'Same location, skip: {src!r}')
            return

        if src in self._src_set:
            raise RuntimeError(f'Duplicated move src: {src!r}')
        if dst in self._dst_set:
            raise RuntimeError(f'Duplicated move dst: {dst!r}')
        if os.path.exists(dst):
            raise RuntimeError(f'Dst already exists: {dst!r}')

        self._move_list.append((src, dst))
        self._src_set.add(src)
        self._dst_set.add(dst)

    def get_src_dst(self):
        log.info(f'Got {len(self._move_list)} files to move')
        for src, dst in self._move_list:
            log.info(f'mv {src!r} {dst!r}')
            yield src, dst

    def get_src_dirnames(self) -> Dict[str, List[str]]:
        dirnames = collections.defaultdict(list)
        for src, _ in self._move_list:
            dirname = os.path.dirname(src)
            dirnames[dirname].append(src)
        return dirnames


def file_is_ok(filename: str) -> bool:
    if 'Псевдоним _KOR1786.jpg' in filename:
        return False
    return True


def rename_dir(
    *,
    dir_name: str,
    move: bool=False,
):
    photo_files = [
        tools.photo.mobile.PhotoFile(file)
        for file in library.files.walk(dir_name, extensions=['JPG', 'jpg'])
        if file_is_ok(file)
    ]
    photo_files.sort()

    log.warn(f'Checking {len(photo_files)} photo files in {dir_name}')

    photos_by_ts = collections.defaultdict(list)
    for photo in photo_files:
        if photo.timestamp:
            photos_by_ts[photo.timestamp].append(photo)
        else:
            log.warn(f'No ts in file, skip: {photo.Path}')

    mover = FileMover()
    for timestamp, photos in sorted(photos_by_ts.items()):
        add_index = len(photos) > 1
        photos.sort(key=lambda photo: photo.datetime)

        for index, photo in enumerate(photos, 1):
            dst_basename = NAME_FORMAT.format(
                dt=photo.datetime,
                suffix=f'-{index}' if add_index else '',
                extension=photo.extension,
            )
            dst_file = os.path.join(os.path.dirname(photo.Path), dst_basename)
            mover.add(photo.Path, dst_file)

    for src, dst in mover.get_src_dst():
        if move:
            os.rename(src, dst)

    for dirname, files in mover.get_src_dirnames().items():
        log.info(f'Dir {dirname} has {len(files)} files: {os.path.basename(files[0])} .. {os.path.basename(files[-1])}')


def run_rename(args):
    rename_dir(
        dir_name=args.dir,
        move=args.move,
    )


def populate_parser(parser):
    parser.add_argument('--dir', help='Add dir to rename', required=True)
    parser.add_argument('--move', help='Do move', action='store_true')
    parser.set_defaults(func=run_rename)
