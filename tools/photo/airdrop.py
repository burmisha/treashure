import datetime
import library
import logging
import collections
import os
import re
import shutil
from tools.photo.renamer import FileMover
from typing import Dict, List

log = logging.getLogger(__name__)

DOWNLOADS_DIR = os.path.join(os.environ['HOME'], 'Downloads')


def name_remap(filename: str) -> str:
    dirname = os.path.basename(os.path.dirname(filename))
    basename = os.path.basename(filename)
    
    basename_index_matches = re.match(r'^IMG_([EO])(\d{4}).(\w\w\w)$', basename)
    if basename_index_matches:
        index = basename_index_matches.group(2) 
        extension = basename_index_matches.group(3) 
        dir_index_matches = re.match(r'^IMG_(\d{4})( 2)?$', dirname)
        if dir_index_matches and (dir_index_matches.group(1) != index):
            raise RuntimeError(f'Very strange name: {filename}')

        return f'IMG_{index}_edited.{extension.upper()}'

    return basename


def assert_equals(value, canonic):
    if value != canonic:
        raise AssertionError(f'Expected: {canonic!r}, got {value!r}')


def test_name_remap():
    assert_equals(name_remap('/Downloads/IMG_5666/IMG_E5666.mov'), 'IMG_5666_edited.MOV')
    assert_equals(name_remap('/Downloads/IMG_5666/IMG_5666.mov'), 'IMG_5666.mov')
    assert_equals(name_remap('/Downloads/IMG_7404/IMG_7404.AAE'), 'IMG_7404.AAE')
    assert_equals(name_remap('/Downloads/IMG_7404/IMG_7404.JPG'), 'IMG_7404.JPG')
    assert_equals(name_remap('/Downloads/IMG_7404/IMG_E7404.jpg'), 'IMG_7404_edited.JPG')
    assert_equals(name_remap('/Downloads/IMG_7404/IMG_O7404.AAE'), 'IMG_7404_edited.AAE')
    assert_equals(name_remap('/Downloads/FEAC8BBA-7A25-409F-8E6F-715FE57ADA8B/IMG_0967.JPG'), 'IMG_0967.JPG')
    assert_equals(name_remap('/Downloads/RPReplay_Final1627725283/IMG_1234.MP4'), 'IMG_1234.MP4')
    assert_equals(name_remap('/Downloads/IMG_0123 2/IMG_E0123.jpg'), 'IMG_0123_edited.JPG')
    assert_equals(name_remap('/Downloads/FullSizeRender/IMG_0123.jpg'), 'IMG_0123.jpg')
    assert_equals(name_remap('/Downloads/FullSizeRender/IMG_E0123.jpg'), 'IMG_0123_edited.JPG')
    assert_equals(name_remap('/Downloads/FullSizeRender 2/IMG_0123.jpg'), 'IMG_0123.jpg')


test_name_remap()


def get_img_dirs(base_dir: str, regexp: str) -> List[str]:
    img_dirs_re = re.compile(regexp)
    dirs = [
        dirname
        for dirname in os.listdir(base_dir)
        if img_dirs_re.match(dirname)
    ]
    dirs.sort()
    if dirs:
        log.info(f'Got {len(dirs)} photo dirs in {base_dir} by {regexp}: [ {dirs[0]} ... {dirs[-1]} ]')
    else:
        log.warn(f'No dirs in {base_dir} by regexp {regexp}')
    return [os.path.join(base_dir, dirname) for dirname in dirs]


def get_photo_files(photo_dirs: List[str]) -> List[str]:
    all_photo_files = []
    for photo_dir in photo_dirs:
        photo_files = list(library.files.walk(photo_dir))
        photo_files.sort()
        if len(photo_files) <= 0:
            raise RuntimeError(f'Empty dir, very strange: {photo_dir}')
        elif len(photo_files) == 1:
            log.debug('ok')
        else:
            log.info(f'Dir {photo_dir} has {len(photo_files)} files:')
            for photo_file in photo_files:
                log.info(f'\tfile: {photo_file}')

        all_photo_files += photo_files

    all_photo_files.sort()

    if not all_photo_files:
        log.warn(f'No files to import in {len(photo_dirs)} dirs')
        return []

    extensions = set(photo_file.split('.')[-1] for photo_file in all_photo_files)
    if len(all_photo_files) > 1:
        log.info(f'Got {len(all_photo_files)} files of extensions {extensions}: [ {all_photo_files[0]} ... {all_photo_files[-1]} ]')
    else:
        log.info(f'Got 1 file of extension {extensions}: {all_photo_files[0]}')
    return all_photo_files


