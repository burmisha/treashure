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

from library import md5sum
import collections

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
        raise RuntimeError('Invalid timestamp {} from {!r}'.format(timestamp, dateStr))
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


class PhotoFile(object):
    def __init__(self, pathToFile):
        self.Path = pathToFile
        self.Exif = None
        self.Basename = os.path.basename(self.Path)

    def LogMessage(self, message, base=False):
        if base:
            logMessage = '{} in basename {}'.format(message, self.Basename)
        else:
            logMessage = '{} in file {}'.format(message, self.Path)
        return logMessage

    def GetExif(self):
        with PIL.Image.open(self.Path) as image:
            if image.format == 'PNG':
                raise NoExifInPng()
            else:
                rawExif = image._getexif()
                if rawExif is None:
                    exif = None
                else:
                    # https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image
                    exif = {
                        PIL.ExifTags.TAGS[k]: v
                        for k, v in rawExif.items()
                        if k in PIL.ExifTags.TAGS
                    }
        if exif is None:
            log.warn(self.LogMessage('No exif'))
        self.Exif = exif

    def ParseGps(self):
        # https://stackoverflow.com/questions/19804768/interpreting-gps-info-of-exif-data-from-photo-in-python
        if 'GPSInfo' in self.Exif:
            gpsInfo = {
                PIL.ExifTags.GPSTAGS.get(key, key): value
                for key, value in self.Exif['GPSInfo'].items()
            }
        else:
            gpsInfo = None
        return gpsInfo

    def GetCamera(self):
        if 'Make' in self.Exif:
            camera = '{} {}'.format(self.Exif['Make'], self.Exif['Model'])
        else:
            log.debug(self.LogMessage('No camera: {!r} {!r}'.format(self.Exif.get('Make'), self.Exif.get('Model'))))
            camera = None
        return camera

    def GetDate(self):
        timestamps = set()
        filenameTimestamp = None
        if (
            re.match(r'^\d{4}(-\d{2}){2} \d{2}([-\.]\d{2}){2}( 1)?\.\w{3,4}$', self.Basename)
            or re.match(r'^\d{4}(-\d{2}){2} \d{2}([-\.]\d{2}){2}_\d{10}\.\w{3}$', self.Basename)
        ):
            filenameTimestamp = timestampFromStr(self.Basename[:19], '%Y-%m-%d %H-%M-%S')
        elif re.match(r'^wp_ss_\d{8}_\d{4}\.\w{3}$', self.Basename):
            filenameTimestamp = timestampFromStr(self.Basename[6:18], '%Y%m%d_%H%M')
        elif re.match(r'^Screenshot_\d{4}(-\d{2}){5}(-\d{3})?_.*.(png|jpg)$', self.Basename):
            # skipping subseconds
            filenameTimestamp = timestampFromStr(self.Basename[11:30], '%Y-%m-%d-%H-%M-%S')
        elif re.match(r'^IMG_\d{8}_\d{6}(_HDR|_HHT|_1)?\.(JPG|jpg|dng)$', self.Basename):
            filenameTimestamp = timestampFromStr(self.Basename[4:19], '%Y%m%d_%H%M%S')
        elif re.match(r'^WP_\d{8}(_\d{2}){3}_(Pro|Smart|Panorama|Selfie|SmartShoot).*\.jpg$', self.Basename):
            filenameTimestamp = timestampFromStr(self.Basename[3:20], '%Y%m%d_%H_%M_%S')
        elif re.match(r'^DOS-\d{4}(-\d{2}){2} \d{2}(_\d{2}){2}Z\.jpg$', self.Basename):
            filenameTimestamp = timestampFromStr(self.Basename[4:23], '%Y-%m-%d %H_%M_%S')
        else:
        # elif (
        #     re.match(r'^IMG_.*', self.Basename)
        # ):
            log.warn(self.LogMessage('Cannot get date', base=True))
        # else:
            # raise RuntimeError(self.LogMessage('Unknown name format: ', base=True))
            # log.warn(self.LogMessage('Unknown name format', base=True))
            # log.warn(self.LogMessage('Unknown name format'))
        if filenameTimestamp is not None:
            log.debug('Name {!r} has date: {}'.format(self.Basename, filenameTimestamp))
            timestamps.add(filenameTimestamp)

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
                    raise RuntimeError(self.LogMessage('Unknown datetime key: {!r} {!r}'.format(key, value)))
        timestamps = sorted(list(timestamps))
        if not timestamps:
            log.warn(self.LogMessage('No timestamps'))
            # raise RuntimeError('No timestamps')
        elif len(timestamps) > 3:
            # yes, they exist
            raise RuntimeError(self.LogMessage('Too many timestamps {}'.format(timestamps)))
        return timestamps


    def IsVsco(self):
        isVsco = False
        for key, value in self.Exif.items():
            if isinstance(value, str):
                if 'vsco' in value.lower():
                    log.debug('Is vsco: {} : {}'.format(key, value))
                    isVsco = True
        return isVsco

    def ReadInfo(self):
        log.debug('Reading {}'.format(self.Path))
        self.Md5Sum = md5sum.Md5Sum(self.Path)
        imageFormat = self.Path.split('.')[-1]
        if imageFormat.lower() in ['jpg', 'jpeg']:
            try:
                self.GetExif()
            except NoExifInPng:
                log.warn(self.LogMessage('File is PNG, not jpeg'))
        elif imageFormat in ['png', 'PNG']:
            log.debug(self.LogMessage('Png has no exif'))
        elif imageFormat in ['dng']:
            log.warn(self.LogMessage('Exif from dng is not supported'))
        else:
            raise RuntimeError('Invalid format')
        try:
            if self.Exif:
                self.GpsInfo = self.ParseGps()
                self.Camera = self.GetCamera()
            self.Timestamps = self.GetDate()
        except:
            pprint(self.Exif)
            raise


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
            photoFile = PhotoFile(filename)
            photoFile.ReadInfo()
            return photoFile
        elif extension in self.SkipExtensions:
            log.debug('Skipping {}'.format(filename))
            return None
        else:
            log.error('Unknown file extension: %r: %r', filename, extension)
            if not self.OpenedDir:
                self.OpenedDir = True
                md5sum.openDir(filename)
            # raise RuntimeError()


def getFilenames(dirs, files, excludeDirs):
    counter = 0
    for filename in files:
        counter += 1
        yield filename

    for dirName in dirs:
        for root, _, files in os.walk(dirName):
            if any(root.startswith(excludeDir) for excludeDir in excludeDirs):
                log.info('{} is excluded'.format(root))
                continue
            files = sorted(list(files))
            log.info('Found {} files in {}'.format(len(files), root))
            for filename in files:
                counter += 1
                yield os.path.join(root, filename)
                if counter % 500 == 0:
                    log.info('Yielded {} photo files'.format(counter))

    log.info('Yielded {} photo files'.format(counter))


def processDirs(args):
    photoFiles = []
    processor = Processor()
    for filename in getFilenames(args.dir, args.file, args.exclude):
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
    parser.add_argument('--exclude', help='Exclude dir from parsing', action='append', default=[])
    parser.add_argument('--file', help='Add file to parsing', action='append', default=[])
    parser.set_defaults(func=processDirs)
