from xml.etree import ElementTree
import gpxpy.gpx

import logging
log = logging.getLogger(__name__)


class GpxWriter(object):
    def __init__(self, filename: str):
        self.__Points = []
        self.__filename = filename
        assert self.__filename.endswith('.gpx')

    def AddPoints(self, points):
        for point in points:
            gpxTrackPoint = gpxpy.gpx.GPXTrackPoint(
                latitude=point.latitude,
                longitude=point.longitude,
                elevation=point.altitude,
                time=point.datetime,
            )
            count = 0
            namespace = '{gpxtpx}'
            extensionElement = ElementTree.Element(namespace + 'TrackPointExtension')
            for suffix, value in [
                ('hr', point.heart_rate),
                ('cad', point.cadence),
            ]:
                if value:
                    count += 1
                    subElement = ElementTree.Element(namespace + suffix)
                    subElement.text = str(value)
                    extensionElement.insert(count, subElement)
            if count:
                gpxTrackPoint.extensions.append(extensionElement)
            self.__Points.append(gpxTrackPoint)

    def HasPoints(self):
        return len(self.__Points) > 0

    def ToXml(self):
        if not self.__Points:
            raise RuntimeError('No points')

        log.debug('Create GPX')
        gpx = gpxpy.gpx.GPX()
        gpx.nsmap = {
            'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
        }

        log.debug('Create first track in GPX')
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        log.debug('Create first segment in GPX track')
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        log.debug('Add points to segment in GPX track')
        self.__Points.sort(key=lambda point: point.time)
        gpx_segment.points.extend(self.__Points)

        return gpx.to_xml()

    def Save(self):
        assert self.__Points
        log.info(f'Writing {len(self.__Points)} points to {self.__filename}')
        with open(self.__filename, 'w') as f:
            f.write(self.ToXml())

