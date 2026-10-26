from dataclasses import dataclass

import pandas as pd


@dataclass
class DashboardState:
    store: str
    view: str = "books"
    filter_table: str = ""
    filter_label: str = ""
    filter_rows: pd.Index | None = None
    chart: tuple | None = None

    def reset(self, store=None):
        if store is not None:
            self.store = store
        self.clear_filter()
        self.chart = None

    def clear_filter(self):
        self.filter_table = ""
        self.filter_label = ""
        self.filter_rows = None

    def has_filter_on(self, table):
        return self.filter_rows is not None and self.filter_table == table

    def starting_rows(self, table, rows, narrow):
        """A narrowing filter works on the rows shown now; any other filter on the whole table."""
        if narrow and self.has_filter_on(table):
            return rows.loc[self.filter_rows]
        return rows

    def set_filter(self, table, label, rows, narrow=False):
        if narrow and self.has_filter_on(table):
            label = f"{self.filter_label} + {label}"
        self.filter_table = table
        self.filter_label = label
        self.filter_rows = rows
        self.view = table
        return label

    def visible_rows(self, table, rows):
        if self.has_filter_on(table):
            return rows.loc[self.filter_rows]
        return rows
