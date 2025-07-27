from google.oauth2.service_account import Credentials
from src.logger import logger
import pandas as pd
import gspread
from gspread.utils import ValueInputOption
import os


def update_sheet(csv_path: str, sheet_name: str, credentials_json: str):
    """
    Append all entries from CSV to Google Sheet in first empty row of A-K,
    then empty the CSV while preserving headers.
    """
    try:
        # Set up authentication and open the sheet
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(credentials_json, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open(sheet_name)
        sheet = spreadsheet.sheet1

        # Read CSV
        if not os.path.exists(csv_path) or os.stat(csv_path).st_size == 0:
            logger.warning(f"CSV at {csv_path} is empty or doesn't exist, nothing to append.")
            return

        df = pd.read_csv(csv_path)
        if df.empty:
            logger.warning(f"CSV at {csv_path} is empty, nothing to append.")
            return

        # Convert all rows to list of strings (only A-K columns)
        all_rows = []
        for i in range(len(df)):
            row = [str(x) for x in df.iloc[i].values.tolist()][:11]
            all_rows.append(row)

        # Find first empty row by checking columns A-K
        existing_data = sheet.get_values("A:K")  # Get all values in A-K columns

        # Find first completely empty row
        next_row = 1
        for i, row in enumerate(existing_data, start=1):
            if any(cell.strip() != "" for cell in row):
                next_row = i + 1
            else:
                next_row = i
                break

        # If no empty rows found, start after last row
        if next_row > len(existing_data):
            next_row = len(existing_data) + 1

        # Update sheet with all new rows
        if all_rows:
            start_range = f"A{next_row}"
            sheet.update(
                range_name=start_range,
                values=all_rows,
                value_input_option=ValueInputOption.user_entered
            )
            logger.info(f"Appended {len(all_rows)} rows starting at row {next_row} to Google Sheet '{sheet_name}'.")

            # Empty CSV while preserving headers
            df.head(0).to_csv(csv_path, index=False)

    except Exception as e:
        logger.error(f"Error updating Google Sheet: {e}")