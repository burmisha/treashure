import argparse
import json
import os
import re
import time
import datetime

import PIL
import PIL.Image
import PIL.ExifTags

from pprint import pprint

import library
import collections
from functools import cached_property

import logging
log = logging.getLogger(__name__)


class NoExifInPng(Exception):
    pass


def timestampFromStr(dateStr, fmt):
    formatter = lambda s: s.replace(':', '-').replace('.', '-')
    tmpStr = formatter(dateStr)
    tmpFmt = formatter(fmt)
    timestamp = int(time.mktime(datetime.datetime.strptime(tmpStr, fmt).timetuple()))
    if 1300000000 < timestamp < 1600000000:
        pass
    elif timestamp == 0:
        log.warn('Timestamp is 0')
    else:
        raise RuntimeError(f'Invalid timestamp {timestamp} from {dateStr!r}')
    return timestamp


def toDict(photofile):
    return {
        'path': photofile.Path,
        'md5sum': photofile.Md5Sum,
        'timestamps': photofile.Timestamps,
    }


def fromDict(photofileJson):
    photofile = PhotoFile(photofileJson['path'])
    photofile.Md5Sum = photofileJson['md5sum']
    photofile.Timestamps = photofileJson['timestamps']
    return photofile


def parse_timestamp(basename: str) -> int:
    if (
        re.match(r'^\d{4}(-\d{2}){2} \d{2}([-\.]\d{2}){2}( 1)?\.\w{3,4}$', basename)
        or re.match(r'^\d{4}(-\d{2}){2} \d{2}([-\.]\d{2}){2}_\d{10}\.\w{3}$', basename)
    ):
        return timestampFromStr(basename[:19], '%Y-%m-%d %H-%M-%S')
    elif re.match(r'^wp_ss_\d{8}_\d{4}\.\w{3}$', basename):
        return timestampFromStr(basename[6:18], '%Y%m%d_%H%M')
    elif re.match(r'^Screenshot_\d{4}(-\d{2}){5}(-\d{3})?_.*.(png|jpg)$', basename):
        # skipping subseconds
        return timestampFromStr(basename[11:30], '%Y-%m-%d-%H-%M-%S')
    elif re.match(r'^IMG_\d{8}_\d{6}(_HDR|_HHT|_1)?\.(JPG|jpg|dng)$', basename):
        return timestampFromStr(basename[4:19], '%Y%m%d_%H%M%S')
    elif re.match(r'^WP_\d{8}(_\d{2}){3}_(Pro|Smart|Panorama|Selfie|SmartShoot).*\.jpg$', basename):
        return timestampFromStr(basename[3:20], '%Y%m%d_%H_%M_%S')
    elif re.match(r'^DOS-\d{4}(-\d{2}){2} \d{2}(_\d{2}){2}Z\.jpg$', basename):
        return timestampFromStr(basename[4:23], '%Y-%m-%d %H_%M_%S')
    elif re.match(r'^1\d{12}\.jpg', basename):
        return int(basename[:13]) // 1000
    elif re.match(r'^Screenshot_\d{8}-\d{6}(~2)?\.png$', basename):
        return timestampFromStr(basename[11:26], '%Y%m%d-%H%M%S')
    elif re.match(r'^PHOTO_\d{8}_\d{6}(_\d)?\.jpg$', basename):
        return timestampFromStr(basename[6:21], '%Y%m%d_%H%M%S')

    return None


def test_parse_timestamp():
    for basename, expected in [
        ('Screenshot_20191231-190906.png', 1577812146),
        ('Screenshot_20191231-190906~2.png', 1577812146),
        ('PHOTO_20191231_190906_0.jpg', 1577812146),
    ]:
        parsed = parse_timestamp(basename)
        assert parsed == expected, f'Broken parse:\n    parsed:\t\t{parsed}\n    sexpected:\t{expected}'


test_parse_timestamp()


class PhotoFile(object):
    def __init__(self, path: str):
        self.Path = path

    @property
    def Basename(self):
        return os.path.basename(self.Path)

    @cached_property
    def pil_format(self):
        with PIL.Image.open(self.Path) as image:
            return image.format

    @cached_property
    def Exif(self):
        with PIL.Image.open(self.Path) as image:
            if image.format == 'PNG':
                return None
            else:
                rawExif = image._getexif()
                if rawExif is None:
                    return None
                else:
                    # https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image
                    return {
                        PIL.ExifTags.TAGS[k]: v
                        for k, v in rawExif.items()
                        if k in PIL.ExifTags.TAGS
                    }

    @cached_property
    def GpsInfo(self):
        if self.Exif is None:
            return None

        # https://stackoverflow.com/questions/19804768/interpreting-gps-info-of-exif-data-from-photo-in-python
        if 'GPSInfo' in self.Exif:
            gpsInfo = {
                PIL.ExifTags.GPSTAGS.get(key, key): value
                for key, value in self.Exif['GPSInfo'].items()
            }
        else:
            gpsInfo = None
        return gpsInfo

    @cached_property
    def Camera(self):
        if not self.Exif:
            return None

        make = self.Exif.get('Make')
        model = self.Exif.get('Model')
        if make:
            return f'{make} {model}'
        else:
            log.debug(f'No camera: make {make!r}, model {model!r} in {self.Path}')
            return None

    @cached_property
    def Timestamps(self):
        timestamps = set()
        filenameTimestamp = parse_timestamp(self.Basename)
        if filenameTimestamp is not None:
            timestamps.add(filenameTimestamp)
        else:
            log.debug(f'Name {self.Basename!r} has no date: {filenameTimestamp}')

        if self.Exif:
            isVsco = self.IsVsco()
            for key, value in self.Exif.items():
                lowerKey = key.lower()
                if key in [
                    'DateTime',
                    'DateTimeDigitized',
                    'DateTimeOriginal',
                ]:
                    assert re.match(r'^\d{4}(:\d{2}){2} (\d{2})(:\d{2}){2}$', value)
                    timestamp = timestampFromStr(value, '%Y-%m-%d %H-%M-%S')
                    log.debug('Date {} is {} ({})'.format(key, value, timestamp))
                    timestamps.add(timestamp)
                elif key in [
                    'SubsecTime',
                    'SubsecTimeDigitized',
                    'SubsecTimeOriginal',
                    'ExposureTime',
                ]:
                    pass
                elif 'date' in lowerKey or 'time' in lowerKey:
                    raise RuntimeError(f'Unknown datetime key: {key!r} {value!r} in {self.Path}')
        timestamps = sorted(list(timestamps))
        if not timestamps:
            log.warn(f'No timestamps in {self.Path}')
            # raise RuntimeError('No timestamps')
        elif len(timestamps) > 3:
            # yes, they exist
            raise RuntimeError(f'Too many timestamps: {timestamps} in {self.Path}')
        return timestamps


    def IsVsco(self):
        isVsco = False
        for key, value in self.Exif.items():
            if isinstance(value, str):
                if 'vsco' in value.lower():
                    log.debug('Is vsco: {} : {}'.format(key, value))
                    isVsco = True
        return isVsco

    @cached_property
    def Md5Sum(self) -> str:
        return library.md5sum.Md5Sum(self.Path)


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

    for dirName in dirs:
        for root, _, files in os.walk(dirName):
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
    photoFiles = []
    processor = Processor()
    for filename in get_filenames(args.dir, args.file, args.skip):
        photoFile = processor(filename)
        if photoFile is not None:
            photoFiles.append(photoFile)

    with open(args.json_file, 'w') as f:
        f.write(json.dumps(
            [toDict(photoFile) for photoFile in photoFiles],
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
