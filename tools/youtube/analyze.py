from tools.youtube.monitor import YTVideo
from collections import defaultdict

import logging
log = logging.getLogger(__name__)


import dash
from dash import dcc
from dash import html
import plotly.express as px
import pandas as pd


class Column:
    time = 'Время (МСК)'
    views = 'Просмотры по счётчику YouTube'
    new_views_rate = 'Новые по счётчику YouTube'
    title = 'Видео'


def analyze_series(videos: dict[int, YTVideo]) -> dict:
    videos = list(videos.values())
    videos.sort(key=lambda v: v.timestamp)

    data = []
    prev_views, prev_ts = None, None
    for video in videos:
        if (prev_views is None) or (video.views > prev_views):
            if prev_views is not None:
                views_rate = (video.views - prev_views) / (video.timestamp - prev_ts) * 60
            else:
                views_rate = 0

            data.append((video.timestamp, video.views, views_rate, video.author))
            prev_views, prev_ts = video.views, video.timestamp

    df = pd.DataFrame(data, columns=[Column.time, Column.views, Column.new_views_rate, Column.title])

    df[Column.time] = pd.to_datetime(df[Column.time], unit='s', utc=True)
    df[Column.time] = df[Column.time].dt.tz_convert('Europe/Moscow')

    return df


def run_analyze(args):
    with open(args.filename) as f:
        videos = [YTVideo.from_json(row) for row in f]

    videos_by_author = defaultdict(dict)
    for video in videos:
        if video.timestamp in videos_by_author[video.author]:
            if videos_by_author[video.author][video.timestamp].title != video.title:
                videos_by_author[video.author][video.timestamp].views += video.views
                continue
        videos_by_author[video.author][video.timestamp] = video

    max_shows = lambda videos_by_ts: max(v.views for v in videos_by_ts.values())
    all_dfs = [analyze_series(series) for series in sorted(list(videos_by_author.values()), key=max_shows, reverse=True)]
    all_data = pd.concat(all_dfs)

    fig = px.line(all_data, x=Column.time, y=Column.views, color=Column.title, title='Все сразу')
    # fig = px.line(all_data, x=Column.time, y=Column.new_views_rate, color=Column.title, title='Все сразу')

    app = dash.Dash(name='june12')
    app.layout = html.Div(
        children=[
            dcc.Graph(
                id='example-graph',
                figure=fig,
                style={'height': '600px'},
            ),
        ],
    )
    app.run_server(debug=True)


def populate_parser(parser):
    parser.add_argument('--filename', help='Filename to save rows', default='june12.json')
    parser.set_defaults(func=run_analyze)
