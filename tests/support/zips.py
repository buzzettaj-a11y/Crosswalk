"""A dict-backed ZipResolver for tests. Exact keys only, like the real resolvers M05 adds."""


class DictResolver:
    def __init__(self, table):
        self.table = {(s.lower(), c.lower()): z for (s, c), z in table.items()}
        self.calls = []

    def zip_for(self, street, borough_or_city):
        self.calls.append((street, borough_or_city))
        return self.table.get((street.lower(), borough_or_city.lower()))
