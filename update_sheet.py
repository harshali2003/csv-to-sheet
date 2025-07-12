import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# CONFIG
CSV_URL = "https://raw.githubusercontent.com/harshali2003/csv-to-sheet/refs/heads/main/dev-int.csv"
SPREADSHEET_ID = "1_XanKnA9VBUVkF8O729Dp-LK-tuH_4y34-lGKme4b1U"
CREDENTIALS_FILE = "creds.json"

try:
    # Setup Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    # Get existing data
    existing_data = sheet.get_all_values()
    existing_headers = existing_data[0] if existing_data else []
    uploaded_dates = set(row[0] for row in existing_data[1:]) if len(existing_data) > 1 else set()

    # Read CSV (no header)
    raw = pd.read_csv(CSV_URL, header=None)
    num_columns = raw.shape[1]
    num_rows = raw.shape[0]

    rows_to_upload = []

    for col in range(0, num_columns, 10):  # 8 data columns + 2 gaps
        if pd.isna(raw.iloc[0, col]):
            continue

        # Read headers
        headers = [str(raw.iloc[0, col + i]).strip() for i in range(8)]

        # Only write headers once
        if not existing_headers:
            sheet.append_row(headers)
            existing_headers = headers

        # Loop through all rows starting from row 1 (data rows)
        for row_idx in range(1, num_rows):
            if pd.isna(raw.iloc[row_idx, col]):
                break  # End of data block

            values = [str(raw.iloc[row_idx, col + i]).strip() for i in range(8)]
            date = values[0]

            # Skip if already uploaded
            if date in uploaded_dates:
                continue

            rows_to_upload.append(values)

    # Older dates first
    rows_to_upload.reverse()

    for row in rows_to_upload:
        sheet.append_row(row)

    print(f"✅ {len(rows_to_upload)} new rows added.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
