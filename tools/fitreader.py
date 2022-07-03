import fitparse
import datetime

import pprint
import os

from tools.model import GeoPoint

import logging
log = logging.getLogger(__name__)


class ErrorThreshold:
    MIN_COUNT = 200
    SHARE = 0.4


class FitReader(object):
    def __init__(self, filename):
        self.__Filename = filename
        self.__Points = []
        self.IsValid = True
        self.FirstTimestamp = None
        self.__load_oints()

    @property
    def description(self):
        return os.path.basename(self.__Filename)

    @property
    def filename(self):
        return self.__Filename

    def __FromSemicircles(self, value):
        # https://forums.garmin.com/forum/developers/garmin-developer-information/60220-
        return float(value) * 180 / (2 ** 31)

    def __load_oints(self):
        log.debug(f'Loading {self.__Filename}')
        try:
            fitFile = fitparse.FitFile(self.__Filename, check_crc=True)
        except fitparse.utils.FitCRCError:
            log.warning(f'FitCRCError on {self.__Filename}', )
            fitFile = fitparse.FitFile(self.__Filename, check_crc=False)
        fitFile.parse()

        count = 0
        failures = []
        for count, message in enumerate(fitFile.get_messages(name='record'), 1):
            values = message.get_values()
            timestamp = int((values['timestamp'] - datetime.datetime(1970, 1, 1)).total_seconds())
            if count == 1:
                log.debug('First timestamp: %s', values['timestamp'])
                self.FirstTimestamp = timestamp
            log.debug(f'Values: {values}')
            try:
                assert timestamp > 100000000
                if 'enhanced_altitude' in values:
                    assert values['enhanced_altitude'] == values['altitude']
                if values.get('position_long') is None or values.get('position_lat') is None:
                    failures.append(count)
                    continue
                geo_point = GeoPoint(
                    longitude=self.__FromSemicircles(values['position_long']),
                    latitude=self.__FromSemicircles(values['position_lat']),
                    altitude=values['altitude'],
                    cadence=values.get('cadence') or None,
                    heart_rate=values.get('heart_rate') or None,
                    timestamp=timestamp,
                )
                self.__Points.append(geo_point)
            except:
                log.exception('Complete failure on %s in file %s', count, self.__Filename)
                pprint.pprint(values)
                raise

        if len(failures) > ErrorThreshold.MIN_COUNT or len(failures) > ErrorThreshold.SHARE * count:
            self.IsValid = False

        ok_str = 'ok' if self.IsValid else 'not ok'
        if failures:
            log.info(
                f'File {self.__Filename} is {ok_str}: {count} points '
                f'and {len(failures)} failures, {failures[:3]} (3 first ones)', 
            )
        else:
            log.debug('File {self.__Filename} is {ok_str}: {count} points')

    def Load(self, raise_on_error=True):
        if raise_on_error and not self.IsValid:
            log.error('Error')
            raise RuntimeError('Too many failures')

        for point in self.__Points:
            yield point
