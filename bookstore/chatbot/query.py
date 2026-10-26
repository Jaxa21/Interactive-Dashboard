import json

import pandas as pd

from bookstore.chatbot.filter_guard import check_filter

AGGREGATIONS = ["count", "sum", "mean", "median", "min", "max", "nunique", "rows"]


def split_columns(text):
    return [name.strip() for name in text.split(",") if name.strip() != ""]


def to_records(df):
    df = df.round(2)
    for column in df.select_dtypes("datetime").columns:
        df[column] = df[column].dt.strftime("%Y-%m-%d %H:%M:%S")
    return json.loads(df.to_json(orient="records"))


def select_rows(table, where):
    if where.strip() == "":
        return table
    check_filter(where, table.columns)
    return table.query(where, engine="python")


def single_value(rows, agg, column):
    if agg == "count":
        return len(rows)
    value = getattr(rows[column], agg)()
    if pd.isna(value):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return str(value)


def grouped_values(rows, agg, column, group_by, having, sort_by, ascending, limit):
    if agg == "rows":
        raise ValueError("agg=rows lists rows; use count/sum/mean/... with group_by")
    groups = rows.groupby(split_columns(group_by))
    if agg == "count":
        name = "count"
        values = groups.size()
    else:
        name = f"{agg}_{column}"
        values = getattr(groups[column], agg)()
    table = values.rename(name).reset_index()
    table = table.sort_values(sort_by if sort_by != "" else name, ascending=ascending)

    answer = {}
    if having.strip() != "":
        answer["groups_before_having"] = len(table)
        table = select_rows(table, having)
    answer["groups"] = len(table)
    answer["result"] = to_records(table.head(limit))
    return answer


def run_query(rows, agg, column, group_by, having, sort_by, ascending, limit, max_rows):
    if agg not in AGGREGATIONS:
        raise ValueError(f"agg must be one of {AGGREGATIONS}")
    if having.strip() != "" and group_by == "":
        raise ValueError("having filters groups, so it needs group_by")
    limit = max(1, min(limit, max_rows))

    answer = {"matching_rows": len(rows)}
    if group_by != "":
        answer.update(grouped_values(rows, agg, column, group_by, having, sort_by, ascending, limit))
    elif agg == "rows":
        if sort_by != "":
            rows = rows.sort_values(sort_by, ascending=ascending)
        if column != "":
            rows = rows[split_columns(column)]
        answer["rows"] = to_records(rows.head(limit))
    else:
        answer["result"] = single_value(rows, agg, column)
    return answer
