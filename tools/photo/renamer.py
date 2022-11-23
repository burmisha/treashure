import library
import tools
import logging
import collections
log = logging.getLogger(__file__)
import os


NAME_FORMAT = '{dt:%Y-%m-%d %H-%M-%S}{suffix}.{extension}'


class FileMover:
    def __init__(self):
        self.move_list = []
        self.src_set = set()
        self.dst_set = set()

    def add(self, src, dst):
        if src == dst:
            log.info(f'Same location, skip: {src!r}')
            return

        if src in self.src_set:
            raise RuntimeError(f'Duplicated move from: {src!r}')
        if dst in self.dst_set:
            raise RuntimeError(f'Duplicated move to: {dst!r}')
        if os.path.exists(dst):
            raise RuntimeError(f'Dst already exists: {dst!r}')

        self.move_list.append((src, dst))
        self.src_set.add(src)
        self.dst_set.add(dst)

    def move(self):
        for src, dst in self.move_list:
            log.info(f'mv {src!r} {dst!r}')
            os.rename(src, dst)

    def __len__(self):
        return len(self.move_list)


def rename_dir(
    *,
    dir_name: str,
    move: bool=False
):
    photo_files = [
        tools.mobile.mobile.PhotoFile(file)
        for file in library.files.walk(dir_name, extensions=['JPG', 'jpg'])
    ]

    photos_by_ts = collections.defaultdict(list)
    ok_count = 0
    for photo in photo_files:
        if len(photo.timestamps) == 1 and photo.is_vsco:
            timestamp = photo.timestamps[0]
            photos_by_ts[timestamp].append(photo)
            ok_count += 1
        else:
            log.warn(f'Skipping {photo}: {photo.timestamps}')

    mover = FileMover()
    for timestamp, photos in sorted(photos_by_ts.items()):
        add_index = len(photos) > 1
        photos.sort(key=lambda photo: photo.datetimes[0])

        for index, photo in enumerate(photos, 1):
            dst_basename = NAME_FORMAT.format(
                dt=photo.datetimes[0],
                suffix=f'-{index}' if add_index else '',
                extension=photo.Basename.split('.')[-1],
            )
            dst_file = os.path.join(os.path.dirname(photo.Path), dst_basename)
            mover.add(photo.Path, dst_file)

    log.info(f'Got {len(mover)} files to move')

    if move:
        mover.move()
    else:
        for src, dst in mover.move_list:
            log.info(f'will move {src!r} {dst!r}')


def run_rename(args):
    rename_dir(
        dir_name=args.dir,
        move=args.move,
    )


def populate_parser(parser):
    parser.add_argument('--dir', help='Add dir to rename', required=True)
    parser.add_argument('--move', help='Do move', action='store_true')
    parser.set_defaults(func=run_rename)
