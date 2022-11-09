import json
import os
import platform

from collections import defaultdict
from enum import Enum
from functools import cached_property
from typing import Dict, List

import attr
import logging
log = logging.getLogger(__file__)

from library.md5sum import Md5Sum


HOME_DIR = os.environ['HOME']


class Platform(str, Enum):
    Windows = 'win'
    macOS = 'osx'


class Mode(str, Enum):
    Old = 'old'
    New = 'new'


def get_platform() -> Platform:
    system = platform.system()
    if system == 'Windows':
        return Platform.Windows
    elif system == 'Darwin':
        return Platform.macOS
    else:
        raise RuntimeError(f'Invalid platform system {system!r}')
    log.info(f'Running in {mode!r} mode')


ya_disk_dir = {
    Platform.Windows: os.path.join('D:' + os.sep, 'YandexDisk'),
    Platform.macOS: os.path.join(HOME_DIR, 'Yandex.Disk.localized'),
}[get_platform()]


class Defaults(object):
    def __init__(self):
        self.OldJsonName = 'old_hashes_5.json'
        self.NewJsonName = 'new_hashes_5.json'

    def GetJsonLocation(self, mode: Mode) -> str:
        basename = {
            mode.Old: self.OldJsonName,
            mode.New: self.NewJsonName,
        }[mode]

        return os.path.join(ya_disk_dir, basename)

    def GetRootLocation(self, mode: Mode):
        paths = {
            # mode.Old: os.path.join(os.sep, 'Volumes', '1Tb_2014', '2015-05-30_photo'),
            # mode.New: os.path.join('D:' + os.sep, 'Photo'),
            # mode.Old: os.path.join('D:' + os.sep, 'PhotoPhotoshop'),
            # mode.New: os.path.join('K:' + os.sep, 'PhotoPhotoshop'),
            # mode.Old: os.path.join(os.sep, 'Volumes', 'bur300gb'),
            # mode.New: os.path.join('K:' + os.sep, 'bur300gb'),
            # mode.Old: os.path.join(os.environ['HOME'], 'ene2nd'),
            # mode.New: os.path.join('K:' + os.sep, 'ene2nd'),
            mode.Old: os.path.join(ya_disk_dir, 'Photo', '2020'),
        }
        return paths[mode]


defaults = Defaults()


def runCalc(args):
    root = defaults.GetRootLocation(args.mode)
    result_file = defaults.GetJsonLocation(args.mode)
    if not os.path.isdir(root):
        raise RuntimeError(f'{root} is not a directory')

    log.info(f'Calculating stats in root {root} and writing to {result_file}')

    hashes = Hashes(root=root)

    for sub_root, _, files in os.walk(root):
        hash_by_name = {file: Md5Sum(os.path.join(sub_root, file)) for file in files}
        if not hash_by_name:
            continue
        localized_root = sub_root.replace(root + os.sep, '').replace(os.sep, '/')
        log.info(f'Found {len(hash_by_name):3d} files in {localized_root!r}')
        hashes.tree[localized_root] = hash_by_name

    hashes.Save(result_file)


@attr.s
class Hashes:
    root: str = attr.ib()
    tree: Dict[str, Dict[str, str]] = attr.ib(default={})

    @classmethod
    def load(self, filename):
        with open(filename) as f:
            data = json.load(f)

        hashes = Hashes(**data)
        log.info(f'Loaded hashes for {hashes.root}')
        return hashes

    def Save(self, filename):
        log.info(f'Saving info about {self.root} to {filename}')
        with open(filename, 'w') as f:
            json.dump(
                attr.asdict(self),
                f,
                sort_keys=True,
                indent=4,
                separators=(',', ': '),
                ensure_ascii=False,
            )

    @cached_property
    def dirs_by_hash(self):
        log.info(f'Building files index for {self.root}')
        index = defaultdict(list)
        for dir_name, hashes in self.tree.items():
            for file_name, file_hash in hashes.items():
                index[file_hash].append(dir_name)
                dirs_count = len(index[file_hash])
                if dirs_count >= 4:
                    log.info(f'File {file_name!r} with hash {file_hash} is among {dirs_count} dirs')

        return index

    @cached_property
    def clean_tree(self) -> Dict[str, List[str]]:
        skipDirs = [' Previews.lrdata', 'Lightroom Settings']
        skipFiles = ['.DS_Store']

        tree_items = {}
        for dir_names, hashes in self.tree.items():
            if any(skipDir in dir_names for skipDir in skipDirs):
                continue
            hashes = {
                filename: fileHash
                for filename, fileHash in hashes.items()
                if filename not in skipFiles
            }
            if hashes:
                tree_items[dir_names] = hashes

        return tree_items


