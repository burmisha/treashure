from typing import List, Optional, Tuple
from functools import cached_property

import datetime
import os
import re

import attr

import PIL
import PIL.Image
import PIL.ExifTags

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


@attr.s
class PhotoFile:
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
    def Exif(self) -> dict:
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
                datetime_exif = {
                	key: value
                	for key, value in self.Exif.items()
                	if 'date' in key.lower() or 'time' in key.lower()
                }

                for key in datetime_exif:
                    if key not in KNOWN_KEYS:
                        raise RuntimeError(f'Unknown datetime key: {key!r}, value {value!r} in {self.Path}')

                if datetime_exif:
                    log.debug(f'EXIF for {self.Path}: {datetime_exif}')
                else:
                    log.debug(f'No date in EXIF for {self.Path}: {self.Exif}')

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
    res = re.search(r'^\+(\d\d):00$', offset)
    if res:
        hours = int(res.group(1))
        assert 1 <= hours <= 11
        return datetime.timedelta(seconds=3600 * hours)
    else:
        raise ValueError(f'Invalid offset: {offset!r}')



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

