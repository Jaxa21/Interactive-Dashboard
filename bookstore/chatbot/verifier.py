import json
import re

NUMBER = re.compile(r"(?<![A-Za-z_\d])(?:\d{4}-\d{2}-\d{2}|\d+(?:,\d{3})*(?:\.\d+)?)(?![A-Za-z_\d])")
LIST_NUMBER = re.compile(r"(?m)^(\s*)\d+[.)]\s+")
EU_DATE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d|\.\d)")
SPACED_NUMBER = re.compile(r"(?<![\d,.])\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:,\d+)?(?!\d)")
DECIMAL_COMMA = re.compile(r"(?<![\d,.])(\d+),(\d{1,2})(?![\d,])")


def normalize(text):
    """Polish/European writing -> the form the tools use: 20.08.2025 -> 2025-08-20,
    739 354,03 -> 739354.03, 3,66 -> 3.66. A comma before exactly three digits stays a thousands separator."""
    text = EU_DATE.sub(lambda m: f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}", text)
    text = SPACED_NUMBER.sub(lambda m: re.sub(r"[ \u00a0\u202f]", "", m.group()).replace(",", "."), text)
    return DECIMAL_COMMA.sub(r"\1.\2", text)


def to_float(token):
    return float(token.replace(",", ""))


def decimals(token):
    if "." in token:
        return len(token.split(".")[1])
    return 0


def list_sizes(value):
    sizes = []
    if isinstance(value, dict):
        sizes.append(len(value))
        for item in value.values():
            sizes += list_sizes(item)
    elif isinstance(value, list):
        sizes.append(len(value))
        for item in value:
            sizes += list_sizes(item)
    return sizes


def find_unverified(answer, question, results, known_numbers=()):
    evidence = normalize(question) + " " + json.dumps(results, default=str)
    dates = set()
    numbers = [float(n) for n in known_numbers] + [float(size) for size in list_sizes(results)]
    for token in NUMBER.findall(evidence):
        if "-" in token:
            dates.add(token)
            numbers += [float(part) for part in token.split("-")]
        else:
            numbers.append(to_float(token))

    answer = LIST_NUMBER.sub(r"\1", normalize(answer))
    unverified = []
    for token in NUMBER.findall(answer):
        if "-" in token:
            if token not in dates:
                unverified.append(token)
            continue
        value = to_float(token)
        tolerance = 0.5 * 10 ** -decimals(token) + 1e-9
        if not any(abs(value - number) <= tolerance for number in numbers):
            unverified.append(token)
    return unverified
