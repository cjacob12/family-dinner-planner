from __future__ import annotations
import json
from pathlib import Path
import streamlit as st
from models import AppState

DATA_FILE = Path(__file__).parent.parent / "meal_plan.json"


def _use_gsheets() -> bool:
    return bool(st.secrets.get("GSHEETS_URL", "") or st.secrets.get("GSHEETS_KEY", ""))


def load_state() -> AppState:
    if _use_gsheets():
        from services.gsheets_storage import load_state_gsheets
        return load_state_gsheets()
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as f:
                return AppState.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError):
            pass
    return AppState()


def save_state(state: AppState) -> None:
    if _use_gsheets():
        from services.gsheets_storage import save_state_gsheets
        save_state_gsheets(state)
        return
    with open(DATA_FILE, "w") as f:
        json.dump(state.to_dict(), f, indent=2)
