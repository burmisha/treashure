#!/usr/bin/env python3


def read_input(filename: str) -> list:
    n = -1

    result = []
    with open(filename) as f:
        for index, line in enumerate(f):
            if index == 0:
                n = int(line.strip())
            elif line.strip():
                start, finish = line.strip().split()
                start, finish = int(start), int(finish)
                if start >= finish:
                    raise RuntimeError('Invalid input order')
                result.append((start, finish))

    if len(result) == n:
        raise RuntimeError('Invalid input length')

    return result


def get_result(sessions: list) -> int:
    pairs = []
    for session in sessions:
        pairs.append((session[0], 1))
        pairs.append((session[1], -1))
    pairs.sort()

    currect_count = 0
    max_count = -1
    result = None
    for timestamp, delta in pairs:
        currect_count += delta
        if currect_count > max_count:
            result = timestamp
            max_count = currect_count

    return result


def write_result(filename: str, result: int) -> int:
    with open(filename, 'w') as f:
        f.write(f'{result}\n')


def main():
    sessions = read_input('input.txt')
    result = get_result(sessions)
    write_result('output.txt', result)


if __name__ == '__main__':
    main()
