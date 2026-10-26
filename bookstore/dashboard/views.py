import altair as alt
import pandas as pd
import streamlit as st

from bookstore.cleaning import analytics
from bookstore.cleaning.store import TABLES

MONEY = st.column_config.NumberColumn(format="dollar")
COUNT = st.column_config.NumberColumn(format="localized")
BLUE = "#4fb3d9"
GREEN = "#5cc98c"
ORANGE = "#f2a654"
PURPLE = "#b392f0"


def pick(label, options, current):
    value = st.segmented_control(label, options, default=current, key=f"{label}_{current}")
    if value is None:
        return current
    return value


def bar_chart(data, x, y, color, sort=None, horizontal=False, height=300):
    if horizontal:
        encoding = {"y": alt.Y(f"{x}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
                    "x": alt.X(f"{y}:Q", title=None)}
    else:
        encoding = {"x": alt.X(f"{x}:N", sort=sort, title=None), "y": alt.Y(f"{y}:Q", title=None)}
    chart = alt.Chart(data).mark_bar(color=color, cornerRadiusEnd=3).encode(
        **encoding, tooltip=[x, alt.Tooltip(f"{y}:Q", format=",.2f")])
    st.altair_chart(chart.properties(height=height), width="stretch")


def daily_chart(daily):
    days = pd.date_range(daily.index.min(), daily.index.max())
    revenue = daily.set_axis(pd.to_datetime(daily.index)).reindex(days, fill_value=0)
    data = pd.DataFrame({"date": days, "revenue": revenue.values,
                         "average": revenue.rolling(7, min_periods=1).mean().round(2).values})
    tooltip = [alt.Tooltip("date:T", format="%Y-%m-%d"), alt.Tooltip("revenue:Q", format="$,.2f"),
               alt.Tooltip("average:Q", title="7-day average", format="$,.2f")]
    base = alt.Chart(data).encode(x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %Y")), tooltip=tooltip)
    daily_area = base.mark_area(color=BLUE, opacity=0.55).encode(
        y=alt.Y("revenue:Q", title=None, axis=alt.Axis(format="$,.0f")))
    trend = base.mark_line(color=ORANGE, strokeWidth=2).encode(y="average:Q")
    st.altair_chart((daily_area + trend).properties(height=280), width="stretch")
    st.caption("Blue: revenue per day (days without sales = $0). Orange: 7-day average.")


def show_dashboard(stores, state):
    store = pick("Store", stores.names(), state.store)
    if store != state.store:
        state.reset(store)
        st.rerun()

    data = stores.get(state.store)
    summary = stores.summary(state.store)

    st.title(f"Bookstore BI - {state.store}")
    st.caption(f"{summary['first_day']} to {summary['last_day']}  |  {summary['orders']:,} orders")
    show_kpis(summary)

    revenue_tab, authors_tab, customers_tab, stores_tab = st.tabs(
        ["Revenue", "Authors", "Customers", "All stores"])
    with revenue_tab:
        show_revenue(stores, state, summary, data)
    with authors_tab:
        show_authors(summary, data)
    with customers_tab:
        show_customers(summary, data)
    with stores_tab:
        show_all_stores(stores)

    show_explorer(data, state)


def show_kpis(summary):
    columns = st.columns(5)
    columns[0].metric("Total revenue", f"${summary['total_revenue']:,.0f}", border=True)
    columns[1].metric("Orders", f"{summary['orders']:,}", border=True)
    columns[2].metric("Average order", f"${summary['average_order']:,.2f}", border=True)
    columns[3].metric("Unique users", f"{summary['unique_users']:,}", border=True)
    columns[4].metric("Unique author sets", f"{summary['unique_author_sets']:,}", border=True)


def show_revenue(stores, state, summary, data):
    left, right = st.columns([1, 2.6])
    with left:
        st.subheader("Top 5 days")
        top = pd.DataFrame(list(summary["top5_days"].items()), columns=["Date", "Revenue"])
        st.dataframe(top, hide_index=True, width="stretch", column_config={"Revenue": MONEY})

    with right:
        daily = analytics.daily_revenue(data.orders)
        if state.chart is None:
            st.subheader("Daily revenue")
        else:
            start, end = state.chart
            st.subheader(f"Daily revenue {start or '...'} to {end or '...'}")
            if start:
                daily = daily[daily.index >= start]
            if end:
                daily = daily[daily.index <= end]
        if daily.empty:
            st.info("No sales in this range")
        else:
            daily_chart(daily)

    month_column, weekday_column = st.columns(2)
    with month_column:
        st.subheader("Revenue by month")
        monthly = analytics.monthly_revenue(data.orders).reset_index()
        monthly.columns = ["month", "revenue"]
        bar_chart(monthly, "month", "revenue", GREEN)
    with weekday_column:
        st.subheader("Revenue by weekday")
        weekdays = analytics.revenue_by_weekday(data.orders).reset_index()
        weekdays.columns = ["weekday", "revenue"]
        bar_chart(weekdays, "weekday", "revenue", ORANGE, sort=analytics.WEEKDAYS)


def show_authors(summary, data):
    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown("**Most popular author set**")
        st.markdown(f"#### {' | '.join(summary['most_popular_author_sets'])}")
        st.caption(f"{summary['most_popular_author_sets_books_sold']} books sold")
    with right.container(border=True):
        st.markdown("**Author sets in the catalogue**")
        st.markdown(f"#### {summary['unique_author_sets']} sets, {len(data.books)} books")

    st.subheader("Top 10 author sets by books sold")
    top = analytics.top_author_sets(data.orders, 10).reset_index()
    top.columns = ["author set", "books sold"]
    bar_chart(top, "author set", "books sold", PURPLE, horizontal=True, height=320)


def show_customers(summary, data):
    ids = summary["best_buyer_ids"]
    left, right = st.columns([1, 2])
    with left.container(border=True):
        st.markdown("**Best buyer (all aliases)**")
        st.markdown(f"`{ids}`")
        st.metric("Total spent", f"${summary['best_buyer_spent']:,.2f}")
        st.caption(f"{len(ids)} user record(s) belong to this person")
    with right:
        st.markdown("**Records of the best buyer**")
        records = data.users[data.users["id"].isin(ids)]
        records = records[["id", "name", "address", "phone", "email", "total_spent"]]
        st.dataframe(records, hide_index=True, width="stretch", column_config={"total_spent": MONEY})

    st.subheader("Top 10 customers by spending")
    customers = analytics.top_customers(data.orders, data.users, 10).reset_index()
    customers.columns = ["customer", "spent"]
    bar_chart(customers, "customer", "spent", BLUE, horizontal=True, height=320)


def show_all_stores(stores):
    rows = []
    monthly = {}
    for name in stores.names():
        summary = stores.summary(name)
        rows.append({
            "Store": name,
            "Revenue": summary["total_revenue"],
            "Orders": summary["orders"],
            "Average order": summary["average_order"],
            "Unique users": summary["unique_users"],
            "Author sets": summary["unique_author_sets"],
            "Best day": list(summary["top5_days"])[0],
            "Best buyer": str(summary["best_buyer_ids"]),
        })
        monthly[name] = analytics.monthly_revenue(stores.get(name).orders)

    table = pd.DataFrame(rows)
    st.subheader("Stores side by side")
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"Revenue": MONEY, "Average order": MONEY, "Orders": COUNT,
                                "Unique users": COUNT, "Author sets": COUNT})

    left, right = st.columns([1, 2])
    with left:
        st.subheader("Total revenue")
        bar_chart(table, "Store", "Revenue", GREEN)
    with right:
        st.subheader("Monthly revenue per store")
        st.line_chart(pd.DataFrame(monthly).fillna(0), height=300)


def show_explorer(data, state):
    st.subheader("Data explorer")
    state.view = pick("Table", TABLES, state.view)
    table = data.table(state.view)
    shown = state.visible_rows(state.view, table)
    if state.has_filter_on(state.view):
        st.info(f"Filter: **{state.filter_label}** - showing {len(shown):,} of {len(table):,} rows")
        if st.button("Clear filter"):
            state.clear_filter()
            st.rerun()
    elif state.filter_rows is not None:
        st.caption(f"A filter is active on the **{state.filter_table}** table: {state.filter_label}")
    st.dataframe(shown, hide_index=True, height=400)


def show_chat(history, get_assistant, store):
    st.header("Ask your data")
    st.caption("Ask a question or give a command, e.g. \"select users with e-mails starting with s or p\".")
    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("trace"):
                with st.expander("How this was computed"):
                    st.json(message["trace"], expanded=False)

    question = st.chat_input("Type a question")
    if question:
        history.append({"role": "user", "content": question})
        with st.spinner("Querying the data..."):
            try:
                answer, trace = get_assistant().reply(store, question)
            except Exception as error:
                answer, trace = f"AI error: {error}", []
        history.append({"role": "assistant", "content": answer, "trace": trace})
        st.rerun()
