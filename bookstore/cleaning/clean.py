import pandas as pd
import yaml

from bookstore.cleaning.parsing import get_currency, parse_price, parse_timestamp
from bookstore.cleaning.store import CleanStore
from bookstore.cleaning.users import find_real_users

MISSING = r"^\s*(NULL)?\s*$"


def find_store_folders(data_dir):
    return sorted(path.parent.name for path in data_dir.glob("*/orders.parquet"))


def read_books(path):
    with open(path, encoding="utf-8") as f:
        books = pd.DataFrame(yaml.safe_load(f))
    books.columns = [str(column).lstrip(":") for column in books.columns]
    return books


def remove_duplicates(df):
    df = df.replace(MISSING, None, regex=True)
    return df.drop_duplicates().drop_duplicates(subset="id").copy()


def make_author_set(authors):
    if not isinstance(authors, str) or authors.strip() == "":
        return None
    names = set()
    for name in authors.split(","):
        if name.strip() != "":
            names.add(name.strip())
    return ", ".join(sorted(names))


def clean_books(raw):
    books = remove_duplicates(raw)
    books["year"] = pd.to_numeric(books["year"], errors="coerce").astype("Int64")
    books["author_set"] = books["author"].apply(make_author_set)
    return books


def clean_users(raw):
    users = remove_duplicates(raw)
    users["name"] = users["name"].str.strip()
    users["phone"] = users["phone"].str.replace(r"\D", "", regex=True).replace("", None)
    users["email"] = users["email"].str.lower().str.strip().replace("", None)
    users["state"] = users["address"].str.extract(r"\b([A-Z]{2}) \d{5}")[0]
    return users


def clean_orders(raw, now):
    orders = remove_duplicates(raw)
    orders["currency"] = orders["unit_price"].apply(get_currency)
    orders["unit_price"] = orders["unit_price"].apply(parse_price)
    orders["timestamp"] = pd.to_datetime(orders["timestamp"].apply(parse_timestamp))
    orders["quantity"] = pd.to_numeric(orders["quantity"], errors="coerce")

    bad = orders["unit_price"].isna() | orders["timestamp"].isna() | (orders["timestamp"] > now)
    bad = bad | ~(orders["quantity"] > 0)
    orders = orders[~bad].copy()

    orders["quantity"] = orders["quantity"].astype("int64")
    orders["paid_price"] = (orders["quantity"] * orders["unit_price"]).round(2)
    orders["date"] = orders["timestamp"].dt.strftime("%Y-%m-%d")
    orders["year"] = orders["timestamp"].dt.year
    orders["month"] = orders["timestamp"].dt.month
    orders["day"] = orders["timestamp"].dt.day
    orders["year_month"] = orders["timestamp"].dt.strftime("%Y-%m")
    orders["weekday"] = orders["timestamp"].dt.day_name()
    orders["hour"] = orders["timestamp"].dt.hour
    return orders


def clean_store(folder, now=None):
    if now is None:
        now = pd.Timestamp.now()

    raw_books = read_books(folder / "books.yaml")
    raw_users = pd.read_csv(folder / "users.csv")
    raw_orders = pd.read_parquet(folder / "orders.parquet")
    books = clean_books(raw_books)
    users = clean_users(raw_users)
    orders = clean_orders(raw_orders, now)
    users["real_user"] = find_real_users(users)

    book_info = books[["id", "title", "author_set", "genre"]].rename(columns={"id": "book_id"})
    user_info = users[["id", "real_user", "name", "email"]].rename(columns={"id": "user_id"})
    orders = orders.merge(book_info, on="book_id").merge(user_info, on="user_id")

    spent = orders.groupby("user_id")["paid_price"].sum()
    users["total_spent"] = users["id"].map(spent).fillna(0).round(2)

    counts = {
        "books": (len(raw_books), len(books)),
        "users": (len(raw_users), len(users)),
        "orders": (len(raw_orders), len(orders)),
    }
    return CleanStore(books, users, orders.reset_index(drop=True)), counts
