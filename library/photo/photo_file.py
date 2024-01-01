from typing import List, Optional, Tuple
from functools import cached_property

import datetime
import os
import re

import attr

import PIL
import PIL.Image
import PIL.ExifTags
import PIL.TiffTags

import library.md5sum
from library.photo.parse_timestamp import parse_timestamp

import logging
log = logging.getLogger(__name__)

PIL.Image.MAX_IMAGE_PIXELS = 200 * 1024 * 1024

KNOWN_KEYS = {
    'DateTime', 'OffsetTime', 'SubsecTime',
    'DateTimeDigitized', 'OffsetTimeDigitized', 'SubsecTimeDigitized',
    'DateTimeOriginal', 'OffsetTimeOriginal', 'SubsecTimeOriginal',
    'ExposureTime', 'CompositeImageExposureTimes',
}


@attr.s
class PhotoInfo:
    path: str = attr.ib()
    md5sum: str = attr.ib()
    timestamps: List[int] = attr.ib()

    @classmethod
    def from_dict(cls, data: dict):
	    return cls(
	        path=data['path'],
	        md5sum=data['md5sum'],
	        timestamps=data['timestamps'],
	    )


SKIP_TIFF_TAGS = {50935, 50936, 50940} # https://www.awaresystems.be/imaging/tiff/tifftags/private.html


def parse_tiff_exif(data: dict) -> dict:
    # https://stackoverflow.com/questions/46477712/reading-tiff-image-metadata-in-python
    result = {}
    for key, value in data.items():
        if key not in PIL.TiffTags.TAGS:
            if key in SKIP_TIFF_TAGS:
                continue
            else:
                log.error(f'Unknown key {key!r} for {value!r}')
                raise ValueError(f'Unknown key {key!r} for {value!r}')

        if isinstance(value, tuple) and len(value) == 1:
            value = value[0]

        result[PIL.TiffTags.TAGS[key]] = value


    return result


def parse_jpg_exif(data: dict) -> dict:
    # https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image
    result = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in data.items()
        if k in PIL.ExifTags.TAGS
    }

    return result

def get_exif(filename: str) -> Optional[dict]:
    with PIL.Image.open(filename) as image:
        if image.format == 'TIFF':
            return parse_tiff_exif(image.tag)
        elif image.format == 'PNG':
            return None
        else:
            exif = image._getexif()
            if exif is None:
                return None
            return parse_jpg_exif(exif)


class PhotoFileAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return '[%s] %s' % (self.extra['filename'], msg), kwargs


class PhotoFile:
    def __init__(self, filename):
        self.Path = filename
        short_name = self.Path.removeprefix(library.files.Location.YandexDisk).lstrip(os.sep)
        self.log = PhotoFileAdapter(logging.getLogger(__name__), {'filename': short_name})

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
    def Exif(self) -> Optional[dict]:
        exif = get_exif(self.Path)
        # if exif:
        #     msg = ['Exif: ']
        #     for key, value in sorted(exif.items()):
        #         msg.append(f'\t{key}: {value} ')
        #     self.log.info('\n'.join(msg))
        return exif

    @cached_property
    def GpsInfo(self) -> dict:
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
                self.log.debug(f'No camera: make {make!r}, model {model!r}')

        return None

    @cached_property
    def filename_dt(self):
        filename_ts = parse_timestamp(self.Basename)
        if filename_ts:
            filename_dt = datetime.datetime.utcfromtimestamp(filename_ts)
            local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
            filename_dt = filename_dt.replace(tzinfo=local_timezone)
            return filename_dt

        log.debug(f'Name {self.Basename!r} has no date')
        return None

    @cached_property
    def datetime(self) -> Optional[datetime.datetime]:
        try:
            if self.Exif:
                datetime_exif = {
                	key: value
                	for key, value in self.Exif.items()
                	if 'date' in key.lower() or 'time' in key.lower()
                }

                for key in datetime_exif:
                    if key not in KNOWN_KEYS:
                        raise RuntimeError(f'Unknown datetime key: {key!r}, value {value!r} in {self.Path}')

                if datetime_exif:
                    log.debug(f'EXIF: {datetime_exif}')
                else:
                    log.debug(f'No date in EXIF: {self.Exif}')

                original_dt = get_dt_from_exif(self.Exif, 'Original')
                if original_dt:
                    return original_dt

                digitized_dt = get_dt_from_exif(self.Exif, 'Digitized')
                if digitized_dt:
                    return digitized_dt

                if self.filename_dt:
                    return self.filename_dt

                modification_dt = get_dt_from_exif(self.Exif, '')
                if modification_dt:
                    self.log.warn(f'Using default dt: {datetime_exif}')
                    return modification_dt

            else:
                self.log.warn(f'No EXIF')

            if self.filename_dt:
                self.log.warn(f'Using filename dt')
                return self.filename_dt

        except:
            self.log.error(f'Failed to get datetime')
            if self.Exif:
                self.log.error(f'Exif {self.Exif}')

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
            for value in self.Exif.values():
                if isinstance(value, str) and 'vsco' in value.lower():
                    return True

        return False

    @cached_property
    def Md5Sum(self) -> str:
        return library.md5sum.md5sum(self.Path)


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


def get_timedelta(offset: str) -> datetime.timedelta:
    offset = offset.strip('\x00')
    res = re.search(r'^\+(\d\d):00$', offset)
    if res:
        hours = int(res.group(1))
        assert 1 <= hours <= 11
        return datetime.timedelta(seconds=3600 * hours)
    else:
        raise ValueError(f'Invalid offset: {offset!r}')


def get_dt_from_exif(exif: dict, suffix: str):
    dt_value = exif.get(f'DateTime{suffix}')
    offset_value = exif.get(f'OffsetTime{suffix}', '')
    subsec_value = exif.get(f'SubsecTime{suffix}')

    if not dt_value:
        return None

    dt_value = dt_value.strip()
    if not dt_value:
        return None

    offset_value = offset_value.strip()
    if offset_value == ':':
        return None

    microsecond = get_microsecond(subsec_value)
    tzinfo = datetime.timezone(get_timedelta(offset_value)) if offset_value else None
    dt_value, days_delta = cut_large_hour(dt_value)
    dt = datetime.datetime.strptime(dt_value, '%Y:%m:%d %H:%M:%S')
    dt += datetime.timedelta(days=days_delta)
    dt = dt.replace(microsecond=microsecond, tzinfo=tzinfo)
    return dt


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
