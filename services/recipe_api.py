from __future__ import annotations
from typing import Optional
import requests
import streamlit as st


BASE_URL = "https://api.spoonacular.com"
PREFERRED_SOURCES = ["skinnytaste.com"]


def _api_key() -> str:
    return st.secrets.get("SPOONACULAR_API_KEY", "")


def _base_params(key: str, number: int) -> dict:
    return {
        "apiKey": key,
        "number": number,
        "addRecipeNutrition": True,
        "addRecipeInformation": True,
        "fillIngredients": True,
        "instructionsRequired": True,
    }


@st.cache_data(ttl=600, show_spinner=False)
def search_recipes(
    query: str,
    number: int = 12,
    cuisine: str = "",
    diet: str = "",
    meal_type: str = "",
    max_ready_time: Optional[int] = None,
    include_ingredients: str = "",
    sort: str = "popularity",
) -> list[dict]:
    key = _api_key()
    if not key or key == "YOUR_SPOONACULAR_API_KEY_HERE":
        return []

    fetch_n = min(number * 2, 24)
    all_results: list[dict] = []
    seen_ids: set[int] = set()

    def _collect(hits: list[dict]):
        for r in hits:
            rid = r.get("id")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                all_results.append(r)

    params = _base_params(key, fetch_n)
    params["query"] = query
    params["sort"] = sort
    params["sortDirection"] = "desc" if sort == "popularity" else "asc"
    if cuisine:
        params["cuisine"] = cuisine
    if diet:
        params["diet"] = diet
    if meal_type:
        params["type"] = meal_type
    if max_ready_time:
        params["maxReadyTime"] = max_ready_time
    if include_ingredients:
        params["includeIngredients"] = include_ingredients

    _collect(_do_search(params))

    if len(all_results) < number:
        params2 = _base_params(key, fetch_n)
        params2["query"] = query
        params2["sort"] = sort
        params2["sortDirection"] = "desc" if sort == "popularity" else "asc"
        if include_ingredients:
            params2["includeIngredients"] = include_ingredients
        if cuisine:
            params2["cuisine"] = cuisine
        if diet:
            params2["diet"] = diet
        _collect(_do_search(params2))

    if len(all_results) < number and len(query.split()) > 2:
        params3 = _base_params(key, fetch_n)
        params3["query"] = " ".join(query.split()[:2])
        params3["sort"] = sort
        params3["sortDirection"] = "desc" if sort == "popularity" else "asc"
        if include_ingredients:
            params3["includeIngredients"] = include_ingredients
        if cuisine:
            params3["cuisine"] = cuisine
        if diet:
            params3["diet"] = diet
        _collect(_do_search(params3))

    if len(all_results) < number:
        params4 = _base_params(key, fetch_n)
        params4["query"] = query
        params4["sort"] = sort
        params4["sortDirection"] = "desc" if sort == "popularity" else "asc"
        _collect(_do_search(params4))

    ranked = _rank(all_results, query, include_ingredients)
    return ranked[:number]


def _rank(results: list[dict], query: str, include_ingredients: str) -> list[dict]:
    q_words = set(query.lower().split())
    ing_words = set()
    if include_ingredients:
        ing_words = {w.strip().lower() for w in include_ingredients.split(",") if w.strip()}

    def _score(r: dict) -> float:
        s = 0.0
        title = (r.get("title") or "").lower()
        title_words = set(title.split())
        overlap = q_words & title_words
        if overlap:
            s += 10 * (len(overlap) / len(q_words))
        if all(w in title for w in q_words):
            s += 15

        if ing_words:
            r_ings = " ".join(r.get("ingredients") or []).lower()
            matched = sum(1 for w in ing_words if w in r_ings)
            s += 8 * (matched / len(ing_words))

        if _is_preferred(r):
            s += 5

        agg = r.get("aggregate_likes") or r.get("spoonacular_score") or 0
        if agg:
            s += min(agg / 100, 3)

        return s

    return sorted(results, key=_score, reverse=True)


def _is_preferred(r: dict) -> bool:
    url = (r.get("source_url") or "").lower()
    return any(src in url for src in PREFERRED_SOURCES)


def _do_search(params: dict) -> list[dict]:
    try:
        resp = requests.get(
            f"{BASE_URL}/recipes/complexSearch",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json().get("results", [])
        return [_parse_search_result(r) for r in raw]
    except Exception:
        return []


def _parse_search_result(r: dict) -> dict:
    calories = None
    nutrients = r.get("nutrition", {}).get("nutrients", [])
    for n in nutrients:
        if n.get("name", "").lower() == "calories":
            calories = int(n.get("amount", 0)) or None
            break

    ingredients = []
    for ing in r.get("extendedIngredients", []):
        orig = ing.get("original", "")
        if orig:
            ingredients.append(orig)

    return {
        "id": r.get("id"),
        "title": r.get("title", ""),
        "image_url": r.get("image", ""),
        "source_url": r.get("sourceUrl", ""),
        "prep_minutes": r.get("preparationMinutes") or r.get("prepTime") or None,
        "cook_minutes": r.get("cookingMinutes") or None,
        "total_minutes": r.get("readyInMinutes") or None,
        "calories_per_serving": calories,
        "servings": r.get("servings"),
        "description": r.get("summary", "")[:200] if r.get("summary") else "",
        "ingredients": ingredients,
        "aggregate_likes": r.get("aggregateLikes", 0),
        "spoonacular_score": r.get("spoonacularScore", 0),
    }


@st.cache_data(ttl=600, show_spinner=False)
def get_recipe_detail(recipe_id: int) -> Optional[dict]:
    key = _api_key()
    if not key or key == "YOUR_SPOONACULAR_API_KEY_HERE":
        return None
    try:
        resp = requests.get(
            f"{BASE_URL}/recipes/{recipe_id}/information",
            params={"apiKey": key, "includeNutrition": True},
            timeout=10,
        )
        resp.raise_for_status()
        return _parse_search_result(resp.json())
    except Exception:
        return None
