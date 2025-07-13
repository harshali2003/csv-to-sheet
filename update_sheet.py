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

    # Read raw CSV (no header)
    raw = pd.read_csv(CSV_URL, header=None)
    num_columns = raw.shape[1]
    num_rows = raw.shape[0]

    blocks = []

    for col in range(0, num_columns, 10):  # 8 data cols + 2 gap
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

    # Pad all blocks to have same height
    max_height = max(len(block) for block in blocks)
    for i in range(len(blocks)):
        while len(blocks[i]) < max_height:
            blocks[i].append([""] * 8)

    # Build final sheet grid
    final_data = []
    for row_idx in range(max_height):
        row = []
        for block in blocks:
            row.extend(block[row_idx])
            row.extend(["", ""])  # 2 column gap
        final_data.append(row)

    # Clear existing sheet
    sheet.clear()

    # Push final data
    sheet.update("A1", final_data)

    print(f"✅ Sheet updated with {len(blocks)} blocks and {len(final_data)} rows.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
