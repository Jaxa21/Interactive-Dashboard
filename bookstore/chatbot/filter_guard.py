import ast

ALLOWED_METHODS = {
    "str", "dt", "contains", "startswith", "endswith", "match", "fullmatch", "lower", "upper", "title",
    "strip", "lstrip", "rstrip", "len", "count", "find", "replace", "slice", "isdigit", "isalpha", "isnumeric",
    "isin", "between", "isna", "notna", "isnull", "notnull", "abs", "round",
    "year", "month", "day", "hour", "minute", "weekday", "dayofweek", "day_name", "month_name",
}
ALLOWED_ARGUMENTS = {"case", "na", "regex", "flags", "inclusive"}
ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.FloorDiv, ast.BitAnd, ast.BitOr, ast.UnaryOp, ast.Not, ast.Invert, ast.USub, ast.UAdd,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Attribute, ast.Call, ast.keyword, ast.Load,
    ast.Subscript, ast.Slice,
)


def remove_strings(text):
    result = ""
    quote = None
    for char in text:
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        else:
            result += char
    return result


def check_filter(where, columns):
    if "@" in remove_strings(where) or "`" in where:
        raise ValueError("@variables and `backticks` are not allowed; use plain column names")
    try:
        tree = ast.parse(where, mode="eval")
    except SyntaxError as error:
        raise ValueError(f"the filter is not valid: {error.msg}") from None

    columns = set(columns)
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"'{type(node).__name__}' is not allowed in a filter")
        if isinstance(node, ast.Name) and node.id not in columns:
            raise ValueError(f"unknown column '{node.id}'; columns are: {', '.join(sorted(columns))}")
        if isinstance(node, ast.Attribute) and node.attr not in ALLOWED_METHODS:
            raise ValueError(f"'.{node.attr}' is not allowed; allowed methods: {', '.join(sorted(ALLOWED_METHODS))}")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Attribute):
            raise ValueError("only column methods can be called, e.g. title.str.contains('x')")
        if isinstance(node, ast.keyword) and node.arg not in ALLOWED_ARGUMENTS:
            raise ValueError(f"argument '{node.arg}' is not allowed")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (str, int, float, bool, type(None))):
            raise ValueError("only text, number, True/False/None literals are allowed")
