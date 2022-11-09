import json
import os
import platform

from collections import defaultdict
from enum import Enum
from typing import Dict, List, Tuple

import attr

import logging
log = logging.getLogger(__file__)

from library.md5sum import Md5Sum
from library.files import walk


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
    Platform.macOS: os.path.join(os.environ['HOME'], 'Yandex.Disk.localized'),
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
    rootDir, hashesFile = defaults.GetRootLocation(args.mode), defaults.GetJsonLocation(args.mode)
    if not os.path.isdir(rootDir):
        raise RuntimeError(f'{rootDir} is not a directory')
    else:
        log.info(f'Detected root at {rootDir}')

    log.info(f'Calculating stats in {rootDir} and writing to {hashesFile}')

    hashes = Hashes(
        filename=hashesFile,
        root=rootDir,
    )

    for root, _, files in os.walk(rootDir):
        hash_by_name = {file: Md5Sum(os.path.join(root, file)) for file in files}
        if not hash_by_name:
            continue
        localized_root = root.replace(rootDir + os.sep, '').replace(os.sep, '/')
        log.info(f'Found {len(hash_by_name):3d} files in {localized_root!r}')
        hashes.tree[localized_root] = hash_by_name

    hashes.Save()


@attr.s
class Hashes:
    filename: str = attr.ib()
    root: str = attr.ib()
    tree: Dict[str, Dict[str, str]] = attr.ib(default={})

    @classmethod
    def load(self, filename):
        with open(filename) as f:
            data = json.load(f)

        return Hashes(
            filename=filename,
            root=data['root'],
            tree=data['tree'],
        )

    def Save(self):
        log.info(f'Saving info about {self.root} to {self.filename}')
        with open(self.filename, 'w') as f:
            json.dump(
                {
                    'root': self.root,
                    'tree': self.tree,
                },
                f,
                sort_keys=True,
                indent=4,
                separators=(',', ': '),
                ensure_ascii=False,
            )

    @property
    def files_by_hash_index(self):
        log.info('Building new files index')
        files_by_hash = defaultdict(list)
        for new_dir, new_hashes in self.tree.items():
            for new_file, new_hash in new_hashes.items():
                files_by_hash[new_hash].append(new_dir)
                if len(files_by_hash[new_hash]) >= 4:
                    log.info(f'File {new_file!r} with hash {new_hash} is among {len(files_by_hash[new_hash])} dirs')

        return index

    @property
    def clean_tree_items(self) -> List[Tuple[str, List[str]]]:
        skipDirs = [' Previews.lrdata', 'Lightroom Settings']
        skipFiles = ['.DS_Store']

        tree_items = []
        for oldDir, oldHashes in self.tree.items():
            if any(skipDir in oldDir for skipDir in skipDirs):
                continue
            hashes = [
                (filename, fileHash)
                for filename, fileHash in oldHashes.iteritems()
                if filename in skipFiles
            ]
            if not hashes:
                continue
            hashes.sort()
            tree_items.append(oldDir, hashes)

        tree_items.sort()
        return tree_items


class Comparator:
    def __init__(self, old_hashes_file: str, new_hashes_file: str):
        self.OldHashes = Hashes.load(old_hashes_file)
        self.NewHashes = Hashes.load(new_hashes_file)

    def VisualizeStates(self, exists):
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

    def __call__(self):
        new_files_hashes = self.NewHashes.files_by_hash_index
        for oldDir, oldHashes in self.OldHashes.clean_tree_items:
            dirs = defaultdict(int)
            exists = []
            for fileName, fileHash in oldHashes:
                fileDirs = new_files_hashes.get(fileHash, [])
                exists.append(bool(fileDirs))
                for d in fileDirs:
                    dirs[d] += 1
            if not all(exists):
                examples, missingFiles = [], []
                for fileExists, (fileName, fileHash) in zip(exists, oldHashes):
                    if not fileExists:
                        examples.append('  {} ({})\n'.format(logDir(fileName), fileHash))
                        missingFiles.append(fileName)
                showSize = 10
                log.info('{} out of {} files from {} are missing, file examples (up to {}):\n{}{}'.format(
                    sum(1 for e in exists if not e),
                    len(oldHashes),
                    logDir(oldDir),
                    showSize,
                    self.VisualizeStates(exists),
                    ''.join(examples[:showSize]).rstrip(),
                ))
                baseDir = os.path.basename(oldDir)
                if len([c for c in baseDir if c.isdigit()]) < 8:
                    baseDir = '_'.join(oldDir.split(os.sep)[-2:])
                dstDir = u'/Users/burmisha/Toshiba_save/Photo/{}'.format(baseDir)
#                 log.info(u'''Cmd to copy them all:
# mkdir '{dstDir}'
# cp '{srcDir}'/{{{files}}} '{dstDir}/'
# '''.format(
#     dstDir=dstDir,
#     srcDir=os.path.join(self.OldHashes.Root, oldDir),
#     files=','.join(missingFiles),
# ))
            else:
                if len(dirs) >= 2:
                    pass
                    examples = '\n'.join('  {} ({} files)'.format(logDir(dirName), count) for dirName, count in sorted(dirs.items()))
                    # log.info('All {} files from {} are among {} dirs:\n{}\n'.format(len(oldHashes), logDir(oldDir), len(dirs), examples))
                elif len(dirs) == 1:
                    pass
                    # log.debug('All {} files from {} are were found in {}'.format(len(oldHashes), logDir(oldDir), logDir(dirs.keys()[0])))
                else:
                    raise
                

def runPrint(args):
    comparator = Comparator(
        old_hashes_file=defaults.GetJsonLocation(Mode.Old),
        new_hashes_file=defaults.GetJsonLocation(Mode.New),
    )
    comparator()


def populate_calc_parser(parser):
    parser.add_argument('--mode', help='Choose mode', choices=[mode.value for mode in Mode], required=True, type=Mode)
    parser.set_defaults(func=runCalc)


def populate_print_parser(parser):
    parser.set_defaults(func=runPrint)
