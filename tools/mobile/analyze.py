import collections
from tools.mobile.mobile import fromDict

import logging
log = logging.getLogger(__name__)


def analyze(args):
    with open(args.json_file) as f:
        res = json.load(f)
    photoFiles = collections.defaultdict(list)
    for item in res:
        photoFile = fromDict(item)
        photoFiles[photoFile.Md5Sum].append(photoFile)

    for md5sumValue, photoFilesList in photoFiles.iteritems():
        if len(photoFilesList) > 1:
            log.info(u'Duplicates: {}\n  {}'.format(
                md5sumValue,
                '\n  '.join(photoFile.Path for photoFile in photoFilesList)
            ))


def populate_parser(parser):
    parser.add_argument('--json-file', help='Json file to store all data', default='data.json')
    parser.set_defaults(func=analyze)
