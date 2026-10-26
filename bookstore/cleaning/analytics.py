import pandas as pd

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def daily_revenue(orders):
    return orders.groupby("date")["paid_price"].sum().round(2)


def top_days(orders, count):
    return daily_revenue(orders).nlargest(count).to_dict()


def monthly_revenue(orders):
    return orders.groupby("year_month")["paid_price"].sum().round(2)


def revenue_by_weekday(orders):
    revenue = orders.groupby("weekday")["paid_price"].sum().round(2)
    return revenue.reindex(WEEKDAYS, fill_value=0)


def most_popular_author_sets(orders):
    sold = orders.groupby("author_set")["quantity"].sum()
    best = sold.max()
    return sorted(sold[sold == best].index.tolist()), int(best)


def top_author_sets(orders, count):
    return orders.groupby("author_set")["quantity"].sum().nlargest(count)


def best_buyer(orders, users):
    spent = orders.groupby("real_user")["paid_price"].sum()
    person = spent.idxmax()
    ids = users.loc[users["real_user"] == person, "id"]
    return sorted(int(user_id) for user_id in ids), round(float(spent.max()), 2)


def top_customers(orders, users, count):
    spent = orders.groupby("real_user")["paid_price"].sum().nlargest(count).round(2)
    names = users.set_index("id")["name"]
    labels = [f"{names.get(person, '?')} ({person})" for person in spent.index]
    return pd.Series(spent.values, index=labels)


def summary(store, top):
    orders = store.orders
    sets, sets_sold = most_popular_author_sets(orders)
    buyer_ids, buyer_spent = best_buyer(orders, store.users)
    total = round(float(orders["paid_price"].sum()), 2)
    return {
        "top5_days": top_days(orders, top),
        "unique_users": int(store.users["real_user"].nunique()),
        "unique_author_sets": int(store.books["author_set"].nunique()),
        "most_popular_author_sets": sets,
        "most_popular_author_sets_books_sold": sets_sold,
        "best_buyer_ids": buyer_ids,
        "best_buyer_spent": buyer_spent,
        "total_revenue": total,
        "orders": len(orders),
        "average_order": round(total / len(orders), 2) if len(orders) else 0,
        "first_day": orders["date"].min(),
        "last_day": orders["date"].max(),
    }
