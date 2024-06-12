#!/usr/bin/env python3

from sys import stdin


def main():
    ok = set()
    count = 0
    with open('input.txt') as f:
        for index, line in enumerate(f):
            if index == 0:
                for s in line.strip():
                    ok.add(s)
            elif index == 1:
                count += sum(1 for s in line if s in ok)
            else:
                break

    with open('output.txt', 'w') as f:
        f.write(f'{count}')


if __name__ == '__main__':
    main()
