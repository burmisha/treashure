from tools.running import trackpoint
from functools import cached_property
import attr

import geopy
import geopy.distance


@attr.s
class Segment(object):
    start: trackpoint.TrackPoint = attr.ib()
    finish: trackpoint.TrackPoint = attr.ib()

    @cached_property
    def distance(self) -> float:
        if not self.start.is_ok or not self.finish.is_ok:
            raise RuntimeError('Invalid segment')
        return geopy.distance.distance(
            (self.start.latitude, self.start.longitude),
            (self.finish.latitude, self.finish.longitude),
        ).km

    @cached_property
    def duration(self) -> int:
        return self.finish.timestamp - self.start.timestamp

    @cached_property
    def speed(self) -> float:
        if self.duration > 0:
            return 1000 * self.distance / self.duration  # meters per second
        return 0
