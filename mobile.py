#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import md5sum
# import json
import os
import PIL
import PIL.Image
import PIL.ExifTags

from pprint import pprint

from collections import defaultdict

import logging
import re
log = logging.getLogger(__file__)

class NoExifInPng(Exception):
    pass

class PhotoFile(object):
    def __init__(self, pathToFile):
        self.Path = pathToFile
        self.Exif = None

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
                    exif = { PIL.ExifTags.TAGS[k]: v for k, v in rawExif.iteritems() if k in PIL.ExifTags.TAGS }
        if exif is None:
            log.warn('No exif')
        self.Exif = exif

    def ParseGps(self):
        # https://stackoverflow.com/questions/19804768/interpreting-gps-info-of-exif-data-from-photo-in-python
        if 'GPSInfo' in self.Exif:
            gpsInfo = { PIL.ExifTags.GPSTAGS.get(key, key): value for key, value in self.Exif['GPSInfo'].iteritems() }
        else:
            gpsInfo = None
        return gpsInfo

    def GetCamera(self):
        if 'Make' in self.Exif:
            camera = '{} {}'.format(self.Exif['Make'], self.Exif['Model'])
        else:
            log.debug('No camera: {!r} {!r}'.format(self.Exif.get('Make'), self.Exif.get('Model')))
            camera = None
        return camera

    def GetDate(self, basename):
        if (
            re.match(r'^\d{4}(.\d\d){2} \d\d(.\d\d){2}( 1)?\..{3}$', basename)
            or re.match(r'^\d{4}(.\d\d){2} \d\d(.\d\d){2}_\d{10}\..{3}$', basename)
        ):
            log.debug('Name has date')
        elif (
            re.match(r'^IMG_.*', basename)
        ):
            log.debug('Name has no date')
        else:
            raise
        if self.Exif:
            times = set()
            isVsco = self.IsVsco()
            for key, value in self.Exif.iteritems():
                lowerKey = key.lower()
                if key in [
                    'DateTime',
                    'DateTimeDigitized',
                    'DateTimeOriginal',
                ]:
                    assert re.match(r'^\d{4}(:\d\d){2} (\d\d)(:\d\d){2}$', value)
                    times.add(value)
                elif key in [
                    'SubsecTime',
                    'SubsecTimeDigitized',
                    'SubsecTimeOriginal',
                    'ExposureTime',
                ]:
                    pass
                elif 'date' in lowerKey or 'time' in lowerKey:
                    raise RuntimeError('Unknown datetime key: {!r} {!r}'.format(key, value))

    def IsVsco(self):
        isVsco = False
        for key, value in self.Exif.iteritems():
            if isinstance(value, (unicode, str)):
                if 'vsco' in value.lower():
                    log.debug('Is vsco: {} : {}'.format(key, value))
                    isVsco = True
        return isVsco

    def ReadInfo(self):
        log.debug('Reading {}'.format(self.Path))
        md5 = md5sum.Md5Sum(self.Path)
        imageFormat = self.Path.split('.')[-1]
        if imageFormat.lower() in ['jpg', 'jpeg']:
            try:
                self.GetExif()
            except NoExifInPng:
                log.warn('File is PNG, not jpeg')
        elif imageFormat in ['png', 'PNG']:
            log.warn('Png has no exif')
        else:
            raise RuntimeError('Invalid format')
        try:
            if self.Exif:
                gpsInfo = self.ParseGps()
                camera = self.GetCamera()
                self.GetDate(os.path.basename(self.Path))
        except:
            pprint(self.Exif)
            raise

class Processor(object):
    def __init__(self):
        self.ParseExtensions = [ 'jpg', 'jpeg', 'png' ]
        self.SkipExtensions = [ 'ds_store', 'mp4', 'mov', 'nar', 'icon' ]

    def __call__(self, filename):
        extension = os.path.basename(filename).split('.')[-1].lower().strip()
        photoFile = None
        if extension in self.ParseExtensions:
            photoFile = PhotoFile(filename)
            photoFile.ReadInfo()
        elif extension in self.SkipExtensions:
            log.debug('Skipping {}'.format(filename))
        else:
            raise RuntimeError('Unknown file extension: {!r}: {!r}'.format(filename, extension))
        return photoFile


def main(args):
    processor = Processor()
    for dirName in args.dir:
        for root, _, files in os.walk(dirName):
            files = list(files)
            log.info('Found {} files in {}'.format(len(files), root))
            for filename in files:
                processor(os.path.join(root, filename))

    for filename in args.file:
        processor(filename)


def CreateArgumentsParser():
    parser = argparse.ArgumentParser('Organize mobile photos')
    parser.add_argument('--debug', help='Debug logging', action='store_true')
    # subparsers = parser.add_subparsers(help='Modes')

    # dirsParser = subparsers.add_parser('dirs', help='Process many dirs')
    parser.add_argument('--dir', help='Add dir to parsing', action='append', default=[])
    parser.add_argument('--file', help='Add file to parsing', action='append', default=[])
    # parser.set_defaults(func=processDirs)

    # fileParser = subparsers.add_parser('file', help='Process files one by one')
    # fileParser.set_defaults(func=processDirs)
    return parser

if __name__ == '__main__':
    parser = CreateArgumentsParser()
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    log.setLevel(logging.DEBUG if args.debug else logging.INFO)
    main(args)
