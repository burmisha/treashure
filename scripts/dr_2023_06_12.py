import itertools


def find_by_delta(delta, regions, target):
    results = []
    for size in range(len(regions) + 1):
        for subset in itertools.combinations(regions, size):
            total = sum(area for _, area in subset)
            diff = abs(total - target)
            if diff <= delta:
                results.append((subset, diff))
    results.sort(key=lambda x: x[1])
    return results


regions = [
    ('Республика Марий Эл', 23375),
    ('Ивановская область', 21437),
    ('Чувашская Республика', 18343),
    ('Чеченская Республика', 16171),
    ('Калининградская область', 15125),
    ('Карачаево-Черкесия', 14277),
    ('Кабардино-Балкария', 12470),
    ('Республика Северная Осетия — Алания', 7987),
    ('Республика Адыгея', 7792),
    ('Республика Ингушетия', 3123),
    ('Москва', 2561),
    ('Санкт-Петербург', 1403),
    ('Севастополь', 864),
]
target = 17098246 - 17075400
rows = find_by_delta(50, regions, target)

for row in find_by_delta(50):
    regions_subset = list(row[0])
    regions_subset.sort(key=lambda x: x[1], reverse=True)
    answer = ', '.join(f'{region[0]} ({region[1]})'for region in regions_subset)
    line = f'{row[1]:2d}: {answer}'
    print(line)
