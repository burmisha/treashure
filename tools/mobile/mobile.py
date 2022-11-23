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
from typing import List, Optional

import logging
log = logging.getLogger(__name__)

PIL.Image.MAX_IMAGE_PIXELS = 200 * 1024 * 1024


def timestampFromStr(dateStr: str, fmt: str) -> int:
    formatter = lambda s: s.replace(':', '-').replace('.', '-')
    tmpStr = formatter(dateStr)
    tmpFmt = formatter(fmt)
    timestamp = int(datetime.datetime.strptime(tmpStr, tmpFmt).timestamp())
    if 1300000000 < timestamp < 1700000000:
        pass
    elif timestamp < 1000000000:
        log.warn(f'Timestamp {timestamp} is too old, skippping')
        return None
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
    elif re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b', basename):
        return timestampFromStr(basename[:19], '%Y-%m-%d %H:%M:%S')
    elif re.match(r'^\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}\b', basename):
        return timestampFromStr(basename[:19], '%Y-%m-%d %H.%M.%S')
    elif re.match(r'^\d{4}-burmisha-\d{14}\b', basename):
        return timestampFromStr(basename[14:28], '%Y%m%d%H%M%S')

    return None


# TODO: check timezones
def test_parse_timestamp():
    for basename, expected in [
        ('Screenshot_20191231-190906.png', 1577804946),
        ('Screenshot_20191231-190906~2.png', 1577804946),
        ('PHOTO_20191231_190906_0.jpg', 1577804946),
        ('2021-11-06 16:18:21.jpg', 1636201101),
        ('2020-04-24 03.00.49 3.jpg', 1587682849),
        ('1305-burmisha-20130524232554', 1369423554),
    ]:
        parsed = parse_timestamp(basename)
        assert parsed == expected, f'Broken parse for {basename}:\n    parsed:\t\t{parsed}\n    expected:\t{expected}'


test_parse_timestamp()


def get_dt_from_exif(exif: dict, suffix: str):
    dt_value = exif.get(f'DateTime{suffix}')
    offset_value = exif.get(f'OffsetTime{suffix}')
    subsec_value = exif.get(f'SubsecTime{suffix}')

    if not dt_value:
        return None

    dt_value = dt_value.strip()
    if not dt_value:
        return None

    microsecond = 0
    if subsec_value is not None:
        millisecond = int(subsec_value.strip('\x00'))
        # units are not specified
        if 0 <= millisecond < 1000:
            microsecond = 1000 * millisecond
        elif 1000 <= millisecond < 999999:
            microsecond = millisecond
        else:
            raise ValueError(f'Invalid millisecond: {millisecond}')
    else:
        millisecond = 0

    if offset_value:
        timedelta = {
            '+01:00': datetime.timedelta(seconds=3600 * 1),
            '+02:00': datetime.timedelta(seconds=3600 * 2),
            '+03:00': datetime.timedelta(seconds=3600 * 3),
            '+04:00': datetime.timedelta(seconds=3600 * 4),
            '+05:00': datetime.timedelta(seconds=3600 * 5),
        }[offset_value]
        tzinfo = datetime.timezone(timedelta)
    else:
        tzinfo = None
    
    date, time = dt_value.split(' ')
    hours, minutes = time.split(':', 1)
    hours = int(hours)
    if hours >= 24:
        hours = hours - 24
        days_delta = 1
        dt_value = f'{date} {hours}:{minutes}'
    else:
        days_delta = 0
    dt = datetime.datetime.strptime(dt_value, '%Y:%m:%d %H:%M:%S')
    dt += datetime.timedelta(days=days_delta)
    dt = dt.replace(microsecond=microsecond, tzinfo=tzinfo)
    return dt


def test_get_dt_from_exif():
    exif = {'DateTime': '2022:04:17 15:13:50', 'SubsecTime': '00'}
    dt = get_dt_from_exif(exif, suffix='')
    assert dt == datetime.datetime(2022, 4, 17, 15, 13, 50), f'{dt!r}'

    exif = {
        'DateTimeOriginal': '2022:07:09 11:39:04',
        'OffsetTimeOriginal': '+05:00',
        'SubsecTimeOriginal': '005',
    }
    dt = get_dt_from_exif(exif, suffix='Original')
    assert dt == datetime.datetime(2022, 7, 9, 11, 39, 4, 5000, tzinfo=datetime.timezone(datetime.timedelta(seconds=18000))), f'{dt!r}'

    exif = {'DateTimeDigitized': '2019:09:22 24:40:46'}
    dt = get_dt_from_exif(exif, suffix='Digitized')
    assert dt == datetime.datetime(2019, 9, 23, 0, 40, 46), f'{dt!r}'

    exif = {'DateTimeDigitized': '2019:09:22 14:40:46', 'SubsecTimeDigitized': '919503\x00'}
    dt = get_dt_from_exif(exif, suffix='Digitized')
    assert dt == datetime.datetime(2019, 9, 22, 14, 40, 46, 919503), f'{dt!r}'


test_get_dt_from_exif()

@attr.s
class PhotoFile(object):
    Path: str = attr.ib()

    @property
    def photo_info(self):
        return PhotoInfo(
            path=self.Path,
            md5sum=self.Md5Sum,
            timestamps=[self.timestamp],
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
    def datetime(self) -> Optional[datetime.datetime]:
        filename_ts = parse_timestamp(self.Basename)
        if filename_ts:
            filename_dt = datetime.datetime.utcfromtimestamp(filename_ts)
            local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
            filename_dt =  filename_dt.replace(tzinfo=local_timezone)
        else:
            filename_dt = None
            log.debug(f'Name {self.Basename!r} has no date')

        if self.Exif:
            datetime_exif = {}
            for key, value in sorted(self.Exif.items()):
                lowerKey = key.lower()
                if 'date' in lowerKey or 'time' in lowerKey:
                    datetime_exif[key] = value
                    if key not in {
                        'DateTime', 'OffsetTime', 'SubsecTime',
                        'DateTimeDigitized', 'OffsetTimeDigitized', 'SubsecTimeDigitized',
                        'DateTimeOriginal', 'OffsetTimeOriginal', 'SubsecTimeOriginal',
                        'ExposureTime', 'CompositeImageExposureTimes',
                    }:
                        raise RuntimeError(f'Unknown datetime key: {key!r}, value {value!r} in {self.Path}')
            if datetime_exif:
                log.debug(f'datetime_exif: {datetime_exif}')
            else:
                log.debug(f'No date in exif for {self.Path}: {self.Exif}')

            original_dt = get_dt_from_exif(self.Exif, 'Original')
            if original_dt:
                return original_dt

            digitized_dt = get_dt_from_exif(self.Exif, 'Digitized')
            if digitized_dt:
                return digitized_dt

            if filename_dt:
                log.warn(f'Using filename dt for {self.Path}: {datetime_exif}')
                return filename_dt

            modification_dt = get_dt_from_exif(self.Exif, '')
            if modification_dt:
                log.warn(f'Using default dt for {self.Path}: {datetime_exif}')
                return modification_dt

        else:
            log.warn(f'No EXIF in {self.Path}')

        if filename_dt:
            log.warn(f'Using filename dt for {self.Path}')
            return filename_dt

        return None
            

    @cached_property
    def timestamp(self) -> Optional[int]:
        if self.datetime:
            return int(self.datetime.timestamp())
        return None

    @cached_property
    def is_vsco(self):
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
