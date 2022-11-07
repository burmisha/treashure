import json
import os
import re
import datetime

import PIL
import PIL.Image
import PIL.ExifTags

import library
from functools import cached_property
import attr
from typing import List

import logging
log = logging.getLogger(__name__)


class NoExifInPng(Exception):
    pass


def timestampFromStr(dateStr: str, fmt: str) -> int:
    formatter = lambda s: s.replace(':', '-').replace('.', '-')
    tmpStr = formatter(dateStr)
    tmpFmt = formatter(fmt)
    timestamp = int(datetime.datetime.strptime(tmpStr, fmt).timestamp())
    if 1300000000 < timestamp < 1600000000:
        pass
    elif timestamp == 0:
        log.warn('Timestamp is 0')
    else:
        raise RuntimeError(f'Invalid timestamp {timestamp} from {dateStr!r}')
    return timestamp


@attr.s
class PhotoInfo:
    path: str = attr.ib()
    md5sum: str = attr.ib()
    timestamps: List[int] = attr.ib()


def fromDict(data: dict) -> PhotoInfo:
    return PhotoInfo(
        path=data['path'],
        md5sum=data['md5sum'],
        timestamps=data['timestamps'],
    )


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


# TODO: check timezones
def test_parse_timestamp():
    for basename, expected in [
        ('Screenshot_20191231-190906.png', 1577804946),
        ('Screenshot_20191231-190906~2.png', 1577804946),
        ('PHOTO_20191231_190906_0.jpg', 1577804946),
    ]:
        parsed = parse_timestamp(basename)
        assert parsed == expected, f'Broken parse for {basename}:\n    parsed:\t\t{parsed}\n    expected:\t{expected}'


test_parse_timestamp()


class PhotoFile(object):
    def __init__(self, path: str):
        self.Path = path

    @property
    def photo_info(self):
        return PhotoInfo(
            path=self.Path,
            md5sum=self.Md5Sum,
            timestamps=self.Timestamps,
        )

    @property
    def Basename(self):
        return os.path.basename(self.Path)

    @cached_property
    def Exif(self):
        with PIL.Image.open(self.Path) as image:
            if image.format != 'PNG':
                rawExif = image._getexif()
                if rawExif:
                    # https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image
                    return {
                        PIL.ExifTags.TAGS[k]: v
                        for k, v in rawExif.items()
                        if k in PIL.ExifTags.TAGS
                    }

        return None

    @cached_property
    def GpsInfo(self):
        # https://stackoverflow.com/questions/19804768/interpreting-gps-info-of-exif-data-from-photo-in-python
        if self.Exif and ('GPSInfo' in self.Exif):
            return {
                PIL.ExifTags.GPSTAGS.get(key, key): value
                for key, value in self.Exif['GPSInfo'].items()
            }
        return None

    @cached_property
    def Camera(self):
        if self.Exif:
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
            for key, value in self.Exif.items():
                lowerKey = key.lower()
                if key in [
                    'DateTime',
                    'DateTimeDigitized',
                    'DateTimeOriginal',
                ]:
                    assert re.match(r'^\d{4}(:\d{2}){2} (\d{2})(:\d{2}){2}$', value)
                    timestamp = timestampFromStr(value, '%Y-%m-%d %H-%M-%S')
                    log.debug(f'Date {key} is {value} ({timestamp})')
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


    @cached_property
    def IsVsco(self):
        if self.Exif:
            return any(
                isinstance(value, str) and 'vsco' in value.lower()
                for  value in self.Exif.values()
            )

        return False

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
    photo_files = []
    processor = Processor()
    for filename in get_filenames(args.dir, args.file, args.skip):
        photo_file = processor(filename)
        if photo_file is not None:
            photo_files.append(photo_file)

    with open(args.json_file, 'w') as f:
        f.write(json.dumps(
            [attr.asdict(photo_file.photo_info) for photo_file in photo_files],
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