def get_dst_dir(base_dir: str) -> str:
    dst_dir = os.path.join(base_dir, f'import_{datetime.datetime.now():%Y-%m-%dT%H-%M-%S}')
    log.info(f'Moving files to {dst_dir} ...')

    if os.path.exists(dst_dir):
        raise RuntimeError(f'Dir already exists: {dst_dir!r}')

    return dst_dir


def import_airdrop(
    *,
    base_dir: str,
    regexp: str,
    do_move: bool,
):
    log.info(f'Importing in {base_dir} by {regexp} ...')
    photo_dirs = get_img_dirs(base_dir, regexp)
    photo_files = get_photo_files(photo_dirs)
    dst_dir = get_dst_dir(base_dir)

    mover = FileMover()
    for photo_file in photo_files:
        mover.add(
            photo_file,
            os.path.join(dst_dir, name_remap(photo_file)),
        )

    if do_move:
        if mover.has_dst_files:
            os.mkdir(dst_dir)

        for src, dst in mover.get_src_dst():
            os.rename(src, dst)

        if any(list(library.files.walk(photo_dir)) for photo_dir in photo_dirs):
            raise RuntimeError(f'Dir is not empty yet: {photo_dir!r}')

        for photo_dir in photo_dirs:
            os.rmdir(photo_dir)
    else:
        for src, dst in mover.get_src_dst():
            pass


def get_dirs_by_index(base_dir, dir_index_re: str) -> Dict[str, str]:
    result = dict()
    for img_dir in get_img_dirs(base_dir, dir_index_re):
        match = re.match(dir_index_re, os.path.basename(img_dir))
        index = match.group(1)
        assert int(index)
        assert index not in result
        result[index] = img_dir

    return result
        


def deduplicate(base_dir: str, do_depuplicate: bool):
    log.info(f'Deduplicating in {base_dir} ...')
    original_dirs = get_dirs_by_index(base_dir, r'^IMG_(\d{4})$')
    copy_dirs = get_dirs_by_index(base_dir, r'^IMG_(\d{4}) 2$')

    dirs_to_delete = []
    for index, copy_dir in sorted(copy_dirs.items()):
        if not index in original_dirs:
            continue
        original_dir = original_dirs[index]
        original_files = get_photo_files([original_dir])
        if len(original_files) != 1:
            raise RuntimeError(f'Strange {index} and {copy_dir}') 
        original_file = original_files[0]
        copy_file = os.path.join(copy_dir, os.path.basename(original_file))
        if library.md5sum.Md5Sum(original_file) != library.md5sum.Md5Sum(copy_file):
            raise RuntimeError(f'Strange {index} and {copy_dir}') 
        else:
            log.info(f'Could drop {original_dir} as {original_file} and {copy_file} are the same')
        dirs_to_delete.append(original_dir)

    if do_depuplicate:
        for dir_to_delete in dirs_to_delete:
            log.info(f'Delete {dir_to_delete}')
            shutil.rmtree(dir_to_delete)


def run_import_airdrop(args):
    deduplicate(
        base_dir=args.dir_name,
        do_depuplicate=args.deduplicate,
    )
    import_airdrop(
        base_dir=args.dir_name,
        regexp = r'^(IMG_\d{4}( 2)?|RPReplay_Final\d{10}|FullSizeRender( \d)?)$',
        do_move=args.move,
    )
    import_airdrop(
        base_dir=args.dir_name,
        regexp='^' + '-'.join([f'[0-9A-F]{{{x}}}' for x in [8, 4, 4, 4, 12]]) + '$',
        do_move=args.move,
    )


def populate_parser(parser):
    parser.add_argument('--dir-name', help='Dir to use', default=DOWNLOADS_DIR)
    parser.add_argument('--move', help='Do move', action='store_true')
    parser.add_argument('--deduplicate', help='Do deduplicate', action='store_true')
    parser.set_defaults(func=run_import_airdrop)
