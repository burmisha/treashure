import collections
import datetime
import os
import re

import library.files
import library.mover

from tools.photo.mobile import PhotoFile

from typing import Dict, List

import logging
log = logging.getLogger(__name__)


VSCO_RE = '-'.join([f'[0-9A-F]{{{x}}}' for x in [8, 4, 4, 4, 12]])
REGEXPS = [
    r'IMG_\d{4}( [23456])?',
    r'RPReplay_Final\d{10}( \d)?',
    r'FullSizeRender( \d+)?',
    r'camphoto_\d+( \d)?',
    r'Image',
    VSCO_RE,
    fr'{VSCO_RE} \d{{4}}-\d{{2}}-\d{{2}} at \d{{2}}\.\d{{2}}\.\d{{2}}',  # is not vsco
]


def rename(filename: str) -> str:
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


def test_rename():
    assert_equals(rename('/any_prefix/IMG_5666/IMG_E5666.mov'), 'IMG_5666_edited.MOV')
    assert_equals(rename('/any_prefix/IMG_5666/IMG_5666.mov'), 'IMG_5666.mov')
    assert_equals(rename('/any_prefix/IMG_7404/IMG_7404.AAE'), 'IMG_7404.AAE')
    assert_equals(rename('/any_prefix/IMG_7404/IMG_7404.JPG'), 'IMG_7404.JPG')
    assert_equals(rename('/any_prefix/IMG_7404/IMG_E7404.jpg'), 'IMG_7404_edited.JPG')
    assert_equals(rename('/any_prefix/IMG_7404/IMG_O7404.AAE'), 'IMG_7404_edited.AAE')
    assert_equals(rename('/any_prefix/FEAC8BBA-7A25-409F-8E6F-715FE57ADA8B/IMG_0967.JPG'), 'IMG_0967.JPG')
    assert_equals(rename('/any_prefix/RPReplay_Final1627725283/IMG_1234.MP4'), 'IMG_1234.MP4')
    assert_equals(rename('/any_prefix/RPReplay_Final1627725283 2/IMG_1234.MP4'), 'IMG_1234.MP4')
    assert_equals(rename('/any_prefix/IMG_0123 2/IMG_E0123.jpg'), 'IMG_0123_edited.JPG')
    assert_equals(rename('/any_prefix/FullSizeRender/IMG_0123.jpg'), 'IMG_0123.jpg')
    assert_equals(rename('/any_prefix/FullSizeRender/IMG_E0123.jpg'), 'IMG_0123_edited.JPG')
    assert_equals(rename('/any_prefix/FullSizeRender 2/IMG_0123.jpg'), 'IMG_0123.jpg')
    assert_equals(rename('/any_prefix/FullSizeRender 22/IMG_0123.jpg'), 'IMG_0123.jpg')


test_rename()


def get_dirnames(dirname: str, regexp_list: List[str]) -> List[str]:
    regexp = r'^({r})$'.format(r='|'.join(regexp_list))
    dir_re = re.compile(regexp)
    dirs = sorted([d for d in os.listdir(dirname) if dir_re.match(d)])
    if dirs:
        log.info(f'Got {len(dirs)} dirs in {dirname}: [ {dirs[0]!r} ... {dirs[len(dirs) // 2]!r} ... {dirs[-1]!r} ]')
    else:
        log.warn(f'No dirs in {dirname}')
    return [os.path.join(dirname, d) for d in dirs]


def count_extensions(files: List[str]) -> Dict[str, int]:
    counter = collections.defaultdict(int)
    for f in files:
        extension = f.split('.')[-1]
        counter[extension] += 1

    return dict(counter)


def get_photo_files(photo_dirs: List[str]) -> List[str]:
    all_photo_files = []
    for photo_dir in photo_dirs:
        photo_files = sorted(library.files.walk(photo_dir))
        if len(photo_files) <= 0:
            raise RuntimeError(f'Empty dir, very strange: {photo_dir!r}')

        extensions = count_extensions(photo_files)
        is_known = any([
            len(photo_files) == 1,
            extensions == {'AAE': 1, 'JPG': 1, 'jpg': 1},
            extensions == {'AAE': 2, 'JPG': 1, 'jpg': 1},  # portrait modes
            extensions == {'AAE': 1, 'MOV': 1, 'mov': 1},
            extensions == {'AAE': 1, 'MOV': 1},
            extensions == {'JPG': 1, 'MOV': 1},  # live photos
        ])

        if not is_known:
            log.info(f'Dir {photo_dir!r} has {len(photo_files)} files: {extensions}')
            for photo_file in photo_files:
                log.info(f'\tfile: {photo_file}')

        all_photo_files += photo_files

    all_photo_files.sort()

    if all_photo_files:
        count = len(all_photo_files)
        log.info(f'Got {count} files, extensions: {count_extensions(all_photo_files)}, examples:')
        for index in [0, count // 6, count // 5, count // 4, count // 3, count // 2, -1]:
            log.info(f'\t\t{index % count + 1:-4d}/{count}:  {all_photo_files[index]!r}')

    else:
        log.warn(f'No files to import')

    return all_photo_files


def is_vsco(filename: str) -> bool:
    return (filename.split('.')[-1].lower() == 'jpg') and PhotoFile(filename).is_vsco


def get_suffix(source_filename: str) -> str:
    if is_vsco(source_filename):
        return 'VSCO'

    dir_basename = os.path.basename(os.path.dirname(source_filename))
    if (source_filename.split('.')[-1].lower() == 'mov') and re.match(f'^{VSCO_RE}$', dir_basename):
        return 'VSCO - video'

    return 'originals'


def import_airdrop(
    *,
    dirname: str,
    regexp_list: list,
    do_move: bool,
):
    log.info(f'Import in {dirname!r}, regexps:')
    for r in regexp_list:
        log.info(f'\t{r}')

    dirnames = get_dirnames(dirname, regexp_list)
    filenames = get_photo_files(dirnames)

    file_mover = library.mover.FileMover()
    now_str = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')

    for src in filenames:
        suffix = get_suffix(src)
        dst = os.path.join(dirname, f'airdrop - {now_str} - {suffix}', rename(src))
        file_mover.add(src, dst)

    if do_move:
        for dirname in file_mover.get_dst_dirnames():
            if os.path.exists(dirname):
                raise RuntimeError(f'Dir already exists: {dirname!r}')
            os.mkdir(dirname)

        for src, dst in file_mover.get_mv_files(with_log=True):
            os.rename(src, dst)

        for filename in file_mover.get_rm_files(with_log=True):
            os.remove(filename)

        if any(list(library.files.walk(dirname)) for dirname in dirnames):
            raise RuntimeError(f'Dir is not empty yet: {photo_dir!r}')

        for photo_dir in dirnames:
            os.rmdir(photo_dir)

    else:
        for src, dst in file_mover.get_mv_files(with_log=True):
            pass

        for filename in file_mover.get_rm_files(with_log=True):
            pass


def run_import_airdrop(args):
    import_airdrop(
        dirname=args.dir,
        regexp_list=REGEXPS,
        do_move=args.move,
    )


def populate_parser(parser):
    parser.add_argument('--dir', help='Work dir', default=library.files.Location.Downloads)
    parser.add_argument('--move', help='Do move', action='store_true')
    parser.set_defaults(func=run_import_airdrop)
