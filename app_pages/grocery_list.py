import streamlit as st
from datetime import date, timedelta
from models import GroceryItem
from services.storage import save_state

state = st.session_state.app_state
st.session_state.setdefault("week_offset", 0)


def _week_dates(offset: int = 0) -> list[date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


def _build_recipe_items() -> list[GroceryItem]:
    items = []
    for d in _week_dates(st.session_state.week_offset):
        key = d.isoformat()
        slot = state.dinners.get(key)
        if not slot or slot.meal_type != "recipe" or not slot.recipe:
            continue
        day_label = d.strftime("%A")
        for ing in slot.recipe.ingredients:
            items.append(GroceryItem(
                name=ing,
                context=f"{slot.recipe.title} ({day_label})",
                checked=False,
                manual=False,
            ))
    return items


def _sync_grocery_list():
    recipe_items = _build_recipe_items()
    manual_items = [g for g in state.grocery if g.manual]
    checked_names = {g.name.lower() for g in state.grocery if g.checked}
    for item in recipe_items:
        if item.name.lower() in checked_names:
            item.checked = True
    state.grocery = recipe_items + manual_items
    save_state(state)


st.header(":material/shopping_cart: Grocery list")
week = _week_dates(st.session_state.week_offset)
st.caption(f"For week of {week[0].strftime('%b %d')} – {week[-1].strftime('%b %d')}")

with st.form("add_item_form"):
    add_cols = st.columns([4, 1])
    with add_cols[0]:
        new_item = st.text_input("Add an item", placeholder="e.g. olive oil, paper towels", label_visibility="collapsed")
    with add_cols[1]:
        add_clicked = st.form_submit_button("Add", icon=":material/add:", use_container_width=True)
if add_clicked and new_item.strip():
    state.grocery.append(GroceryItem(
        name=new_item.strip(),
        context="Manual",
        checked=False,
        manual=True,
    ))
    save_state(state)
    st.rerun()

_sync_grocery_list()

recipe_items = [g for g in state.grocery if not g.manual]
manual_items = [g for g in state.grocery if g.manual]
total = len(state.grocery)
checked = sum(1 for g in state.grocery if g.checked)

if total == 0:
    st.info("No items yet. Add items above, or plan dinners on the **Weekly planner** page and ingredients will appear here automatically.", icon=":material/playlist_add:")
    st.stop()

st.caption(f"{checked} of {total} items checked off")
progress = checked / total if total > 0 else 0
st.progress(progress)

if manual_items:
    st.subheader("My items")
    for idx, item in enumerate(state.grocery):
        if not item.manual:
            continue
        col_check, col_del = st.columns([5, 1])
        with col_check:
            new_val = st.checkbox(
                item.name,
                value=item.checked,
                key=f"grocery_{idx}",
            )
            if new_val != item.checked:
                state.grocery[idx].checked = new_val
                save_state(state)
                st.rerun()
        with col_del:
            if st.button("", key=f"del_{idx}", icon=":material/close:"):
                state.grocery.pop(idx)
                save_state(state)
                st.rerun()

if recipe_items:
    st.subheader("From recipes")
    grouped: dict[str, list[tuple[int, GroceryItem]]] = {}
    for idx, item in enumerate(state.grocery):
        if item.manual:
            continue
        ctx = item.context or "Other"
        grouped.setdefault(ctx, []).append((idx, item))

    for context, items_with_idx in grouped.items():
        st.markdown(f"**{context}**")
        for idx, item in items_with_idx:
            new_val = st.checkbox(
                item.name,
                value=item.checked,
                key=f"grocery_{idx}",
            )
            if new_val != item.checked:
                state.grocery[idx].checked = new_val
                save_state(state)
                st.rerun()

st.divider()

col_clear_checked, col_clear_all = st.columns(2)
with col_clear_checked:
    if st.button("Clear checked", icon=":material/cleaning_services:", use_container_width=True):
        state.grocery = [g for g in state.grocery if not g.checked]
        save_state(state)
        st.rerun()
with col_clear_all:
    if st.button("Clear all", icon=":material/delete_sweep:", use_container_width=True):
        state.grocery = []
        save_state(state)
        st.rerun()
