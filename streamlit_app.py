import streamlit as st
from services.storage import load_state, save_state

st.set_page_config(
    page_title="Family dinner planner",
    page_icon=":material/restaurant:",
    layout="centered",
)

st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("app_state", None)

if not st.session_state.authenticated:
    st.title(":material/restaurant: Family dinner planner")
    st.caption("Christa · Lauren · Romi · Gus")
    with st.form("login_form"):
        password = st.text_input("Password", type="password", placeholder="Enter family password")
        submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
    if submitted:
        if password == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.authenticated = True
            st.session_state.app_state = load_state()
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

if st.session_state.app_state is None:
    st.session_state.app_state = load_state()

page = st.navigation(
    [
        st.Page("app_pages/weekly_planner.py", title="Weekly planner", icon=":material/calendar_today:"),
        st.Page("app_pages/recipe_search.py", title="Find recipes", icon=":material/search:"),
        st.Page("app_pages/grocery_list.py", title="Grocery list", icon=":material/shopping_cart:"),
    ],
    position="top",
)

with st.sidebar:
    if st.button("Sign out", icon=":material/logout:"):
        st.session_state.authenticated = False
        st.session_state.app_state = None
        st.rerun()

page.run()
