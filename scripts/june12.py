#!/usr/bin/env python3

from pytube import YouTube, Channel
from dataclasses import dataclass, asdict
from typing import Optional
import json
import time
import sys


@dataclass
class YTVideo:
    timestamp: int
    views: int
    rating: Optional[float]
    title: str
    author: str

    def to_row(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'), ensure_ascii=False)


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
    # 'https://www.youtube.com/watch?v=3aopl3Jg2Zc',
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
    videos = []
    for link in links:
        video = YouTube(link)
        yt_video = YTVideo(
            author=video.author,
            views=video.views,
            rating=video.rating,
            title=video.title,
            timestamp=timestamp,
        )
        videos.append(yt_video)

    videos.sort(key=lambda v: (v.author, v.title))

    for video in videos:
        print(video)

    return videos


def save_videos(videos: list[YTVideo], filename: str):
    with open(filename, 'a') as f:
        for video in videos:
            if not isinstance(video, YTVideo):
                raise RuntimeError(f'Invalid {video}')
            f.write(f'{video.to_row()}\n')


def main():
    while True:
        try:
            videos = get_videos(YOUTUBE_LINKS)
            save_videos(videos, 'june12.txt')
        except Exception as e:
            print(f'Got error: {e}')

        print('Sleeping')
        time.sleep(60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        sys.exit(1)
