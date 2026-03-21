from __future__ import annotations
from typing import Optional
import requests
import streamlit as st


BASE_URL = "https://api.spoonacular.com"


def _api_key() -> str:
    return st.secrets.get("SPOONACULAR_API_KEY", "")


@st.cache_data(ttl=600, show_spinner=False)
def search_recipes(
    query: str,
    number: int = 9,
    cuisine: str = "",
    diet: str = "",
    meal_type: str = "",
    max_ready_time: Optional[int] = None,
) -> list[dict]:
    key = _api_key()
    if not key or key == "YOUR_SPOONACULAR_API_KEY_HERE":
        return []

    params = {
        "apiKey": key,
        "query": query,
        "number": number,
        "addRecipeNutrition": True,
        "addRecipeInformation": True,
        "fillIngredients": True,
        "instructionsRequired": True,
    }
    if cuisine:
        params["cuisine"] = cuisine
    if diet:
        params["diet"] = diet
    if meal_type:
        params["type"] = meal_type
    if max_ready_time:
        params["maxReadyTime"] = max_ready_time

    results = _do_search(params)

    if not results and len(query.split()) > 2:
        shorter = " ".join(query.split()[:2])
        params["query"] = shorter
        results = _do_search(params)

    if not results and (cuisine or diet or meal_type or max_ready_time):
        params = {
            "apiKey": key,
            "query": query,
            "number": number,
            "addRecipeNutrition": True,
            "addRecipeInformation": True,
            "fillIngredients": True,
        }
        results = _do_search(params)

    return results


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
