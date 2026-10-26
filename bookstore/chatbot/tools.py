import re

from bookstore.chatbot.query import run_query, select_rows, to_records

ARITHMETIC = re.compile(r"[\d\s.+\-*/()%]+")


def tool(description):
    def add_description(function):
        function.__doc__ = description
        return function
    return add_description


class DataTools:
    def __init__(self, stores, max_rows):
        self.stores = stores
        self.max_rows = max_rows

    def functions(self):
        return [self.kpis, self.query, self.calculate]

    @tool("Summary of one store: top 5 revenue days, number of unique (real) users, number of unique "
          "author sets, most popular author set(s) by books sold, best buyer with all their user ids, "
          "total revenue, number of orders, average order, first and last day.")
    def kpis(self, store: str) -> dict:
        return self.stores.summary(store)

    @tool("Exact answer computed from one store's clean data.\n"
          "table: books, users or orders.\n"
          "where: pandas df.query() filter, e.g. \"email.str.match('[sp]')\" or "
          "\"genre == 'Fantasy' and year_month == '2026-03'\" or \"date >= '2025-09-01'\"; empty = all rows.\n"
          "agg: count, sum, mean, median, min, max or nunique of `column`; "
          "or rows = list rows (`column` = comma-separated columns to show, ordered by sort_by).\n"
          "group_by: comma-separated columns -> one value per group, named 'count' or '<agg>_<column>' "
          "(e.g. sum_paid_price), largest first unless ascending=True; sort_by=a group column orders the groups "
          "by it instead, e.g. group_by=year_month, sort_by=year_month, ascending=True for a trend over time.\n"
          "having: filter on those group values, like SQL HAVING; `groups` is then the number of groups that "
          "pass. E.g. people with aliases: table=users, agg=count, group_by=real_user, having=\"count > 1\"; "
          "days over $3000: table=orders, agg=sum, column=paid_price, group_by=date, "
          "having=\"sum_paid_price > 3000\".\n"
          "The answer always includes matching_rows; groups and rows are cut to `limit` (at most 50).")
    def query(self, store: str, table: str, where: str = "", agg: str = "count", column: str = "",
              group_by: str = "", having: str = "", sort_by: str = "", ascending: bool = False,
              limit: int = 20) -> dict:
        rows = select_rows(self.stores.get(store).table(table), where)
        return run_query(rows, agg, column, group_by, having, sort_by, ascending, limit, self.max_rows)

    @tool("Exact arithmetic on numbers taken from other tools, e.g. '(3719.35 - 3587.94) / 3587.94 * 100'.")
    def calculate(self, expression: str) -> float:
        if not ARITHMETIC.fullmatch(expression) or "**" in expression:
            raise ValueError("only numbers and + - * / % ( ) are allowed")
        return round(eval(expression, {"__builtins__": {}}), 4)


class ValueClassifier:
    def __init__(self, model, batch_size):
        self.model = model
        self.batch_size = batch_size

    def matching(self, values, criterion):
        hits = []
        for start in range(0, len(values), self.batch_size):
            batch = values[start:start + self.batch_size]
            lines = [f"{index}. {value}" for index, value in enumerate(batch)]
            prompt = (f"Criterion: {criterion}\nJudge each numbered item by its text alone. "
                      'Reply as JSON {"matches": [numbers of the items that meet the criterion]}.\n'
                      + "\n".join(lines))
            answer = self.model.ask_json(prompt)
            for index in answer.get("matches", []):
                if isinstance(index, int) and 0 <= index < len(batch):
                    hits.append(batch[index])
        return hits


class DashboardTools:
    def __init__(self, state, stores, classifier, example_rows):
        self.state = state
        self.stores = stores
        self.classifier = classifier
        self.example_rows = example_rows

    def functions(self):
        return [self.filter_rows, self.filter_by_meaning, self.switch_store, self.set_chart_range,
                self.clear_filters]

    @tool("DASHBOARD: show only the rows of a table (books, users or orders) that match an exact pandas "
          "df.query() filter, e.g. \"email.str.match('[sp]')\".\n"
          "exclude=True hides the matching rows instead ('filter out', 'remove', 'hide').\n"
          "narrow=True filters the rows shown now instead of the whole table ('of those', 'now only', 'also').\n"
          "label: a short description shown above the table.")
    def filter_rows(self, table: str, where: str, label: str, exclude: bool = False, narrow: bool = False) -> dict:
        rows = self.state.starting_rows(table, self.table_shown(table), narrow)
        matches = rows.index.isin(select_rows(rows, where).index)
        return self.apply(table, rows, matches, label, exclude, narrow)

    @tool("DASHBOARD: like filter_rows, for criteria that need understanding of the text and cannot be written "
          "as a filter, e.g. column='title', criterion='contains the name of a person'. "
          "Every distinct value of the column is judged yes/no; the filter itself is then exact. "
          "Empty values never match. exclude and narrow work as in filter_rows.")
    def filter_by_meaning(self, table: str, column: str, criterion: str, label: str,
                          exclude: bool = False, narrow: bool = False) -> dict:
        rows = self.state.starting_rows(table, self.table_shown(table), narrow)
        values = rows[column]
        known = values.dropna().astype(str)
        hits = self.classifier.matching(sorted(known.unique()), criterion)
        matches = (values.notna() & values.astype(str).isin(hits)).to_numpy()
        return self.apply(table, rows, matches, label, exclude, narrow)

    @tool("DASHBOARD: show another store. Clears filters and the chart range.")
    def switch_store(self, store: str) -> dict:
        self.stores.get(store)
        self.state.reset(store)
        return {"now_showing": store}

    @tool("DASHBOARD: zoom the daily revenue chart to dates 'YYYY-MM-DD'. Empty start and end = whole period.")
    def set_chart_range(self, start: str = "", end: str = "") -> dict:
        if start == "" and end == "":
            self.state.chart = None
        else:
            self.state.chart = (start, end)
        return {"chart_range": self.state.chart}

    @tool("DASHBOARD: remove all filters and reset the chart range.")
    def clear_filters(self) -> dict:
        self.state.reset()
        return {"cleared": True}

    def table_shown(self, table):
        return self.stores.get(self.state.store).table(table)

    def apply(self, table, rows, matches, label, exclude, narrow):
        if exclude:
            shown = rows[~matches]
            label = label + " (excluded)"
        else:
            shown = rows[matches]
        label = self.state.set_filter(table, label, shown.index, narrow)
        return {"rows_shown": len(shown), "rows_before_this_filter": len(rows),
                "rows_total": len(self.table_shown(table)), "filter": label,
                "examples": to_records(shown.head(self.example_rows))}
