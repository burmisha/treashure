import argparse
import hashlib
import json
import os
import platform

from collections import defaultdict

import logging
log = logging.getLogger(__file__)


class Defaults(object):
    def __init__(self):
        system = platform.system()
        if system == 'Windows':
            mode = 'win'
        elif system == 'Darwin':
            mode = 'osx'
        else:
            raise RuntimeError('Invalid platform system {!r}'.format(system))
        log.info('Running in {!r} mode'.format(mode))
        self.System = mode
        self.OldJsonName = 'old_hashes_4.json'
        self.NewJsonName = 'new_hashes_4.json'

    def GetJsonLocation(self, oldOrNew):
        basename = self.OldJsonName if oldOrNew == 'old' else self.NewJsonName
        yaDisk = {
            'win': os.path.join('D:' + os.sep, 'YandexDisk'),
            'osx': os.path.join(os.sep, 'Users', 'burmisha', 'Yandex.Disk.localized'),
        }
        return os.path.join(yaDisk[self.System], 'tmp', basename)

    def GetRootLocation(self, oldOrNew):
        paths = {
        #     'old': os.path.join(os.sep, 'Volumes', '1Tb_2014', '2015-05-30_photo'),
        #     'new': os.path.join('D:' + os.sep, 'Photo'),
        #     'old': os.path.join('D:' + os.sep, 'PhotoPhotoshop'),
        #     'new': os.path.join('K:' + os.sep, 'PhotoPhotoshop'),
        #     'old': os.path.join(os.sep, 'Volumes', 'bur300gb'),
        #     'new': os.path.join('K:' + os.sep, 'bur300gb'),
            'old': os.path.join(os.sep, 'Users', 'burmisha', 'ene2nd'),
            'new': os.path.join('K:' + os.sep, 'ene2nd'),
        }
        return paths[oldOrNew]


defaults = Defaults()


def Md5Sum(filename):
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(2 ** 16), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def runCalc(args):
    rootDir, hashesFile = defaults.GetRootLocation(args.mode), defaults.GetJsonLocation(args.mode)
    rootDir = unicode(rootDir.decode('utf-8'))
    if not os.path.isdir(rootDir):
        raise RuntimeError('{} is not a directory'.format(logDir(rootDir)))
    else:
        log.info(u'Detected root at {}'.format(logDir(rootDir)))

    log.info('Calculating stats in {} and writing to {}'.format(logDir(rootDir), logDir(hashesFile)))

    hashes = Hashes(hashesFile)
    hashes.Root = rootDir

    for root, _, files in os.walk(rootDir):
        files = list(files)
        if files:
            log.info('Found {} files in {}'.format(len(files), logDir(root)))
            localName = root.replace(rootDir + os.sep, '').replace(os.sep, '/')
            hashes.Tree[localName] = dict((file, Md5Sum(os.path.join(root, file))) for file in files)

    hashes.Save()

def logDir(dirName):
    return '\'{}\''.format(dirName.encode('utf-8'))

class Hashes(object):
    def __init__(self, filename):
        self.Filename = filename
        self.Root = None
        self.Tree = {}

    def Load(self):
        with open(self.Filename) as f:
            hashes = json.loads(f.read())
            self.Root = hashes['root']
            self.Tree = hashes['tree']
            log.info('Found root {}'.format(logDir(self.Root)))

    def Save(self):
        log.info('Saving info about {} to {}'.format(logDir(self.Root), logDir(self.Filename)))
        with open(self.Filename, 'w') as f:
            json.dump(
                {
                    'root': self.Root,
                    'tree': self.Tree,
                },
                f,
                sort_keys=True,
                indent=4,
                separators=(',', ': ')
            )


class Comparator(object):
    def __init__(self, oldHashes, newHashes):
        self.OldHashes = Hashes(oldHashes)
        self.NewHashes = Hashes(newHashes)

        self.OldHashes.Load()
        self.NewHashes.Load()

    def Index(self):
        log.info('Building new files index')
        oldFilesHashes = defaultdict(list)
        for newDir, newHashes in self.NewHashes.Tree.iteritems():
            for fileName, fileHash in newHashes.iteritems():
                oldFilesHashes[fileHash].append(newDir)
                if len(oldFilesHashes[fileHash]) >= 4:
                    log.info('File {!r} with hash {} is among {} dirs'.format(fileName, fileHash, len(oldFilesHashes[fileHash])))

        return oldFilesHashes

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

    def OldItems(self):
        skipDirs = [' Previews.lrdata', 'Lightroom Settings']
        skipFiles = ['.DS_Store']
        treeItems = self.OldHashes.Tree.items()
        treeItems.sort()
        for oldDir, oldHashes in treeItems:
            if any(skipDir in oldDir for skipDir in skipDirs):
                continue
            else:
                hashes = []
                for fileName, fileHash in oldHashes.iteritems():
                    if fileName not in skipFiles:
                        hashes.append((fileName, fileHash))
                if hashes:
                    hashes.sort()
                    yield oldDir, hashes

    def __call__(self):
        oldFilesHashes = self.Index()
        for oldDir, oldHashes in self.OldItems():
            dirs = defaultdict(int)
            exists = []
            for fileName, fileHash in oldHashes:
                fileDirs = oldFilesHashes.get(fileHash, [])
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
        defaults.GetJsonLocation('old'),
        defaults.GetJsonLocation('new'),
    )
    comparator()


def populate_calc_parser(parser):
    parser.add_argument('--mode', help='Choose mode', choices=['old', 'new'], required=True)
    parser.set_defaults(func=runCalc)


def populate_print_parser(parser):
    parser.set_defaults(func=runPrint)
