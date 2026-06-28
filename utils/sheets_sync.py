try:
    import gspread
except ModuleNotFoundError:
    class _MissingGSpreadModule:
        class SpreadsheetNotFound(Exception):
            """Fallback exception shim when gspread is not installed."""

        @staticmethod
        def authorize(_creds):
            raise RuntimeError(
                "gspread is required for Google Sheets sync. "
                "Install requirements-streamlit.txt to enable this integration."
            )

    gspread = _MissingGSpreadModule()

try:
    from google.oauth2.service_account import Credentials
except ModuleNotFoundError:
    class _MissingCredentials:
        @staticmethod
        def from_service_account_info(_payload):
            raise RuntimeError(
                "google-auth is required for Google Sheets sync. "
                "Install requirements-streamlit.txt to enable this integration."
            )

    Credentials = _MissingCredentials


def sync_to_google_sheets(df, sheet_name, credentials_dict):
    """Sync a dataframe to a Google Sheet using a service account payload."""
    creds = Credentials.from_service_account_info(credentials_dict)
    client = gspread.authorize(creds)

    try:
        sheet = client.open(sheet_name).sheet1
    except gspread.SpreadsheetNotFound:
        sheet = client.create(sheet_name).sheet1

    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    return True
