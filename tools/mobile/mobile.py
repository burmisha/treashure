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
from typing import List, Optional, Tuple

import logging
log = logging.getLogger(__name__)

PIL.Image.MAX_IMAGE_PIXELS = 200 * 1024 * 1024



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


TIMESTAMP_RE = (
    r'('
    r'20\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r'([-_\.: ])?'
    r'\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r'([-_\.:])?'
    r'\d{2}'
    r')'
)

TS_PREFIXES = [
    fr'^{TIMESTAMP_RE}[-_\.~ ]',
    fr'[a-zA-Z-_]{TIMESTAMP_RE}[-_\.~ ]',
    fr'^{TIMESTAMP_RE}\b',
    fr'[a-zA-Z-_]{TIMESTAMP_RE}\b',
]


def parse_timestamp(basename: str) -> int:
    for ts_re in TS_PREFIXES:
        res = re.search(ts_re, basename)
        if res:
            res = ''.join([l for l in res.group(1) if l.isdigit()])
            timestamp = int(datetime.datetime.strptime(res, '%Y%m%d%H%M%S').timestamp())
            if 1100000000 < timestamp < 2000000000:
                return timestamp
            elif timestamp < 100000000:
                log.warn(f'Timestamp {timestamp} is too old, skippping')
                return None
            else:
                raise RuntimeError(f'Invalid timestamp {timestamp} from {basename!r}')

    if re.match(r'.*\d{4}.?\d{2}.?\d{2}.*\d{2}.?\d{2}.?\d{2}.*', basename):
        log.info(f'No dt in {basename}')

    return None


# TODO: check timezones
def test_parse_timestamp():
    for basename, expected in [
        ('Screenshot_20191231-190906.png', 1577804946),
        ('Screenshot_20191231-190906~2.png', 1577804946),
        ('PHOTO_20191231_190906_0.jpg', 1577804946),
        ('2021-11-06 16:18:21.jpg', 1636201101),
        ('2020-04-24 03.00.49 3.jpg', 1587682849),
        ('1305-burmisha-20130524232554.png', 1369423554),
        ('photo_2018-05-10_17-13-31.jpg', 1525958011),
        ('photo_2018_05-10_17-13-31.jpg', 1525958011),
        ('photo_2018.05-10_17-13-31.jpg', 1525958011),
        ('photo_2018:05-10_17-13-31.jpg', 1525958011),
        ('20180510171331.png', 1525958011),
        ('2018-05-10 17:13:31.png', 1525958011),
        ('2007_04_03-07_58_17.png', 1175569097),
        ('photo311519012136790160.png', None),
        ('11-49472976-784857-800-100.jpg', None),
        ('XX-49472976-784857-800-100.jpg', None),
        ('2007_04_26-16_37_11.jpg', 1177587431),
        ('P-00930-2007_04_26-16_37_11.jpg', 1177587431),
        ('IMG_20191028_081550_384.jpg', 1572236150),
        ('IMG_20191028_081550_384', 1572236150),
        ('20191028081550', 1572236150),
        ('2005-01-01 10:10:10', 1104559810),
        ('2033-01-01 10:10:10', 1988172610),
    ]:
        parsed = parse_timestamp(basename)
        assert parsed == expected, f'Broken parse for {basename}:\n    parsed:\t\t{parsed}\n    expected:\t{expected}'


test_parse_timestamp()


def get_timedelta(offset: str) -> datetime.timedelta:
    res = re.search(r'^\+(\d\d):00$', offset)
    if res:
        hours = int(res.group(1))
        assert 1 <= hours <= 11
        return datetime.timedelta(seconds=3600 * hours)
    else:
        raise ValueError(f'Invalid offset: {offset!r}')


def cut_large_hour(dt_str: str) -> Tuple[str, int]:
    date, time = dt_str.split(' ')
    hours, minutes = time.split(':', 1)
    hours = int(hours)
    if hours >= 24:
        hours = hours - 24
        return f'{date} {hours}:{minutes}', 1
    else:
        return dt_str, 0
        days_delta = 0


def test_cut_large_hour():
    for dt, expected_dt, expected_days in [
        ('2010-11-22 24:40:20', '2010-11-22 0:40:20', 1),
        ('2010-11-22 23:41:21', '2010-11-22 23:41:21', 0),
    ]:
        result_dt, result_days = cut_large_hour(dt)
        assert result_dt == expected_dt, f'{result_dt!r} expected {expected_dt!r}'
        assert result_days == expected_days, f'{result_days!r} expected {expected_days!r}'


test_cut_large_hour()


def get_microsecond(subsec: str) -> int:
    if subsec is not None:
        millisecond = int(subsec.strip('\x00'))
        # units are not specified
        if 0 <= millisecond < 1000:
            return 1000 * millisecond
        elif 1000 <= millisecond < 999999:
            return millisecond
        else:
            raise ValueError(f'Invalid millisecond: {millisecond}')

    return 0

def get_dt_from_exif(exif: dict, suffix: str):
    dt_value = exif.get(f'DateTime{suffix}')
    offset_value = exif.get(f'OffsetTime{suffix}')
    subsec_value = exif.get(f'SubsecTime{suffix}')

    if not dt_value:
        return None

    dt_value = dt_value.strip()
    if not dt_value:
        return None

    microsecond = get_microsecond(subsec_value)
    tzinfo = datetime.timezone(get_timedelta(offset_value)) if offset_value else None
    dt_value, days_delta = cut_large_hour(dt_value)
    dt = datetime.datetime.strptime(dt_value, '%Y:%m:%d %H:%M:%S')
    dt += datetime.timedelta(days=days_delta)
    dt = dt.replace(microsecond=microsecond, tzinfo=tzinfo)
    return dt


def test_get_dt_from_exif():
    for exif, suffix, dt in [
        (
            {'DateTime': '2022:04:17 15:13:50', 'SubsecTime': '00'},
            '',
            datetime.datetime(2022, 4, 17, 15, 13, 50),
        ),
        (
            {
                'DateTimeOriginal': '2022:07:09 11:39:04',
                'OffsetTimeOriginal': '+05:00',
                'SubsecTimeOriginal': '005',
            },
            'Original',
            datetime.datetime(2022, 7, 9, 11, 39, 4, 5000, tzinfo=datetime.timezone(datetime.timedelta(seconds=18000)))
        ),
        (
            {'DateTimeDigitized': '2019:09:22 24:40:46'},
            'Digitized',
            datetime.datetime(2019, 9, 23, 0, 40, 46)
        ),
        (
            {'DateTimeDigitized': '2019:09:22 14:40:46', 'SubsecTimeDigitized': '919503\x00'},
            'Digitized',
            datetime.datetime(2019, 9, 22, 14, 40, 46, 919503)
        ),
    ]:
        result = get_dt_from_exif(exif, suffix=suffix)
        assert result == dt, f'Error:\ngot:\t\t{result!r}\nexpected:\t{dt!r}'


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

    @cached_property
    def Basename(self):
        return os.path.basename(self.Path)

    @cached_property
    def extension(self):
        return self.Basename.split('.')[-1]

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
        try:
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
        except:
            log.error(f'Failed to get datetime on {self.Path!r}')
            raise

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
