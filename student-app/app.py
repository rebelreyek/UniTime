from pathlib import Path

from flask import Flask, request, jsonify, render_template
import gspread, json
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

app = Flask(__name__)
secretpath = Path(__file__).parent.parent / '2399_secret.json'

# Define the scope and credentials for Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(secretpath, scope)
client = gspread.authorize(credentials)

G_workbook = client.open("StudentAttendance2425") # name of workbook
G_sheet_roster = G_workbook.worksheet("Cumulative") # name of worksheet
G_roster = G_sheet_roster.get_all_records()

# fix up to string
for member in G_roster:
            member["HBID"] = str(member["HBID"])

@app.route('/')
def home():
    return render_template('homepage.html.jinja')

@app.route('/get_data', methods=['GET'])
def get_data():
    try:
        id_number = request.args.get('id')

        if not id_number:
            error_msg = "No ID Provided"
            return render_template('error.html.jinja', error_msg = error_msg)
        elif len(id_number) != 7:
            error_msg = "Invalid ID"
            return render_template('error.html.jinja', error_msg = error_msg)

        user_found = False
        for member in G_roster:
            if member["HBID"] == id_number:
                user_found = True
                break
        if user_found:
            data = student_data(member)
            return render_template('display.html.jinja', data = data)
        else:
            error_msg = "HBID not found"
            return render_template('error.html.jinja', error_msg = error_msg)
    
    except Exception as e:
        error_msg = "Hanna is bad at writing code: " + e
        return render_template('error.html.jinja', error_msg = error_msg)

# may be irrelevant if we just reboot the app every day at 3am   
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
    # general requirements
    outreach_target = 20
    tech_target = 125
    pre_target = 30
    biz_target = 3

    # 8 week build season
    jv_build = 24 # 8x3
    v_build = 72 # 8x9

    # honors - blanket across the board, so could live somewhere else. or here
    biz_honors = 6
    outreach_honors = 35
    tech_honors = 250

    name = member["Name"]

    if member["Rookie"] == "TRUE":
        outreach_target = 10

    if member["Leadership"] == "TRUE":
        v_build = 96 # 8x12
        tech_target = 175
        if member["HBID"] == "7071199": # captain (CH) ID
            v_build = 120 # 8x15
            tech_target = 200 # this is not in the handbook (oops)

    pre_hrs = member["Pre-Season"]
    build_hrs = member["Build Season"]
    tech_hrs = member["Total Tech Hours"]
    outreach_hrs = member["Outreach"]
    business_obj = member["Business"]
    outreach_ec = False

    if member["Outreach EC"] == "TRUE":
        outreach_ec = True

    data = {"name": name, 
            "outreach_target": outreach_target, 
            "tech_target": tech_target,
            "biz_target": biz_target,
            "pre_target": pre_target,
            "jv_build": jv_build,
            "v_build": v_build,
            "pre_hrs": pre_hrs,
            "build_hrs": build_hrs,
            "tech_hrs": tech_hrs,
            "outreach_hrs": outreach_hrs,
            "biz_obj": business_obj,
            "outreach_ec": outreach_ec,
    }
    return data
     

if __name__ == '__main__':
    app.run(host='0.0.0.0')
