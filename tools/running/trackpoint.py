from typing import Optional, List
import datetime
import attr


@attr.s
class TrackPoint:
    longitude: Optional[float] = attr.ib(default=None)
    latitude: Optional[float] = attr.ib(default=None)
    altitude: Optional[float] = attr.ib(default=None)
    timestamp: Optional[int] = attr.ib(default=None)
    cadence: Optional[int] = attr.ib(default=None)
    heart_rate: Optional[int] = attr.ib(default=None)
    distance_m: Optional[float] = attr.ib(default=None)
    speed: Optional[float] = attr.ib(default=None)

    @property
    def datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.timestamp)

    @property
    def long_lat(self) -> List[float]:
        return [self.longitude, self.latitude]

    @property
    def lat_long(self) -> List[float]:
        return [self.latitude, self.longitude]

    @property
    def is_ok(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def yandex_maps_link(self):
        text = f'{self.latitude}%2C{self.longitude}'
        ll = f'{self.longitude}%2C{self.latitude}'
        return f'https://yandex.ru/maps/?ll={ll}&mode=search&sll={ll}&text={text}&z=15'
