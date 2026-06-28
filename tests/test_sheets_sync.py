import pandas as pd
import pytest

from utils import sheets_sync


class StubSheet:
    def __init__(self):
        self.cleared = False
        self.updated_rows = None

    def clear(self):
        self.cleared = True

    def update(self, rows):
        self.updated_rows = rows


class StubSpreadsheet:
    def __init__(self, sheet):
        self.sheet1 = sheet


class StubClient:
    def __init__(self, sheet):
        self.sheet = sheet
        self.created = None

    def open(self, sheet_name):
        return StubSpreadsheet(self.sheet)

    def create(self, sheet_name):
        self.created = sheet_name
        return StubSpreadsheet(self.sheet)


def test_sync_to_sheets(monkeypatch):
    sheet = StubSheet()
    client = StubClient(sheet)

    monkeypatch.setattr(
        sheets_sync.Credentials,
        "from_service_account_info",
        staticmethod(lambda payload: {"creds": payload}),
    )
    monkeypatch.setattr(sheets_sync.gspread, "authorize", lambda creds: client)

    df = pd.DataFrame({"customer_id": [1, 2], "score": [0.87, 0.45]})
    success = sheets_sync.sync_to_google_sheets(
        df,
        "Test_Scored_Customers",
        {"type": "service_account"},
    )

    assert success is True
    assert sheet.cleared is True
    assert sheet.updated_rows[0] == ["customer_id", "score"]
    assert sheet.updated_rows[1][0] == 1
    assert sheet.updated_rows[1][1] == 0.87
    assert sheet.updated_rows[2][0] == 2
    assert sheet.updated_rows[2][1] == 0.45


def test_sync_to_sheets_raises_clear_error_when_gspread_missing(monkeypatch):
    monkeypatch.setattr(
        sheets_sync.Credentials,
        "from_service_account_info",
        staticmethod(lambda payload: {"creds": payload}),
    )

    def fail_authorize(_creds):
        raise RuntimeError(
            "gspread is required for Google Sheets sync. "
            "Install requirements-streamlit.txt to enable this integration."
        )

    monkeypatch.setattr(sheets_sync.gspread, "authorize", fail_authorize)

    with pytest.raises(RuntimeError, match="gspread is required"):
        sheets_sync.sync_to_google_sheets(
            pd.DataFrame({"customer_id": [1]}),
            "Missing_Dependency",
            {"type": "service_account"},
        )
