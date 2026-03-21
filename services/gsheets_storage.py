from __future__ import annotations
import json
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
from models import AppState

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DINNERS_SHEET = "dinners"
GROCERY_SHEET = "grocery"


def _get_client() -> gspread.Client:
    creds_info = st.secrets.get("gcp_service_account", {})
    if not creds_info:
        raise ValueError("Missing gcp_service_account in secrets.toml")
    creds = Credentials.from_service_account_info(dict(creds_info), scopes=SCOPES)
    return gspread.authorize(creds)


def _get_spreadsheet() -> gspread.Spreadsheet:
    client = _get_client()
    sheet_url = st.secrets.get("GSHEETS_URL", "")
    if sheet_url:
        return client.open_by_url(sheet_url)
    sheet_key = st.secrets.get("GSHEETS_KEY", "")
    if sheet_key:
        return client.open_by_key(sheet_key)
    raise ValueError("Set GSHEETS_URL or GSHEETS_KEY in secrets.toml")


def _ensure_worksheets(spreadsheet: gspread.Spreadsheet):
    titles = [ws.title for ws in spreadsheet.worksheets()]
    if DINNERS_SHEET not in titles:
        spreadsheet.add_worksheet(title=DINNERS_SHEET, rows=1, cols=1)
    if GROCERY_SHEET not in titles:
        spreadsheet.add_worksheet(title=GROCERY_SHEET, rows=1, cols=1)


def load_state_gsheets() -> AppState:
    try:
        ss = _get_spreadsheet()
        _ensure_worksheets(ss)
        dinners_ws = ss.worksheet(DINNERS_SHEET)
        dinners_json = dinners_ws.acell("A1").value
        grocery_ws = ss.worksheet(GROCERY_SHEET)
        grocery_json = grocery_ws.acell("A1").value
        data = {
            "dinners": json.loads(dinners_json) if dinners_json else {},
            "grocery": json.loads(grocery_json) if grocery_json else [],
        }
        return AppState.from_dict(data)
    except Exception:
        return AppState()


def save_state_gsheets(state: AppState) -> None:
    ss = _get_spreadsheet()
    _ensure_worksheets(ss)
    d = state.to_dict()
    dinners_ws = ss.worksheet(DINNERS_SHEET)
    dinners_ws.update_acell("A1", json.dumps(d["dinners"]))
    grocery_ws = ss.worksheet(GROCERY_SHEET)
    grocery_ws.update_acell("A1", json.dumps(d["grocery"]))
