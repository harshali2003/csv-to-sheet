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

    # For Google API client
    scoped_creds = GoogleCredentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    service = build("sheets", "v4", credentials=scoped_creds)

    # Read raw CSV (no header)
    raw = pd.read_csv(CSV_URL, header=None)
    num_columns = raw.shape[1]
    num_rows = raw.shape[0]

    blocks = []

    for col in range(0, num_columns, 10):  # 8 data cols + 2 gaps
        if pd.isna(raw.iloc[0, col]):
            continue

        block = []
        for row in range(num_rows):
            if pd.isna(raw.iloc[row, col]):
                break
            block.append([str(raw.iloc[row, col + i]).strip() for i in range(8)])
        blocks.append(block)

    # Reverse blocks: latest first
    # blocks.reverse()

    # Pad all blocks to same height
    max_height = max(len(block) for block in blocks)
    for i in range(len(blocks)):
        while len(blocks[i]) < max_height:
            blocks[i].append([""] * 8)

    # Create top row with merged date labels
    top_row = []
    for block in blocks:
        date = block[1][0]  # first data row's date
        top_row.extend([date] + [""] * 7)
        top_row.extend(["", ""])  # 2 gap columns

    # Create second row with headers
    header_row = []
    for block in blocks:
        header_row.extend(block[0])  # actual headers like Module, T, P, ...
        header_row.extend(["", ""])

    # Create data rows
    data_rows = []
    for row_idx in range(1, max_height):
        row = []
        for block in blocks:
            row.extend(block[row_idx])
            row.extend(["", ""])
        data_rows.append(row)

    # Final data
    final_data = [top_row, header_row] + data_rows

    # Push data
    sheet.clear()
    sheet.update("A1", final_data)

    # Merge cells in top row for each date
    requests = []
    col_index = 0
    for _ in blocks:
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet._properties["sheetId"],
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": col_index,
                    "endColumnIndex": col_index + 8
                },
                "mergeType": "MERGE_ALL"
            }
        })
        col_index += 10  # 8 data + 2 gap

    # Execute merge requests
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()

    print(f"✅ Sheet updated with merged headers and {len(data_rows)} data rows.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
