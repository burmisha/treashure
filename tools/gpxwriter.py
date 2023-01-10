from xml.etree import ElementTree
import gpxpy.gpx

import logging
log = logging.getLogger(__name__)

NAMESPACE = 'gpxtpx'


def _to_track_point(point) -> gpxpy.gpx.GPXTrackPoint:
    gpxTrackPoint = gpxpy.gpx.GPXTrackPoint(
        latitude=point.latitude,
        longitude=point.longitude,
        elevation=point.altitude,
        time=point.datetime,
    )

    point_extension = ElementTree.Element(f'{{{NAMESPACE}}}TrackPointExtension')

    count = 0
    for element_name, value in [
        (f'{{{NAMESPACE}}}hr', point.heart_rate),
        (f'{{{NAMESPACE}}}cad', point.cadence),
    ]:
        if value:
            count += 1
            element = ElementTree.Element(element_name)
            element.text = str(value)
            point_extension.insert(count, element)

    if count:
        gpxTrackPoint.extensions.append(point_extension)

    return gpxTrackPoint


def save_gpx(gpx: list, filename: str):
    log.info(f'Save GPX: {filename!r} with {len(gpx.tracks[0].segments[0].points)} points')
    assert filename.endswith('.gpx')
    assert gpx.tracks[0].segments[0].points
    with open(filename, 'w') as f:
        f.write(gpx.to_xml())


def to_gpx(points: list) -> gpxpy.gpx.GPX:
    track_points = [_to_track_point(point) for point in points]
    track_points.sort(key=lambda track_point: track_point.time)

    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_segment.points.extend(track_points)

    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.segments.append(gpx_segment)

    gpx_file = gpxpy.gpx.GPX()
    gpx_file.nsmap = {
        NAMESPACE: 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
    }
    gpx_file.tracks.append(gpx_track)

    return gpx_file
