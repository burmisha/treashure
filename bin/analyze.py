#!/usr/bin/env python3.9

import streamlit as st
from streamlit_folium import st_folium
import folium

import os

import library
from tools import fitreader
from tools import model
from tools import speed
from typing import List

with st.sidebar:
    years = list(range(2013, 2023))
    year = st.selectbox('Year: ', years, len(years) - 1)

    dirname = os.path.join(model.SYNC_LOCAL_DIR, str(year))

    files = {
        os.path.basename(file): file
        for file in library.files.walk(dirname, extensions=['.FIT', '.fit'])
    }

    track_name = st.selectbox(
        'Track file name',
        sorted(files.keys()),
    )

    add_clean_track = st.checkbox('Add clean track')

    track = fitreader.read_fit_file(files[track_name])
    st.write('Start:', track.start_ts)


st.write('Track file:', files[track_name])

m = folium.Map(
    location=[track.middle_lat, track.middle_long],
    zoom_start=13,
    tiles='cartodbpositron',
)
m.fit_bounds(track.min_max_lat_long)

def add_marker(point: model.GeoPoint, tooltip: str, color: str, icon: str):
    marker = folium.Marker(
        point.lat_long,
        tooltip=tooltip,
        icon=folium.Icon(color=color, icon=icon),
    )
    marker.add_to(m)

add_marker(point=track.start_point, tooltip='start', color='blue', icon='play')
add_marker(point=track.finish_point, tooltip='finish', color='green', icon='stop')


def add_track(points: List[model.GeoPoint]):
    for index, (start, finish) in enumerate(zip(points[:-1], points[1:])):
        color = '#11ffff' if index % 2 else '#ff11ff'
        pl = folium.vector_layers.PolyLine([start.lat_long, finish.lat_long], color=color)
        pl.add_to(m)

add_track(track.points)

if add_clean_track:
    clean_track = speed.analyze_track(track)
    add_track(clean_track.clean_points)


st_data = st_folium(m, width = 725)
