#!/usr/bin/env python3
import os
from library.files import Location
import pandas as pd
import plotly.express as px
from collections import defaultdict
import streamlit as st
from anytree import Node, RenderTree
from anytree.exporter import DotExporter

from logging import getLogger, basicConfig

logger = getLogger(__name__)
basicConfig(
    level='INFO',
    format='%(asctime)s.%(msecs)03d %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)

ENCODING = 'cp1251'
DIRNAME = os.path.join(Location.YandexDisk, 'Documents', '2024', '2024.12 Files')
FILES = [
	os.path.join(DIRNAME, 'dir_D_(subdirs).txt'),
	os.path.join(DIRNAME, 'dir_D_Photo_(subdirs).txt'),
	os.path.join(DIRNAME, 'dir_E_(subdirs).txt'),
	os.path.join(DIRNAME, 'dir_K_(subdirs).txt'),
	os.path.join(DIRNAME, 'dir_L_(subdirs).txt'),
	os.path.join(DIRNAME, 'dir_P_(subdirs).txt'),
]
DISK_NAMES = {'D', 'E', 'K', 'L', 'P'}

def parse_lines(lines):
    for line in lines:
        disk_name, path = line.strip().split(':')
        assert disk_name in DISK_NAMES
        parts = path.strip('\\').split('\\')
        if parts:
            yield [disk_name] + parts


def get_paths(filenames: list[str]) -> list[list[str]]:
    result = []
    for filename in filenames:
        with open(filename, encoding=ENCODING) as f:
            for path in parse_lines(f):
                result.append(path)
    return result


def build_tree(paths: list[list[str]]) -> Node:
    root = Node('HomeComputer')
    nodes = {'': root}  # используем пустую строку для корня
    
    for path in paths:
        current_node = root
        full_path = ''
        
        for part in path:
            full_path = f"{full_path}/{part}" if full_path else part
            if full_path not in nodes:
                new_node = Node(part, parent=current_node)
                # new_node = Node(full_path, parent=current_node)
                nodes[full_path] = new_node
                current_node = new_node
            else:
                current_node = nodes[full_path]
    
    return root


def count_nodes(node):
    return len(node.descendants) + 1


if __name__ == '__main__':
    paths = get_paths(FILES)
    tree = build_tree(paths)
    for pre, _, node in RenderTree(tree, maxlevel=3):
        subdirs_count = count_nodes(node)
        if subdirs_count > 1:
            print(f"{pre}{node.name} — {subdirs_count} subdirs")
        else:
            print(f"{pre}{node.name}")

# from streamlit_tree_select import tree_select

# def convert_to_streamlit_tree(node, include_node_count=True):
#     result = {
#         'label': f'{node.name} ({count_nodes(node)} nodes)' if include_node_count else node.name,
#         'value': node.name,
#         # 'checked': False,  # Добавляем состояние checkbox
#         # 'expanded': True,  # Узел развернут по умолчанию
#     }
    
#     if node.children:
#         result['children'] = [convert_to_streamlit_tree(child, include_node_count=include_node_count) for child in node.children]
    
#     return result


# def show_tree_streamlit(tree):
#     streamlit_tree = convert_to_streamlit_tree(tree)
    
#     selected = tree_select(
#         nodes=[streamlit_tree],  # Используем параметр items вместо data
#         # check=True,  # Включаем checkboxes
#         expanded=True,  # Разворачиваем все узлы по умолчанию
#     )

#     return selected

# if __name__ == '__main__':
#     st.title('File Tree Viewer')
    
#     paths = get_paths(FILES)
#     tree = build_tree(paths)
    
#     show_tree_streamlit(tree)
#     # selected_nodes = show_tree_streamlit(tree)
#     # if selected_nodes:
#     #     st.write("Selected nodes:", selected_nodes)
