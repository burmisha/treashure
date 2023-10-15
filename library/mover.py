import collections
import difflib
import os

import library.md5sum

from dataclasses import dataclass
from typing import Dict, List

import logging
log = logging.getLogger(__name__)


@dataclass
class BrokenFile:
    old_src: str
    new_src: str
    dst: str
    old_md5: str
    new_md5: str


class FileMover:
    def __init__(self):
        self._move_list = []  # to keep order
        self._src_to_dst = dict()
        self._dst_to_src = dict()
        self._remove_list = []
        self._broken_files = []

    def add(self, src: str, dst: str):
        if src == dst:
            log.debug(f'Same location, skip: {src!r}')
            return

        if os.path.exists(dst):
            raise RuntimeError(f'Dst already exists: {dst!r}')

        if src in self._src_to_dst:
            raise RuntimeError(f'Trying to move src again: {src!r}')

        if dst in self._dst_to_src:
            broken_file = BrokenFile(
                old_src=self._dst_to_src[dst],
                new_src=src,
                dst=dst,
                old_md5=library.md5sum.Md5Sum(self._dst_to_src[dst]),
                new_md5=library.md5sum.Md5Sum(src),
            )
            if broken_file.old_md5 == broken_file.new_md5:
                log.debug(
                    f'Same dst location for files, will drop {src}:'
                    f'\n\told src:\t{broken_file.old_src}'
                    f'\n\tnew src:\t{broken_file.new_src}'
                    f'\n\tdst:\t\t{broken_file.dst}'
                    f'\n\tmd5sum:\t{broken_file.old_md5}'
                )
                self._remove_list.append(src)
                return
            else:
                self._broken_files.append(broken_file)

        self._move_list.append((src, dst))
        self._src_to_dst[src] = dst
        self._dst_to_src[dst] = src

    @property
    def has_dst_files(self):
        return bool(self._move_list)

    def get_mv_files(self, with_log=False):
        self._validate()
        if with_log:
            log.info(f'Got {len(self._move_list)} files to move')
        for src, dst in self._move_list:
            if with_log:
                log.info(f'mv {src!r} -> {dst!r}')
            yield src, dst

    def get_rm_files(self, with_log=False):
        self._validate()
        if with_log:
            log.info(f'Got {len(self._remove_list)} files to remove')
        for filename in self._remove_list:
            if with_log:
                log.info(f'rm {filename!r}')
            yield filename

    def _validate(self):
        for broken_file in self._broken_files:
            log.error(
                f'Broken file:'
                f'\n\told: {broken_file.old_src!r} ({broken_file.old_md5})'
                f'\n\tnew: {broken_file.new_src!r} ({broken_file.new_md5})'
                f'\n\tdst: {broken_file.dst!r}'
            )
            if broken_file.dst.endswith('.AAE'):
                with open(broken_file.old_src) as old, open(broken_file.new_src) as new:
                    ndiff = difflib.ndiff(old.readlines(), new.readlines())
                    delta = ''.join(
                        line for line in ndiff
                        if line.startswith('- ') or line.startswith('+ ')
                    )
                    log.error(f'diff:\n{delta}')

        if self._broken_files:
            raise RuntimeError(f'Has {len(self._broken_files)} broken files, resolve manually')

    def get_src_dirnames(self) -> Dict[str, List[str]]:
        dirnames = collections.defaultdict(list)
        for src, _ in self.get_mv_files():
            dirnames[os.path.dirname(src)].append(src)

        for dirname, files in dirnames.items():
            log.info(f'Src dir {dirname!r} with {len(files)} files: [ {os.path.basename(files[0])!r} .. {os.path.basename(files[-1])!r} ]')

        return dict(dirnames)

    def get_dst_dirnames(self) -> Dict[str, List[str]]:
        dirnames = collections.defaultdict(list)
        for _, dst in self.get_mv_files():
            dirnames[os.path.dirname(dst)].append(dst)

        for dirname, files in dirnames.items():
            log.info(f'Dst dir {dirname!r} with {len(files)} files: [ {os.path.basename(files[0])!r} .. {os.path.basename(files[-1])!r} ]')

        return dict(dirnames)
