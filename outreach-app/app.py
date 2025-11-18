import multiprocessing
from pathlib import Path

import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

import secrets

app = Flask(__name__)
secretpath = Path(__file__).parent.parent / "timeclock24/2399_secret.json"

# Define the scope and credentials for Google Sheets API
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(secretpath, scope)
client = gspread.authorize(credentials)

G_workbook = client.open("Outreach Event Data Collection (Cleaned-up Version)")
G_sheet_outreach = G_workbook.worksheet("2025-2026") # name of worksheet

def refresh_sheet(sheet, _lock=multiprocessing.Lock()):
    with _lock:
        data = sheet.get_all_records()
        return data
    
G_outreach = refresh_sheet(G_sheet_outreach)   

# Convert G_outreach into a JSON-serializable structure
EVENTS = []
for row in G_outreach:
    event = {
        "title": row.get("Event Name", ""),
        "date": row.get("Date", ""),
        "location": row.get("Location", ""),
        "description": row.get("Description", ""),
        "community": row.get("Community", ""),
        "first": row.get("FIRST Definition", ""),
        "headcount": row.get("Attendee Headcount", ""),
        # Add more fields as needed based on your sheet columns
    }
    EVENTS.append(event)

@app.route('/events', methods=['GET'])
def get_events():
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    # TODO: Filtering
    filtered_events = EVENTS

    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_events = filtered_events[start:end]

    return jsonify({
        "events": paginated_events,
        "page": page,
        "per_page": per_page,
        "total": len(filtered_events)
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0")