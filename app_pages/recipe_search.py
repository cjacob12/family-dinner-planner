import streamlit as st
from datetime import date, timedelta
from models import DinnerSlot, Recipe
from services.recipe_api import search_recipes
from services.storage import save_state

state = st.session_state.app_state
st.session_state.setdefault("week_offset", 0)


def _week_dates(offset: int = 0) -> list[date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


current_week = _week_dates(st.session_state.week_offset)
next_week = _week_dates(st.session_state.week_offset + 1)
DAY_OPTIONS = {}
for d in current_week + next_week:
    DAY_OPTIONS[d.strftime("%A, %b %d")] = d

CUISINES = [
    "", "African", "American", "British", "Chinese", "French",
    "Greek", "Indian", "Italian", "Japanese", "Korean",
    "Mediterranean", "Mexican", "Middle Eastern", "Thai", "Vietnamese",
]
DIETS = [
    "", "Gluten Free", "Ketogenic", "Paleo",
    "Pescetarian", "Vegan", "Vegetarian", "Whole30",
]


@st.dialog("Assign to day", width="small")
def _assign_recipe(recipe_idx: int):
    results = st.session_state.get("search_results", [])
    if recipe_idx >= len(results):
        st.error("Recipe not found.")
        return

    r = results[recipe_idx]
    st.markdown(f"**{r['title']}**")
    if r.get("image_url"):
        st.image(r["image_url"], width=200)

    day_label = st.selectbox("Pick a day", options=list(DAY_OPTIONS.keys()))
    d = DAY_OPTIONS[day_label]
    day_iso = d.isoformat()

    existing = state.dinners.get(day_iso)
    if existing and existing.is_planned:
        st.warning(f"{day_label} already has: **{existing.display_name}**. Saving will replace it.")

    if st.button("Save to planner", type="primary", use_container_width=True, icon=":material/check:"):
        state.dinners[day_iso] = DinnerSlot(
            day=day_iso,
            meal_type="recipe",
            recipe=Recipe(
                title=r.get("title", ""),
                source_url=r.get("source_url", ""),
                image_url=r.get("image_url", ""),
                ingredients=r.get("ingredients", []),
                prep_minutes=r.get("prep_minutes"),
                cook_minutes=r.get("cook_minutes"),
                total_minutes=r.get("total_minutes"),
                calories_per_serving=r.get("calories_per_serving"),
                servings=r.get("servings"),
                description=r.get("description", ""),
            ),
        )
        save_state(state)
        st.session_state.pop("assigning_recipe", None)
        st.toast(f"Saved **{r['title']}** to {day_label}")
        st.rerun()

    if st.button("Cancel"):
        st.session_state.pop("assigning_recipe", None)
        st.rerun()


st.header(":material/search: Find recipes")

api_key = st.secrets.get("SPOONACULAR_API_KEY", "")
if not api_key or api_key == "YOUR_SPOONACULAR_API_KEY_HERE":
    st.warning(
        "No Spoonacular API key configured. Add your key to `.streamlit/secrets.toml` as `SPOONACULAR_API_KEY`.",
        icon=":material/key:",
    )
    st.caption("[Get a free API key at spoonacular.com](https://spoonacular.com/food-api/console)")
    st.stop()

with st.form("search_form"):
    query = st.text_input(
        "What are you in the mood for?",
        placeholder="e.g. chicken tacos, pasta, salmon",
    )
    with st.expander("Filters (optional)"):
        filter_cols = st.columns(2)
        with filter_cols[0]:
            cuisine = st.selectbox("Cuisine", options=CUISINES, format_func=lambda x: x or "Any cuisine")
            diet = st.selectbox("Diet", options=DIETS, format_func=lambda x: x or "No restriction")
        with filter_cols[1]:
            max_time = st.selectbox("Max cook time", options=[0, 15, 30, 45, 60, 90, 120], format_func=lambda x: "No limit" if x == 0 else f"{x} minutes")
            num_results = st.selectbox("Results", options=[3, 6, 9, 12], index=2)

    searched = st.form_submit_button("Search recipes", type="primary", use_container_width=True, icon=":material/search:")

if searched and query.strip():
    with st.spinner("Searching recipes..."):
        results = search_recipes(
            query.strip(),
            number=num_results,
            cuisine=cuisine,
            diet=diet,
            max_ready_time=max_time if max_time > 0 else None,
        )
    st.session_state.search_results = results
    st.session_state.search_query = query.strip()

results = st.session_state.get("search_results", [])
query_display = st.session_state.get("search_query", "")

if query_display and results:
    st.subheader(f"Results for \"{query_display}\"")
    st.caption(f"{len(results)} recipes found")

    for i, r in enumerate(results):
        with st.container(border=True):
            img_col, info_col = st.columns([1, 2])
            with img_col:
                if r.get("image_url"):
                    st.image(r["image_url"], use_container_width=True)
                else:
                    st.markdown(":material/dinner_dining:")
            with info_col:
                st.markdown(f"**{r['title']}**")
                meta = []
                if r.get("total_minutes"):
                    meta.append(f":material/schedule: {r['total_minutes']} min")
                if r.get("calories_per_serving"):
                    meta.append(f":material/local_fire_department: {r['calories_per_serving']} cal")
                if r.get("servings"):
                    meta.append(f":material/group: {r['servings']} servings")
                if meta:
                    st.caption(" · ".join(meta))
                if r.get("source_url"):
                    st.caption(f"[View full recipe]({r['source_url']})")

                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button("Use this", key=f"use_{i}", icon=":material/add_circle:", use_container_width=True, type="primary"):
                        st.session_state.assigning_recipe = i
                        st.rerun()
                with btn_cols[1]:
                    if r.get("ingredients"):
                        with st.popover("Ingredients", icon=":material/list:", use_container_width=True):
                            for ing in r["ingredients"]:
                                st.markdown(f"- {ing}")

elif query_display and not results:
    st.info("No recipes found. Try broader terms or remove filters.", icon=":material/search_off:")

if st.session_state.get("assigning_recipe") is not None:
    _assign_recipe(st.session_state["assigning_recipe"])
