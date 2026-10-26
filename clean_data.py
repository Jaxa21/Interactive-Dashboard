import matplotlib.dates as mdates
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import StrMethodFormatter

from bookstore import config
from bookstore.cleaning import analytics
from bookstore.cleaning.clean import clean_store, find_store_folders
from bookstore.cleaning.store import save_store


def save_chart(name, daily):
    config.results_dir().mkdir(exist_ok=True)
    days = pd.date_range(daily.index.min(), daily.index.max())
    revenue = daily.set_axis(pd.to_datetime(daily.index)).reindex(days, fill_value=0)
    figure = Figure(figsize=(12, 4))
    axes = figure.subplots()
    axes.fill_between(days, revenue.values, color="#4fb3d9", alpha=0.55, linewidth=0, label="revenue per day")
    axes.plot(days, revenue.rolling(7, min_periods=1).mean(), color="#f2a654", linewidth=2, label="7-day average")
    axes.set_title(f"{name} daily revenue (USD)")
    axes.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    axes.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    axes.set_ylim(bottom=0)
    axes.grid(axis="y", alpha=0.3)
    axes.legend(loc="upper left", frameon=False)
    figure.savefig(config.results_dir() / f"{name}_daily_revenue.png", bbox_inches="tight", dpi=110)


def run(name):
    store, counts = clean_store(config.data_dir() / name)
    save_store(store, config.clean_dir() / name)
    result = analytics.summary(store, config.TOP_DAYS)
    print(f"\n=== {name} ===")
    for table, (read, kept) in counts.items():
        print(f"{table}: {read} rows read, {kept} kept")
    print("top 5 days:", ", ".join(result["top5_days"]))
    print("unique users:", result["unique_users"])
    print("unique author sets:", result["unique_author_sets"])
    print("most popular author set:", result["most_popular_author_sets"],
          result["most_popular_author_sets_books_sold"], "books")
    print("best buyer:", result["best_buyer_ids"], f"${result['best_buyer_spent']:,.2f}")
    save_chart(name, analytics.daily_revenue(store.orders))


def main():
    names = find_store_folders(config.data_dir())
    first = "STORE1" if "STORE1" in names else names[0]
    run(first)
    for name in names:
        if name != first:
            run(name)


if __name__ == "__main__":
    main()
