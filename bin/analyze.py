#!/usr/bin/env python3.9

import streamlit as st
from streamlit_folium import st_folium
import folium

import os

import library
from tools import fitreader
from tools import model


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

    track = fitreader.read_fit_file(files[track_name])
    st.write('Start:', track.start_ts)


st.write('Track file:', files[track_name])

m = folium.Map(
    location=[track.middle_lat, track.middle_long],
    zoom_start=13,
    tiles='cartodbpositron',
)
m.fit_bounds(track.min_max_lat_long)

start_marker = folium.Marker(
    track.start_point.lat_long,
    tooltip='start',
    icon=folium.Icon(color='blue', icon='play'),
)
start_marker.add_to(m)
finish_marker = folium.Marker(
    track.finish_point.lat_long,
    tooltip='finish',
    icon=folium.Icon(color='green', icon='stop'),
)
finish_marker.add_to(m)

for index, (seg_start, seg_finish) in enumerate(zip(track.points[:-1], track.points[1:])):
    color = '#11ffff' if index % 2 else '#ff11ff'
    pl = folium.vector_layers.PolyLine([seg_start.lat_long, seg_finish.lat_long], color=color)
    pl.add_to(m)

st_data = st_folium(m, width = 725)
