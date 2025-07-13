import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials as GoogleCredentials

# CONFIG
CSV_URL = "https://raw.githubusercontent.com/harshali2003/csv-to-sheet/refs/heads/main/dev-int.csv"
SPREADSHEET_ID = "1_XanKnA9VBUVkF8O729Dp-LK-tuH_4y34-lGKme4b1U"
CREDENTIALS_FILE = "creds.json"

try:
    # Setup Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    scoped_creds = GoogleCredentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    service = build("sheets", "v4", credentials=scoped_creds)

    # Read raw CSV (no header)
    raw = pd.read_csv(CSV_URL, header=None)
    num_columns = raw.shape[1]
    num_rows = raw.shape[0]

    blocks = []

    for col in range(0, num_columns, 10):  # 8 data cols + 2 gap
        if pd.isna(raw.iloc[0, col]):
            continue

        block = []
        for row in range(1, num_rows):  # skip header
            if pd.isna(raw.iloc[row, col]):
                break
            block.append([
                float(raw.iloc[row, col + i]) if pd.notna(raw.iloc[row, col + i]) and str(raw.iloc[row, col + i]).strip().replace('.', '', 1).isdigit()
                else str(raw.iloc[row, col + i]).strip()
                for i in range(1, 8)
            ])
        blocks.append(block)

    # Reverse blocks so latest is last
    blocks.reverse()

    # Pad all blocks to same height
    max_height = max(len(block) for block in blocks)
    for i in range(len(blocks)):
        while len(blocks[i]) < max_height:
            blocks[i].append([""] * 7)

    # Get current column count (from sheet)
    sheet_data = sheet.get_all_values()
    existing_col_count = len(sheet_data[0]) if sheet_data else 0

    # Find next start column (must be ≥ 9 to protect A–I)
    start_col = max(existing_col_count, 9)

    requests = []

    for block in blocks:
        date = str(block[0][0])  # first data row's date (in date cell)

        # Prepare top row
        top_row = [date] + [""] * 6
        header_row = [str(raw.iloc[0, i + 1]).strip() for i in range(7)]  # skip date col

        # Insert top row
        requests.append({
            "updateCells": {
                "rows": [{"values": [{"userEnteredValue": {"stringValue": cell}} for cell in top_row]}],
                "fields": "*",
                "start": {
                    "sheetId": sheet._properties["sheetId"],
                    "rowIndex": 0,
                    "columnIndex": start_col
                }
            }
        })

        # Merge date cell
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet._properties["sheetId"],
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": start_col,
                    "endColumnIndex": start_col + 7
                },
                "mergeType": "MERGE_ALL"
            }
        })

        # Insert header row
        requests.append({
            "updateCells": {
                "rows": [{"values": [{"userEnteredValue": {"stringValue": cell}} for cell in header_row]}],
                "fields": "*",
                "start": {
                    "sheetId": sheet._properties["sheetId"],
                    "rowIndex": 1,
                    "columnIndex": start_col
                }
            }
        })

        # Insert data rows
        for i in range(max_height - 1):
            row_data = block[i + 1]
            cell_values = []
            for val in row_data:
                if isinstance(val, float) or isinstance(val, int):
                    cell_values.append({"userEnteredValue": {"numberValue": float(val)}})
                else:
                    cell_values.append({"userEnteredValue": {"stringValue": val}})
            requests.append({
                "updateCells": {
                    "rows": [{"values": cell_values}],
                    "fields": "*",
                    "start": {
                        "sheetId": sheet._properties["sheetId"],
                        "rowIndex": i + 2,
                        "columnIndex": start_col
                    }
                }
            })

        # Move to next block (7 cols data + 2 gap)
        start_col += 9

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()

    print("✅ Sheet updated without touching static columns A–I.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
