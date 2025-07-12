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
    
    # Get latest uploaded date
    existing_data = sheet.get_all_values()
    
    if len(existing_data) < 2:
        latest_uploaded_date = None
    else:
        latest_uploaded_date = existing_data[1][0]
    # Read CSV
    df = pd.read_csv(CSV_URL)
    df = df.astype(str)
    new_rows = []
    
    for _, row in df.iterrows():
        if row['date'] == latest_uploaded_date:
            break
        new_rows.append(row.tolist())
    
    new_rows.reverse()
    
    for row in new_rows:
        sheet.append_row(row)
    
    print(f"✅ {len(new_rows)} new rows added.")

except Exception as e:
    print(f"❌ ERROR: {e}")
    raise
