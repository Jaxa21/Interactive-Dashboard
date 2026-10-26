import pandas as pd

from bookstore.cleaning import analytics

TABLES = ["books", "users", "orders"]


class CleanStore:
    def __init__(self, books, users, orders):
        self.books = books
        self.users = users
        self.orders = orders

    def table(self, name):
        if name not in TABLES:
            raise ValueError(f"unknown table '{name}', use one of {TABLES}")
        return getattr(self, name)

    def schema(self):
        parts = []
        for name in TABLES:
            parts.append(f"{name}({', '.join(self.table(name).columns)})")
        return ", ".join(parts)


def save_store(store, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        store.table(name).to_parquet(folder / f"{name}.parquet", index=False)


def load_store(folder):
    tables = [pd.read_parquet(folder / f"{name}.parquet") for name in TABLES]
    return CleanStore(*tables)


class Stores:
    def __init__(self, clean_dir, top_days):
        self.clean_dir = clean_dir
        self.top_days = top_days
        self.loaded = {}
        self.summaries = {}
        self.found = None

    def names(self):
        if self.found is None:
            self.found = sorted(path.parent.name for path in self.clean_dir.glob("*/orders.parquet"))
        return self.found

    def get(self, name):
        if name not in self.names():
            raise ValueError(f"unknown store '{name}', use one of {self.names()}")
        if name not in self.loaded:
            self.loaded[name] = load_store(self.clean_dir / name)
        return self.loaded[name]

    def summary(self, name):
        if name not in self.summaries:
            self.summaries[name] = analytics.summary(self.get(name), self.top_days)
        return self.summaries[name]
