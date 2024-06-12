#!/usr/bin/env python3

from sys import stdin


def parse_stdin():
    parts = []
    for line in stdin:
        for part in line.split():
            parts.append(int(part))
    return parts


def main():
    print(sum(parse_stdin()))


if __name__ == '__main__':
    main()
