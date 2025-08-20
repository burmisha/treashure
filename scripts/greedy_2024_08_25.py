#!/usr/bin/env python3
import sys
import dataclasses


@dataclasses.dataclass
class Section:
    start: int
    finish: int


def read_input(source) -> list[Section]:
    total_count = None
    sections = []
    for index, line in enumerate(source):
        if index == 0:
            total_count = int(line.strip())
        else:
            parts = line.strip().split()
            section = Section(start=int(parts[0]), finish=int(parts[1]))
            sections.append(section)
    
    if len(sections) != total_count:
        raise ValueError('Invalid sections count')
    
    return sections


def get_solution(sections: list[Section]) -> int:
    active_sections = sections[:]
    active_sections.sort(key=lambda s: s.finish)

    result = 0
    current_time = 0
    while active_sections:
        greedy_choice = active_sections[0]
        current_time = greedy_choice.finish
        result += 1
        active_sections = [s for s in active_sections if s.start > current_time]

    return result


def main():
    sections = read_input(sys.stdin)
    result = get_solution(sections)
    print(f'{result}')


def test():
    assert get_solution([Section(s, f) for s, f in [(1, 3), (2, 3), (4, 5)]]) == 2
    assert get_solution([Section(s, f) for s, f in [(1, 2), (2, 3), (4, 5), (4, 5), (5, 6)]]) == 2
    assert get_solution([Section(s, f) for s, f in [(1, 50), (49, 50)]]) == 1


if __name__ == '__main__':
    main()
