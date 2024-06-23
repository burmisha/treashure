import os

from library.files import Location
from library.youtube.download import download_target
from library.youtube.target import DownloadTarget
from tools.youtube import data

from tqdm import tqdm

import logging
log = logging.getLogger(__name__)


def get_targets() -> list[DownloadTarget]:
    anarchy_targets = list(data.ANARCHY_TARGETS)
    for index, target in enumerate(anarchy_targets):
        anarchy_targets[index].custom_tags = {
            '\xa9nam': target.name,
            '\xa9ART': 'АО',
            '\xa9wrt': 'mariarakhmaninova.com',
            '\xa9cmt': f'Source: {target.url}',
        }
        anarchy_targets[index].output_path = os.path.join(Location.Downloads, 'Анархическое образование')

    return anarchy_targets


def run_download(args):
    for target in tqdm(get_targets(), desc='All targets'):
        download_target(
            target=target,
            download_video=args.do_video,
            download_audio=args.do_audio,
        )


def populate_parser(parser):
    parser.add_argument('--do-audio', help='Download audio', action='store_true')
    parser.add_argument('--do-video', help='Download video', action='store_true')
    parser.set_defaults(func=run_download)
