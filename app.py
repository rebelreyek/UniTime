from flask import Flask, request, jsonify, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Define the scope and credentials for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
client = gspread.authorize(credentials)

# Open your Google Sheet by title
G_workbook = client.open("StudentAttendance2324") # name of workbook
G_sheet_roster = G_workbook.worksheet("Student") # name of worksheet
G_team = G_sheet_roster.get_all_records() # all data in worksheet in json

# landing page to search for student ID
@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/get_data', methods=['GET'])
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
            stuName = data[1]

            # pull out student data
            preHours = float(data[3])
            preTargetA = int(data[4])
            prePercentA = int(data[5])
            preTargetB = int(data[6])
            prePercentB = int(data[7])
            buildHours = float(data[8])
            buildTargetA = int(data[9])
            buildPercentA = int(data[10])
            buildTargetB = float(data[11])
            buildPercentB = int(data[12])
            techHours = float(data[13])
            techTarget = float(data[14])
            techPercent = int(data[15])
            outHours = float(data[16])
            outTarget = int(data[17])
            outPercent = int(data[18])
            bizObj = int(data[19])
            bizTarget = int(data[20])
            bizPercent = int(data[21])

            results = { "preHours": preHours, "prePercentA": prePercentA, "prePercentB": prePercentB, 
                        "preTargetA": preTargetA, "preTargetB": preTargetB, 
                        "buildHours": buildHours, "buildTargetA": buildTargetA, "buildTargetB": buildTargetB, 
                        "buildPercentA": buildPercentA, "buildPercentB": buildPercentB, 
                        "techHours": techHours, "techTarget": techTarget, "techPercent": techPercent,
                        "outPercent": outPercent, "outTarget": outTarget, "outHours": outHours,
                        "bizPercent": bizPercent, "bizTarget": bizTarget, "bizObj": bizObj}

            return render_template('display_data.html', stuName = stuName, results = results)


        else:
            return jsonify({"error": "ID not found"})
    except Exception as e:
        return jsonify({"hanna is bad at writing exceptions"})

if __name__ == '__main__':
    app.run(debug=True)