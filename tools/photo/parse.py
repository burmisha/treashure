import logging
log = logging.getLogger(__file__)

import pprint
import json

# https://stuvel.eu/flickrapi
import flickrapi

class Photo(object):
    def RequiredSizes(self):
        return ['Large Square', 'Original']

    def SetUrls(self, urls):
        self.LargeSquareUrl = urls['Large Square']
        self.OriginalUrl = urls['Original']

    def SetCoordinates(self, coordinates):
        self.Latitude = coordinates['latitude']
        self.Longitude = coordinates['longitude']

    def __str__(self):
        return {
            'LargeSquareUrl': self.LargeSquareUrl,
            'OriginalUrl': self.OriginalUrl,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
        }

    def __repr__(self):
        return str(self.__str__())


class Flickr(object):
    def __init__(self, *, username: str, apiKey: str, apiSecret: str):
        self.FlickrAPI = flickrapi.FlickrAPI(apiKey, apiSecret, format='parsed-json')

        nsid = self.FlickrAPI.people.findByUsername(username=username)
        self.Nsid = nsid['user']['nsid']
        log.info('nsid: %s', self.Nsid)

    def GetSizes(self, photoId, sizes):
        data = self.FlickrAPI.photos.getSizes(photo_id=photoId)
        result = {}
        availableSizes = dict((size['label'], size) for size in data['sizes']['size'])
        for size in sizes:
            result[size] = availableSizes[size]['source']
        return result

    def GetLocation(self, photoId):
        data = self.FlickrAPI.photos.geo.getLocation(photo_id=photoId)
        result = {}
        for key in ['latitude', 'longitude']:
            result[key] = data['photo']['location'][key]
        return result

    def GetPhotos(self, photosetId, maxCount=10):
        r = self.FlickrAPI.photosets.getPhotos(photoset_id=photosetId, user_id=self.Nsid)
        assert len(r['photoset']['photo']) == r['photoset']['total']
        pprint.pprint(r)
        for photoItem in r['photoset']['photo'][:maxCount]:
            photoId = photoItem['id']
            photo = Photo()
            photo.SetUrls(self.GetSizes(photoId, photo.RequiredSizes()))
            photo.SetCoordinates(self.GetLocation(photoId))
            yield photo


class MinMax(object):
    def __init__(self):
        self.Min = None
        self.Max = None
        self.Values = []

    def __call__(self, value):
        self.Values.append(value)
        v = float(value)
        if self.Min is None or v < self.Min:
            self.Min = v
        if self.Max is None or v > self.Max:
            self.Max = v

    def Median(self):
        return (self.Min + self.Max) / 2

    def Mean(self):
        # TODO: index 1 or 2 mean
        self.Values.sort()
        return self.Values[len(self.Values) / 2]


def FormGeoJson(photos):
    features = []
    minMaxLongitude = MinMax()
    minMaxLatitude = MinMax()
    for photo in photos:
        minMaxLongitude(photo.Longitude)
        minMaxLatitude(photo.Latitude)
        features.append({
            'geometry': {
                'type': 'Point',
                'coordinates': [
                    photo.Longitude,
                    photo.Latitude,
                ]
            },
            'type': 'Feature',
            'properties': {
                'O_url': photo.OriginalUrl,
                'LS_url': photo.LargeSquareUrl,
            }
        })

    data = {
        'type': 'FeatureCollection',
        'features': features,
        'view_point': [
            minMaxLongitude.Median(),
            minMaxLatitude.Median(),
        ]
    }
    return data


def run_parse(args):
    with open(args.secrets) as f:
        secrets = json.load(f)

    flickr = Flickr(
        username=secrets['flickr']['username'],
        apiKey=secrets['flickr']['api_key'],
        apiSecret=secrets['flickr']['api_secret'],
    )
    photos = list(flickr.GetPhotos('72157650399997108'))
    pprint.pprint(FormGeoJson(photos))


def populate_parser(parser):
    parser.add_argument('--debug', help='Debug logging', action='store_true')
    parser.add_argument('--secrets', help='Secrets file', default='secrets.json')
    parser.set_defaults(func=run_parse)
