from pytube import YouTube
from dataclasses import dataclass, asdict
from typing import Optional
import json
import time
import sys

import logging
log = logging.getLogger(__name__)


@dataclass
class YTVideo:
    timestamp: int
    views: int
    title: str
    author: str

    def to_row(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'), ensure_ascii=False)

    @classmethod
    def from_json(cls, row: str):
        data = json.loads(row)
        return cls(
            author=data['author'],
            views=data['views'],
            title=data['title'],
            timestamp=data['timestamp'],
        )

    @classmethod
    def from_pytype_video(cls, video: YouTube, timestamp: int):
        return cls(
            author=video.author,
            views=video.views,
            title=video.title,
            timestamp=timestamp,
        )


# https://www.youtube.com/hashtag/тынеодин
YOUTUBE_LINKS = [
    'https://www.youtube.com/watch?v=fh1Z2Lrzxyw',
    'https://www.youtube.com/watch?v=SRM3_QzM7Uw',
    'https://www.youtube.com/watch?v=3aopl3Jg2Zc',
    'https://www.youtube.com/watch?v=O963hdbB408',
    'https://www.youtube.com/watch?v=7ZHGeOg7ULM',
    'https://www.youtube.com/watch?v=p32muLvJ1KQ',
    'https://www.youtube.com/watch?v=wO_MlCOy4GQ',
    'https://www.youtube.com/watch?v=1y5cYkqkQMY',
    'https://www.youtube.com/watch?v=UxajY6Yml9U',
    'https://www.youtube.com/watch?v=7r4FC0uOZLc',
    'https://www.youtube.com/watch?v=ev8jH-qUzCo',
    'https://www.youtube.com/watch?v=8NtkNlZYaBs',
    'https://www.youtube.com/watch?v=KFQcla-jth4',
    'https://www.youtube.com/watch?v=jXG2epJUQX8',
    'https://www.youtube.com/watch?v=TcafRe-Qo5A',
    'https://www.youtube.com/watch?v=_9HN5QCLVo0',
    'https://www.youtube.com/watch?v=0tpOAVtpDos',
    'https://www.youtube.com/watch?v=2V6hXfhe618',
    'https://www.youtube.com/watch?v=XRYLFOcti7g',
    'https://www.youtube.com/watch?v=nFaXeLnbMgM',
    'https://www.youtube.com/watch?v=39JevUzdBXA',
    'https://www.youtube.com/watch?v=6IY08DJA-hA',
    'https://www.youtube.com/watch?v=D2fiK0sYp2s',
    'https://www.youtube.com/watch?v=NTw5Ln8p1xg',
    'https://www.youtube.com/watch?v=nmIJlWT1nkQ',
    'https://www.youtube.com/watch?v=fu0NG9CdWSo',
    'https://www.youtube.com/watch?v=Edb5FZZDR1M',
    'https://www.youtube.com/watch?v=4HbBUVBPoAQ',
    'https://www.youtube.com/watch?v=m5SrkcLN_kc',
    'https://www.youtube.com/watch?v=7glC0exEZYA',
    'https://www.youtube.com/watch?v=B6DkWTW5v6A',
    'https://www.youtube.com/watch?v=2hgxogKNAzU',
    'https://www.youtube.com/watch?v=cvUeTRTIffU',
    'https://www.youtube.com/watch?v=XzUlUJFFwW8',
    'https://www.youtube.com/watch?v=Zrz4Tsc5zxs',
]


def now() -> int:
    return int(time.time())


def get_videos(links: list[str]) -> list[YTVideo]:
    timestamp = now()

    log.info(f'Getting {len(links)} videos at {timestamp} ...')

    videos = [YTVideo.from_pytype_video(YouTube(link), timestamp) for link in links]
    videos.sort(key=lambda v: (v.author, v.title))

    return videos


def save_videos(videos: list[YTVideo], filename: str):
    log.info(f'Adding {len(videos)} videos to {filename}')
    with open(filename, 'a') as f:
        for video in videos:
            if not isinstance(video, YTVideo):
                raise RuntimeError(f'Invalid {video}')
            f.write(f'{video.to_row()}\n')


def run_monitor(args):
    while True:
        try:
            videos = get_videos(YOUTUBE_LINKS)
            for video in videos:
                log.info(video)
            save_videos(videos, args.filename)
        except Exception as e:
            log.exception(f'Got error: {e}, skipping')

        log.info(f'Sleeping for {args.sleep_time} seconds')
        time.sleep(args.sleep_time)


def populate_parser(parser):
    parser.add_argument('--filename', help='Filename to save rows', default='june12.json')
    parser.add_argument('--sleep-time', help='Sleep time in seconds', default=600, type=int)
    parser.set_defaults(func=run_monitor)
