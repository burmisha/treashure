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

import geojson


class Key(str, Enum):
    Year = 'year'
    Filename = 'filename'
    ShowOriginalTrack = 'show_original_track'
    ShowCleanTrack = 'show_clean_track'
    ShowPoints = 'show_points'
    PrintTimestamps = 'print_timestamps'


DEFAULTS = {
    Key.Year: 2019,
    Key.Filename: '2019-12-01-15-30-54_9C1E3054.FIT',
    # Key.Year: 2018,
    # Key.Filename: '2018-08-18-09-16-50_88I81650.FIT',
    Key.ShowOriginalTrack: True,
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
        analyze.ACTIVE_YEARS,
        analyze.ACTIVE_YEARS.index(st.session_state[Key.Year]),
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

    st.checkbox('Add original track', key=Key.ShowOriginalTrack)
    st.checkbox('Add clean track', key=Key.ShowCleanTrack)
    st.checkbox('Show points', key=Key.ShowPoints)
    st.checkbox('Print timestamps', key=Key.PrintTimestamps)

    filename = FILES_BY_NAME[st.session_state[Key.Filename]]
    track = fitreader.read_fit_file(filename, raise_on_error=False)
    st.write('Start:', track.start_ts)

    st.write('Track file:', filename)

    triangle_limit = float(st.slider('triangle limit',
        min_value=analyze.MinLimits.triangle,
        max_value=analyze.MaxLimits.triangle,
        value=analyze.DefaultLimits.triangle,
        step=analyze.Steps.triangle,
    ))
    speed_limit = float(st.slider('speed limit',
        min_value=analyze.MinLimits.speed,
        max_value=analyze.MaxLimits.speed,
        value=analyze.DefaultLimits.speed,
        step=analyze.Steps.speed,
    ))
    distance_limit = float(st.slider('distance limit',
        min_value=analyze.MinLimits.distance,
        max_value=analyze.MaxLimits.distance,
        value=analyze.DefaultLimits.distance,
        step=analyze.Steps.distance,
    ))


m = folium.Map(
    location=[track.middle_lat, track.middle_long],
    zoom_start=13,
    tiles='cartodbpositron',
    # tiles='OpenStreetMap',
)
# m.fit_bounds(track.min_max_lat_long)

def add_marker(
    *,
    point: trackpoint.TrackPoint,
    tooltip: str=None,
    color: str=None,
    icon: str=None,
    popup: str=None,
):
    marker = folium.Marker(
        point.lat_long,
        tooltip=tooltip,
        icon=folium.Icon(color=color, icon=icon),
        popup=popup,
    )
    marker.add_to(m)

add_marker(point=track.start_point, tooltip='start', color='blue', icon='play')
add_marker(point=track.finish_point, tooltip='finish', color='green', icon='stop')


def add_track(points: List[trackpoint.TrackPoint]):
    # https://geopandas.org/en/stable/gallery/polygon_plotting_with_folium.html
    # https://stackoverflow.com/questions/58032477/how-to-properly-use-key-on-in-folium-choropleths
    # https://www.nagarajbhat.com/post/folium-visualization/

    # see folium.features.Choropleth
    # for index, (start, finish) in enumerate(zip(points[:-1], points[1:])):
    #     color = '#11ffff' if index % 2 else '#ff11ff'
    #     pl = folium.vector_layers.PolyLine([start.lat_long, finish.lat_long], color=color)
    #     pl.add_to(m)

    gj = geojson.LineString([p.long_lat for p in points])
    folium.features.Choropleth(
        geo_data=gj,
        fill_color="PuBu",
    ).add_to(m)

    # if st.session_state[Key.ShowPoints]:
    #     for point in points:
    #         add_marker(point=point, popup=point.timestamp)


if st.session_state[Key.ShowOriginalTrack]:
    add_track(track.ok_points)

if st.session_state[Key.ShowCleanTrack]:
    limits = analyze.Limits(
        triangle=triangle_limit,
        speed=speed_limit,
        distance=distance_limit,
    )
    clean_track, broken_points = analyze.analyze_track(track, limits)
    st.write('Broken points count', len(broken_points))
    for point in broken_points:
        add_marker(point=point, color='red', popup=point.timestamp, icon='ban-circle')
    add_track(clean_track.ok_points)

st_data = st_folium(m, width = 725)

if st.session_state[Key.PrintTimestamps]:
    st.write('Timestamps:', [point.timestamp for point in track.ok_points])