def visualize_states(exists: list):
    if any(exists):
        index = 0
        delta = 80
        result = ''
        while index < len(exists):
            part = exists[index:index + delta]
            line = ''.join(['X' if p else '_' for p in part])
            add = ' ' * (delta - len(line))
            result += '|{}|{} {} of {} are missing\n'.format(line, add, sum(1 for p in part if not p), len(part))
            index += delta
        return result
    else:
        return 'All files are missing\n'


def compare(*, old_hashes_file: str, new_hashes_file: str):
    old_hashes = Hashes.load(old_hashes_file)
    new_hashes = Hashes.load(new_hashes_file)
    for oldDir, oldHashes in old_hashes.clean_tree.items():
        relevant_dirs = defaultdict(int)
        for fileName, fileHash in oldHashes.items():
            fileDirs = new_hashes.dirs_by_hash[fileHash]
            for d in fileDirs:
                relevant_dirs[d] += 1

        if sum(relevant_dirs.values()) == len(oldHashes):
            relevant_dirs_count = len(relevant_dirs)
            items = sorted(relevant_dirs.items())
            files_count = len(oldHashes)
            if relevant_dirs_count >= 2:
                examples = '\n'.join(f'  {dirName!r} ({count} files)' for dirName, count in items)
                log.info(f'Found all {files_count:3d} files from {oldDir!r} in {relevant_dirs_count} dirs:\n{examples}\n')
            elif relevant_dirs_count == 1:
                log.info(f'Found all {files_count:3d} files from {oldDir!r} in {items[0][0]!r}')
            else:
                raise RuntimeError('No relevant dirs')

        else:
            examples, missingFiles = [], []
            exists = []
            for fileName, fileHash in oldHashes.items():
                fileExists = bool(new_hashes.dirs_by_hash[fileHash])
                exists.append(fileExists)
                if not fileExists:
                    examples.append('  {fileName!r} ({fileHash})')
                    missingFiles.append(fileName)

            limit = 10
            splitter = '\n'
            log.info(
                f'{sum(1 for e in exists if not e)} out of {len(oldHashes)} files from {oldDir!r} are missing, '
                f'file examples (up to {limit}):\n{visualize_states(exists)}'
                f'{splitter.join(examples[:limit])}'
            )
            baseDir = os.path.basename(oldDir)
            if len([c for c in baseDir if c.isdigit()]) < 8:
                baseDir = '_'.join(oldDir.split(os.sep)[-2:])

            dstDir = f'{HOME_DIR}/Toshiba_save/Photo/{baseDir}'
            log.debug(f'''Cmd to copy them all:
mkdir '{dstDir}'
cp '{os.path.join(old_hashes.root, oldDir)}'/{{{",".join(missingFiles)}}} '{dstDir}/'
''')


def runCompare(args):
    compare(
        old_hashes_file=defaults.GetJsonLocation(Mode.Old),
        new_hashes_file=defaults.GetJsonLocation(Mode.Old),
    )


def populate_calc_parser(parser):
    parser.add_argument('--mode', help='Choose mode', choices=[mode.value for mode in Mode], required=True, type=Mode)
    parser.set_defaults(func=runCalc)


def populate_compare_parser(parser):
    parser.set_defaults(func=runCompare)
