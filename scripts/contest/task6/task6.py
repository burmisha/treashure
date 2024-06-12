#!/usr/bin/env python3

from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict


@dataclass
class DirectedGraph:
    nodes: set = field(default_factory=set)
    edges: DefaultDict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    reversed_edges: DefaultDict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def connect(self, source: str, destination: str):
        if source not in self.nodes:
            self.nodes.add(source)
        if destination not in self.nodes:
            self.nodes.add(destination)

        self.edges[source].add(destination)
        self.reversed_edges[destination].add(source)

    def delete_node(self, node: str):
        for connected_node in self.reversed_edges[node]:
            self.edges[connected_node].remove(node)

        del self.reversed_edges[node]
        self.nodes.remove(node)


def read_input(filename: str) -> list:
    result = []
    with open(filename) as f:
        for line in f:
            if not '->' in line:
                continue
            parts = line.split()
            src, dst = parts[0].strip('"'), parts[2].strip('"')
            result.append((src, dst))
    return result


def get_result(deps: list) -> list[str]:
    graph = DirectedGraph()
    for source, destination in deps:
        graph.connect(source, destination)

    result = []
    while graph.nodes:
        candidates = [node for node in graph.nodes if not graph.edges[node]]

        if not candidates:
            raise RuntimeError('Deps cycle, nothing to install')

        for node in candidates:
            graph.delete_node(node)
        result.extend(candidates)

    return result


def write_result(filename: str, result: list[str]):
    with open(filename, 'w') as f:
        for line in result:
            f.write(f'{line}\n')


def main():
    deps = read_input('input.txt')
    result = get_result(deps)
    write_result('output.txt', result)


if __name__ == '__main__':
    main()
