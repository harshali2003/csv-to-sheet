import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import set_column_width, CellFormat, format_cell_range
from gspread_formatting.dataframe import format_with_dataframe
from gspread_formatting import Borders, Color, TextFormat, set_frozen

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

    # Reverse blocks: latest date first
    blocks.reverse()

    # Pad all blocks to same height
    max_height = max(len(block) for block in blocks)
    for i in range(len(blocks)):
        while len(blocks[i]) < max_height:
            blocks[i].append([""] * 8)

    # Build merged top row with date labels
    top_row = []
    for block in blocks:
        date = block[1][0]  # first data row's date (row 1 because row 0 = header)
        top_row.extend([date] + [""] * 7)  # one date cell + 7 blanks
        top_row.extend(["", ""])  # 2 gaps

    # Build second row (headers) and rest data
    header_row = []
    for block in blocks:
        header_row.extend(block[0])  # actual headers
        header_row.extend(["", ""])

    data_rows = []
    for row_idx in range(1, max_height):
        row = []
        for block in blocks:
            row.extend(block[row_idx])
            row.extend(["", ""])
        data_rows.append(row)

    # Final sheet content
    final_data = [top_row, header_row] + data_rows

    # Clear and update
    sheet.clear()
    sheet.update("A1", final_data)

    # Merge date header cells
    requests = []
    col_index = 1
    for _ in blocks:
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet._properties['sheetId'],
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": col_index - 1,
                    "endColumnIndex": col_index - 1 + 8
                },
                "mergeType": "MERGE_ALL"
            }
        })
        col_index += 10  # 8 data cols + 2 gaps

    if requests:
        client.request('post', f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate',
                       json={"requests": requests},
                       headers={"Authorization": f"Bearer {creds.get_access_token().access_token}"})

    print(f"✅ Sheet updated with merged date headers and {len(data_rows)} data rows.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
