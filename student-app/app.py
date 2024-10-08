from flask import Flask, request, jsonify, render_template
import gspread, json
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
secretpath = 'C:/Users/hanna keyerleber/Documents/GitHub/UniTime/'

# Define the scope and credentials for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(secretpath + '2399_secret.json', scope)
client = gspread.authorize(credentials)

G_workbook = client.open("StudentAttendance2425") # name of workbook
G_sheet_roster = G_workbook.worksheet("Cumulative") # name of worksheet
G_roster = G_sheet_roster.get_all_records()

# fix up to string
for member in G_roster:
            member["HBID"] = str(member["HBID"])

@app.route('/')
def home():
    return render_template('homepage.html')

@app.route('/get_data', methods=['GET'])
def get_data():
    try:
        id_number = request.args.get('id')

        if not id_number:
            error_msg = "No ID Provided"
            return render_template('error.html', error_msg = error_msg)
        elif len(id_number) != 7:
            error_msg = "Invalid ID"
            return render_template('error.html', error_msg = error_msg)

        user_found = False
        for member in G_roster:
            if member["HBID"] == id_number:
                user_found = True
                break
        if user_found:
            data = student_data(member)
            return render_template('display.html', data = data)
        else:
            error_msg = "HBID not found"
            return render_template('error.html', error_msg = error_msg)
    
    except Exception as e:
        error_msg = "Hanna is bad at writing code" + e
        return render_template('error.html', error_msg = error_msg)
    
def load_roster():
    # Open your Google Sheet by title
    G_workbook = client.open("StudentAttendance2425") # name of workbook
    G_sheet_roster = G_workbook.worksheet("Cumulative") # name of worksheet
    G_roster = G_sheet_roster.get_all_records()

    # fix up to string
    for member in G_roster:
        member["HBID"] = str(member["HBID"])
        
    return G_roster

def student_data(member):
    outreach_hrs = 20
    tech_hrs = 125
    name = member["Name"]

    if member["Rookie"] == "TRUE":
        outreach_hrs = 10

    if member["Leadership"] == "TRUE":
         tech_hrs = 175

    data = {"name": name, "outreach": outreach_hrs, "tech": tech_hrs}
    return data
     

if __name__ == '__main__':
    app.run(debug=True)