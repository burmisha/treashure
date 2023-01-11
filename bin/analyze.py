#!/usr/bin/env python3.9

import streamlit as st
from streamlit_folium import st_folium
import folium

import os

import library
from tools.running import fitreader
from tools.running import dirname
from tools.running.process import analyze
from tools.running import trackpoint
from typing import List

from enum import Enum

YEARS = list(range(2013, 2023))


class Key(str, Enum):
    Year = 'year'
    Filename = 'filename'
    ShowCleanTrack = 'add_clean'
    ShowPoints = 'show_points'
    PrintTimestamps = 'print_timestamps'


DEFAULTS = {
    Key.Year: 2019,
    Key.Filename: '2019-12-01-15-30-54_9C1E3054.FIT',
    Key.ShowCleanTrack: False,
    Key.ShowPoints: False,
    Key.PrintTimestamps: False,
}

for key, default_value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


FILES_BY_NAME = {
    os.path.basename(file): file
    for file in library.files.walk(
        dirname.SYNC_LOCAL_DIR,
        extensions=['.FIT', '.fit']
    )
}


def switch_to_next_file():
    names = available_names()
    index = names.index(st.session_state[Key.Filename])
    next_index = index + 1
    if next_index < len(names):
        st.session_state[Key.Filename] = names[next_index]


def available_names():
    return sorted([name for name, file in FILES_BY_NAME.items() if f'/{st.session_state[Key.Year]}/' in file])


with st.sidebar:
    st.selectbox(
        'Year: ',
        YEARS,
        YEARS.index(st.session_state[Key.Year]),
        key=Key.Year,
    )

    dirname = os.path.join(dirname.SYNC_LOCAL_DIR, str(st.session_state[Key.Year]))

    sorted_keys = available_names()
    default_index = 0
    if st.session_state[Key.Filename] in sorted_keys:
        default_index = sorted_keys.index(st.session_state[Key.Filename])

    st.selectbox(
        'Track file name',
        sorted_keys,
        index=default_index,
        key=Key.Filename,
    )
    st.button('Next track', on_click=switch_to_next_file)

    st.checkbox('Add clean track', key=Key.ShowCleanTrack)
    st.checkbox('Show points', key=Key.ShowPoints)
    st.checkbox('Print timestamps', key=Key.PrintTimestamps)

    filename = FILES_BY_NAME[st.session_state[Key.Filename]]
    track = fitreader.read_fit_file(filename, raise_on_error=False)
    st.write('Start:', track.start_ts)

    st.write('Track file:', filename)

    speed_limit = int(st.slider('speed limit', min_value=0, max_value=10, value=analyze.DEFAULT_SPEED_LIMIT))
    distance_limit = int(st.slider('distance limit', min_value=0, max_value=10, value=analyze.DEFAULT_DISTANCE_LIMIT))


m = folium.Map(
    location=[track.middle_lat, track.middle_long],
    zoom_start=13,
    tiles='cartodbpositron',
)
m.fit_bounds(track.min_max_lat_long)

def add_marker(point: trackpoint.TrackPoint, tooltip: str, color: str, icon: str):
    marker = folium.Marker(
        point.lat_long,
        tooltip=tooltip,
        icon=folium.Icon(color=color, icon=icon),
    )
    marker.add_to(m)

add_marker(point=track.start_point, tooltip='start', color='blue', icon='play')
add_marker(point=track.finish_point, tooltip='finish', color='green', icon='stop')


def add_track(points: List[trackpoint.TrackPoint]):
    for index, (start, finish) in enumerate(zip(points[:-1], points[1:])):
        color = '#11ffff' if index % 2 else '#ff11ff'
        pl = folium.vector_layers.PolyLine([start.lat_long, finish.lat_long], color=color)
        pl.add_to(m)

    if st.session_state[Key.ShowPoints]:
        for point in points:
            folium.Marker(point.lat_long, popup=point.timestamp).add_to(m)


add_track(track.ok_points)


# if st.session_state[Key.ShowCleanTrack]:
#     clean_track = analyze.analyze_track(track, speed_limit=speed_limit, distance_limit=distance_limit)
#     add_track(clean_track.ok_points)


st_data = st_folium(m, width = 725)

if st.session_state[Key.PrintTimestamps]:
    st.write('Timestamps:', [point.timestamp for point in track.ok_points])
