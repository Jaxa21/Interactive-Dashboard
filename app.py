import streamlit as st

from bookstore import config
from bookstore.chatbot import assistant
from bookstore.cleaning.store import Stores
from bookstore.dashboard.state import DashboardState
from bookstore.dashboard.views import show_chat, show_dashboard


@st.cache_resource
def load_stores():
    return Stores(config.clean_dir(), config.TOP_DAYS)


def get_assistant(stores, state):
    if "assistant" not in st.session_state:
        provider = assistant.gemini(st.secrets["LLM_API_KEY"])
        st.session_state.assistant = assistant.build_assistant(stores, state, provider)
    return st.session_state.assistant


st.set_page_config(page_title="Bookstore BI", layout="wide")

stores = load_stores()
if not stores.names():
    st.error(f"No clean data in {config.clean_dir()}. Run `python clean_data.py` first.")
    st.stop()

if "state" not in st.session_state:
    st.session_state.state = DashboardState(stores.names()[0])
if "history" not in st.session_state:
    st.session_state.history = []
state = st.session_state.state

with st.sidebar:
    show_chat(st.session_state.history, lambda: get_assistant(stores, state), state.store)

show_dashboard(stores, state)
