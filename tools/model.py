from typing import List, Optional
import attr

@attr.s
class GeoPoint(object):
    longitude: float = attr.ib(default=None)
    latitude: float = attr.ib(default=None)
    altitude: Optional[float] = attr.ib(default=None)
    timestamp: Optional[float] = attr.ib(default=None)
    cadence: Optional[float] = attr.ib(default=None)
    heart_rate: Optional[float] = attr.ib(default=None)

    @property
    def datetime(self):
        return datetime.datetime.fromtimestamp(self.timestamp)

    def __str__(self):
        return {
            'Lng': self.longitude,
            'Lat': self.latitude,
            'Alt': self.altitude,
            'Ts': self.timestamp,
            'Dt': self.datetime,
        }
