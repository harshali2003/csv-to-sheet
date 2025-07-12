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
    latest_uploaded_date = existing_data[-1][0] if len(existing_data) > 1 else None

    # Read the CSV without header
    raw = pd.read_csv(CSV_URL, header=None)
    num_columns = raw.shape[1]

    rows_to_upload = []

    for col in range(0, num_columns, 10):  # 8 columns of data + 2 gap
        if pd.isna(raw.iloc[0, col]):
            continue

        # Extract headers and values
        headers = [str(raw.iloc[0, col + i]).strip() for i in range(8)]
        values = [str(raw.iloc[1, col + i]).strip() for i in range(8)]

        date = values[0]
        if date == latest_uploaded_date:
            break

        # Write headers if sheet is empty
        if not existing_headers:
            sheet.append_row(headers)
            existing_headers = headers

        rows_to_upload.append(values)

    rows_to_upload.reverse()

    for row in rows_to_upload:
        sheet.append_row(row)

    print(f"✅ {len(rows_to_upload)} new rows added.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
