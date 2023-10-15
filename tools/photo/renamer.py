import collections
import os

import library.files
import library.mover
import tools.photo.mobile

import logging
log = logging.getLogger(__name__)

NAME_FORMAT = '{dt:%Y-%m-%d %H-%M-%S}{suffix}.{extension}'


def file_is_ok(filename: str) -> bool:
    if 'Псевдоним _KOR1786.jpg' in filename:
        return False
    return True


def rename_dir(
    *,
    dirname: str,
    do_move: bool,
):
    photo_files = [
        tools.photo.mobile.PhotoFile(file)
        for file in library.files.walk(dirname, extensions=['JPG', 'jpg'])
        if file_is_ok(file)
    ]
    photo_files.sort()

    log.info(f'Checking {len(photo_files)} photo files in {dirname}')

    photo_files_by_timestamp = collections.defaultdict(list)
    for photo_file in photo_files:
        if photo_file.timestamp:
            photo_files_by_timestamp[photo_file.timestamp].append(photo_file)
        else:
            log.warn(f'No timestamp in file, skip: {photo_file.Path}')

    file_mover = library.mover.FileMover()
    for timestamp, photos in sorted(photo_files_by_timestamp.items()):
        if len(photos) >= 10:
            for photo in photos:
                log.info(f'{photo}')
            raise RuntimeError(f'Too many photos for one timestamp {timestamp}')

        add_index = len(photos) > 1
        photos.sort(key=lambda photo: photo.datetime)

        for index, photo in enumerate(photos, 1):
            basename = NAME_FORMAT.format(
                dt=photo.datetime,
                suffix=f'-{index}' if add_index else '',
                extension=photo.extension,
            )
            dst = os.path.join(os.path.dirname(photo.Path), basename)
            file_mover.add(photo.Path, dst)


    file_mover.get_src_dirnames()
    file_mover.get_dst_dirnames()

    for src, dst in file_mover.get_mv_files(with_log=True):
        if do_move:
            os.rename(src, dst)


def run_rename(args):
    rename_dir(
        dirname=args.dir,
        do_move=args.move,
    )


def populate_parser(parser):
    parser.add_argument('--dir', help='Dir to rename', required=True)
    parser.add_argument('--move', help='Do move', action='store_true')
    parser.set_defaults(func=run_rename)
