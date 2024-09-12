from flask import Flask, request, jsonify, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials

attendance = Flask(__name__)

# Define the scope and credentials for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
client = gspread.authorize(credentials)

# Open your Google Sheet by title
G_workbook = client.open("StudentAttendance2425") # name of workbook
G_sheet_roster = G_workbook.worksheet("Cumulative") # name of worksheet
G_team = G_sheet_roster.get_all_records() # all data in worksheet in json

# landing page to search for student ID
@attendance.route('/')
def index():
    return render_template('homepage.html')

@attendance.route('/get_data', methods=['GET'])
def get_data():
    id_number = request.args.get('id')

    if not id_number:
        return jsonify({"error": "ID number not provided"})

    try:
        cell_list = G_sheet_roster.findall(id_number)
        if cell_list:
            # Take the first cell found
            cell = cell_list[0]
            row = cell.row
            data = G_sheet_roster.row_values(row)

            # pull out student name
            stuName = data[2]

            results = { "name": stuName }
            return render_template('test.html', results = results)


        else:
            return jsonify({"error": "ID not found"})
    except Exception as e:
        return jsonify({"hanna is bad at writing exceptions"})

if __name__ == '__main__':
    attendance.run(debug=False)