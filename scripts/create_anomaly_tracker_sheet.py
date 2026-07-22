import gspread
import sys

def main():
    try:
        # 1. Authenticate using the service account credentials
        gc = gspread.service_account(filename="credentials.json")

        # 2. Open the existing Google Spreadsheet
        sheet_key = "10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U"
        print(f"Opening spreadsheet with key: '{sheet_key}'...")
        sh = gc.open_by_key(sheet_key)

        # 3. Rename the default sheet to "Anomalies"
        worksheet = sh.sheet1
        worksheet.update_title("Anomalies")

        # 4. Write the header row
        headers = [
            "audit_date", "audit_run_id", "target_name", "record_id",
            "resource_name", "parameter_name", "unit", "observed_value",
            "group_mean", "group_std", "group_n", "z_score", "severity",
            "analyst_email", "Status", "Analyst Notes"
        ]
        worksheet.update([headers], "A1")

        print("\nSpreadsheet formatted successfully!")
        print(f"URL: {sh.url}")
        print(f"KEY: {sh.id}")

        print("\nAdd the following to your .env file:")
        print(f"AUDITOR_ANOMALY_TRACKER_SHEET_KEY={sh.id}")

    except Exception as e:
        print(f"Error formatting spreadsheet: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
