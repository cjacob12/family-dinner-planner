import streamlit as st
from datetime import date, timedelta
from models import DinnerSlot, Recipe, EatOutMeal
from services.storage import save_state

state = st.session_state.app_state
st.session_state.setdefault("week_offset", 0)


def _week_dates(offset: int = 0) -> list[date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


WEEK = _week_dates(st.session_state.week_offset)
DAY_LABELS = {d: d.strftime("%A") for d in WEEK}


def _get_slot(d: date) -> DinnerSlot:
    key = d.isoformat()
    if key not in state.dinners:
        state.dinners[key] = DinnerSlot(day=key)
    return state.dinners[key]


def _save():
    save_state(state)


def _time_str(slot: DinnerSlot) -> str:
    if slot.meal_type != "recipe" or not slot.recipe:
        return ""
    parts = []
    if slot.recipe.prep_minutes:
        parts.append(f"{slot.recipe.prep_minutes}m prep")
    if slot.recipe.cook_minutes:
        parts.append(f"{slot.recipe.cook_minutes}m cook")
    if not parts and slot.recipe.total_minutes:
        parts.append(f"{slot.recipe.total_minutes}m total")
    return " · ".join(parts)


@st.dialog("Plan dinner", width="large")
def _render_edit_form(day_iso: str):
    d = date.fromisoformat(day_iso)
    slot = _get_slot(d)
    day_label = d.strftime("%A, %b %d")
    st.subheader(day_label)

    meal_type = st.segmented_control(
        "Meal type",
        options=["Cook at home", "Eat out"],
        default="Eat out" if slot.meal_type == "eat_out" else "Cook at home",
        key=f"type_{day_iso}",
        label_visibility="collapsed",
    )

    if meal_type == "Eat out":
        with st.form(f"eatout_form_{day_iso}"):
            name = st.text_input("Where / what?", value=slot.eat_out.name if slot.eat_out else "", placeholder="e.g. Pizza night, Sushi downtown")
            notes = st.text_input("Notes (optional)", value=slot.eat_out.notes if slot.eat_out else "", placeholder="e.g. reservation at 6pm")
            cals = st.number_input("Estimated calories (optional)", value=slot.eat_out.estimated_calories if slot.eat_out and slot.eat_out.estimated_calories else 0, min_value=0, step=50)
            if st.form_submit_button("Save", type="primary", use_container_width=True):
                state.dinners[day_iso] = DinnerSlot(
                    day=day_iso,
                    meal_type="eat_out",
                    eat_out=EatOutMeal(name=name, notes=notes, estimated_calories=cals if cals > 0 else None),
                )
                _save()
                st.session_state.pop("editing_day", None)
                st.rerun()
    else:
        st.info("Use the **Find recipes** page to search and assign a recipe to this day.", icon=":material/search:")
        st.caption(f"Tip: on the Find recipes page, select **{day_label}** as the target day.")

        with st.form(f"manual_form_{day_iso}"):
            st.caption("Or enter a recipe manually:")
            title = st.text_input("Recipe name", value=slot.recipe.title if slot.recipe else "", placeholder="e.g. Chicken tacos")
            url = st.text_input("Recipe URL (optional)", value=slot.recipe.source_url if slot.recipe else "")
            col_p, col_c = st.columns(2)
            with col_p:
                prep = st.number_input("Prep (min)", value=slot.recipe.prep_minutes or 0 if slot.recipe else 0, min_value=0)
            with col_c:
                cook = st.number_input("Cook (min)", value=slot.recipe.cook_minutes or 0 if slot.recipe else 0, min_value=0)
            ingredients_str = st.text_area(
                "Ingredients (one per line)",
                value="\n".join(slot.recipe.ingredients) if slot.recipe and slot.recipe.ingredients else "",
                placeholder="2 chicken breasts\n1 cup rice\n1 can black beans",
            )
            cals = st.number_input("Calories per serving (optional)", value=slot.recipe.calories_per_serving or 0 if slot.recipe else 0, min_value=0, step=10)
            servings = st.number_input("Servings", value=slot.recipe.servings or 4 if slot.recipe else 4, min_value=1)
            if st.form_submit_button("Save recipe", type="primary", use_container_width=True):
                ingredients = [line.strip() for line in ingredients_str.split("\n") if line.strip()]
                state.dinners[day_iso] = DinnerSlot(
                    day=day_iso,
                    meal_type="recipe",
                    recipe=Recipe(
                        title=title,
                        source_url=url,
                        ingredients=ingredients,
                        prep_minutes=prep if prep > 0 else None,
                        cook_minutes=cook if cook > 0 else None,
                        total_minutes=(prep + cook) if (prep or cook) else None,
                        calories_per_serving=cals if cals > 0 else None,
                        servings=servings,
                    ),
                )
                _save()
                st.session_state.pop("editing_day", None)
                st.rerun()

    if st.button("Cancel"):
        st.session_state.pop("editing_day", None)
        st.rerun()


week_start = WEEK[0]
week_end = WEEK[-1]
is_current_week = st.session_state.week_offset == 0

if is_current_week:
    week_label = "This week"
elif st.session_state.week_offset == 1:
    week_label = "Next week"
elif st.session_state.week_offset == -1:
    week_label = "Last week"
else:
    week_label = f"Week of {week_start.strftime('%b %d')}"

st.header(f":material/calendar_today: {week_label}")
st.caption(f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}")

nav_cols = st.columns([1, 1, 1])
with nav_cols[0]:
    if st.button("Previous", icon=":material/chevron_left:", use_container_width=True):
        st.session_state.week_offset -= 1
        st.rerun()
with nav_cols[1]:
    if st.button("Today", icon=":material/today:", use_container_width=True, disabled=is_current_week):
        st.session_state.week_offset = 0
        st.rerun()
with nav_cols[2]:
    if st.button("Next", icon=":material/chevron_right:", use_container_width=True):
        st.session_state.week_offset += 1
        st.rerun()

planned = sum(1 for d in WEEK if _get_slot(d).is_planned)
total_cal = sum(_get_slot(d).calories or 0 for d in WEEK)
summary = f"{planned} of 7 dinners planned"
if total_cal > 0:
    summary += f" · ~{total_cal:,} cal total"
st.caption(summary)

for d in WEEK:
    slot = _get_slot(d)
    is_today = d == date.today()
    day_label = DAY_LABELS[d]
    date_str = d.strftime("%b %d")

    with st.container(border=True):
        header_cols = st.columns([3, 1])
        with header_cols[0]:
            prefix = ":material/today: " if is_today else ""
            st.markdown(f"**{prefix}{day_label}** · {date_str}")
        with header_cols[1]:
            if slot.is_planned:
                if slot.meal_type == "eat_out":
                    st.badge("Eat out", icon=":material/restaurant:", color="orange")
                else:
                    st.badge("Home", icon=":material/home:", color="green")

        if slot.is_planned:
            content_cols = st.columns([1, 3])
            with content_cols[0]:
                if slot.meal_type == "recipe" and slot.recipe and slot.recipe.image_url:
                    st.image(slot.recipe.image_url, width=90)
                elif slot.meal_type == "eat_out":
                    st.markdown(":material/restaurant:")
                else:
                    st.markdown(":material/dinner_dining:")
            with content_cols[1]:
                st.markdown(f"**{slot.display_name}**")
                meta_parts = []
                time_info = _time_str(slot)
                if time_info:
                    meta_parts.append(time_info)
                if slot.calories:
                    meta_parts.append(f"~{slot.calories} cal/serving")
                if slot.recipe and slot.recipe.servings:
                    meta_parts.append(f"{slot.recipe.servings} servings")
                if meta_parts:
                    st.caption(" · ".join(meta_parts))
                if slot.meal_type == "eat_out" and slot.eat_out and slot.eat_out.notes:
                    st.caption(slot.eat_out.notes)
                if slot.recipe and slot.recipe.source_url:
                    st.caption(f"[View recipe]({slot.recipe.source_url})")

            action_cols = st.columns(2)
            with action_cols[0]:
                if st.button("Replace", key=f"replace_{d}", icon=":material/edit:", use_container_width=True):
                    st.session_state.editing_day = d.isoformat()
                    st.rerun()
            with action_cols[1]:
                if st.button("Clear", key=f"clear_{d}", icon=":material/close:", use_container_width=True):
                    state.dinners[d.isoformat()] = DinnerSlot(day=d.isoformat())
                    _save()
                    st.toast(f"Cleared {day_label}")
                    st.rerun()
        else:
            st.caption("No dinner planned")
            if st.button("Plan dinner", key=f"plan_{d}", icon=":material/add:", use_container_width=True):
                st.session_state.editing_day = d.isoformat()
                st.rerun()

if st.session_state.get("editing_day"):
    _render_edit_form(st.session_state["editing_day"])
