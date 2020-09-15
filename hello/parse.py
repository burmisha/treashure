#!/usr/bin/env python
import argparse
import logging
log = logging.getLogger(__file__)

import pprint

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
    def __init__(self, username):
        apiKey = u'11dbfd0f5ad9e189fedc967a9eb62f7a'
        apiSecret = u'5a2d1c64c0164e67'
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


def main(args):
    flickr = Flickr('burmisha')
    photos = list(flickr.GetPhotos('72157650399997108'))
    pprint.pprint(FormGeoJson(photos))


def CreateArgumentsParser():
    parser = argparse.ArgumentParser('Prepare photos', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--debug', help='Debug logging', action='store_true')
    return parser


if __name__ == '__main__':
    parser = CreateArgumentsParser()
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
    log.setLevel(logging.DEBUG if args.debug else logging.INFO)
    log.info('Start')
    main(args)
    log.info('Finish')
