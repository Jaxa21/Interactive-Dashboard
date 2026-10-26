import re
from datetime import datetime

import pandas as pd
from dateutil import parser

EUR_TO_USD = 1.2


def get_currency(price):
    if not isinstance(price, str):
        return None
    if "EUR" in price or "€" in price:
        return "EUR"
    return "USD"


def parse_price(price):
    if not isinstance(price, str):
        return float("nan")

    if "¢" in price:
        numbers = re.findall(r"\d+", price)
        if len(numbers) < 2:
            return float("nan")
        amount = int(numbers[0]) + int(numbers[1]) / 100
    else:
        match = re.search(r"\d+(\.\d*)?", price)
        if match is None:
            return float("nan")
        amount = float(match.group())

    if get_currency(price) == "EUR":
        amount = amount * EUR_TO_USD
    return round(amount, 2)


def parse_timestamp(text):
    if not isinstance(text, str):
        return pd.NaT

    text = text.replace(";", " ").replace(",", " ")
    text = text.replace("A.M.", "AM").replace("P.M.", "PM")
    day_first = re.search(r"\d\.\d+\.\d{4}", text) is not None

    try:
        first = parser.parse(text, dayfirst=day_first, default=datetime(2000, 1, 1))
        second = parser.parse(text, dayfirst=day_first, default=datetime(2001, 2, 2))
    except (ValueError, OverflowError):
        return pd.NaT

    if first != second:
        return pd.NaT
    return pd.Timestamp(first).floor("s")
