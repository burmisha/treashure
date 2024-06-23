import os
from tqdm import tqdm
from library.process import run
from library.youtube.target import DownloadTarget

from pytube import YouTube
from mutagen.mp4 import MP4


import logging
log = logging.getLogger(__name__)


def on_progress(stream, chunk, bytes_remaining):
    global pbar
    pbar.update(len(chunk))


def on_complete(stream, file_path):
    global pbar
    pbar.close()



def join_files(*, video_file: str, audio_file: str, result_file: str):
    command = [
        'ffmpeg',
        '-i', video_file,
        '-i', audio_file,
        '-c', 'copy',
        result_file
    ]
    run(command)


def get_streams(streams):
    for stream in streams:
        log.info(f'    Available {stream}')

    video_streams = streams.filter(res='1080p', type='video')
    if not video_streams:
        log.info(f'    Using 720p')
        video_streams = streams.filter(res='720p', type='video')
    else:
        log.info(f'    Using 1080p')

    if not video_streams:
        raise RuntimeError('No video streams')

    video_streams.order_by('resolution').desc()
    video_stream = video_streams.first()

    audio_streams = streams.filter(type='audio')
    audio_streams.order_by('abr').desc()
    audio_stream = audio_streams.first()
    return video_stream, audio_stream


def download_target(
    *,
    target: DownloadTarget,
    download_video: bool = False,
    download_audio: bool = False,
):
    audio_file = os.path.join(target.output_path, target.audio_filename)
    video_file = os.path.join(target.output_path, target.video_filename)
    result_file = os.path.join(target.output_path, target.result_filename)

    audio_is_missing = download_audio and not os.path.isfile(audio_file)
    video_is_missing = download_video and not os.path.isfile(result_file)

    if not audio_is_missing and not video_is_missing:
        return

    log.info(f'New target: {target.name!r} ({target.url})')

    yt = YouTube(
        target.url,
        on_progress_callback=on_progress,
        on_complete_callback=on_complete,
    )

    video_stream, audio_stream = get_streams(yt.streams)

    global pbar

    if audio_is_missing or video_is_missing:
        pbar = tqdm(total=audio_stream.filesize, unit='B', unit_scale=True, desc='Downloading audio stream')
        audio_stream.download(output_path=target.output_path, filename=target.audio_filename)

        if target.custom_tags:
            audio_tags = MP4(audio_file)
            for key, value in target.custom_tags.items():
                audio_tags[key] = value
            audio_tags.save()

    if video_is_missing:
        pbar = tqdm(total=video_stream.filesize, unit='B', unit_scale=True, desc='Downloading video stream')
        video_stream.download(output_path=target.output_path, filename=target.video_filename)
        join_files(
            video_file=video_file,
            audio_file=audio_file,
            result_file=result_file,
        )
        os.remove(os.path.join(target.output_path, target.video_filename))

