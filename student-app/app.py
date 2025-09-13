import multiprocessing
from pathlib import Path

import gspread
from flask import Flask, jsonify, render_template, request
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
secretpath = Path(__file__).parent.parent / "timeclock24/2399_secret.json"

# Define the scope and credentials for Google Sheets API
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(secretpath, scope)
client = gspread.authorize(credentials)


G_workbook = client.open("StudentAttendance2526")  # name of workbook
G_sheet_data = G_workbook.worksheet(
    "Cumulative"
)  # name of worksheet with cumulative data
G_sheet_checklist = G_workbook.worksheet(
    "Checklist"
)  # name of worksheet with checklist items


def refresh_data(_lock=multiprocessing.Lock()):
    with _lock:
        data = G_sheet_data.get_all_records()
        # fix up to string
        for member in data:
            member["HBID"] = str(member["HBID"])
        return data


def refresh_checklist(_lock=multiprocessing.Lock()):
    with _lock:
        checklist = G_sheet_checklist.get_all_records()
        # fix up to string
        for member in checklist:
            member["HBID"] = str(member["HBID"])
        return checklist


G_data = refresh_data()
G_checklist = refresh_checklist()


@app.route("/refresh", methods=["POST"])
def refresh():
    global G_data, G_checklist
    G_data = refresh_data()
    G_checklist = refresh_checklist()
    refresh = len(G_data) + len(G_checklist)
    return jsonify({"refreshed": refresh})


@app.route("/")
def home():
    return render_template("homepage.html.jinja")


@app.route("/get_data", methods=["GET"])
def get_data():
    try:
        id_number = request.args.get("id")

        if not id_number:
            error_msg = "No ID Provided"
            return render_template("error.html.jinja", error_msg=error_msg)
        elif len(id_number) != 7:
            error_msg = "Invalid ID"
            return render_template("error.html.jinja", error_msg=error_msg)

        user_found = False
        for member in G_data:
            if member["HBID"] == id_number:
                user_found = True
                break
        if user_found:
            data = student_data(member)
            for member in G_checklist:
                if member["HBID"] == id_number:
                    checklist = student_checklist(member)
                    break
            # TODO: dont show leadership JV
            return render_template("display.html.jinja", data=data, checklist=checklist)
        else:
            error_msg = "HBID not found"
            return render_template("error.html.jinja", error_msg=error_msg)

    except Exception as e:
        error_msg = "Hanna is bad at writing code: " + e
        return render_template("error.html.jinja", error_msg=error_msg)


# may be irrelevant if we just reboot the app every day at 3am
def load_data():
    # Open your Google Sheet by title
    G_workbook = client.open("StudentAttendance2526")  # name of workbook
    G_sheet_data = G_workbook.worksheet("Cumulative")  # name of worksheet
    G_data = G_sheet_data.get_all_records()

    # fix up to string
    for member in G_data:
        member["HBID"] = str(member["HBID"])

    return G_data


def load_checklist():
    # Open your Google Sheet by title
    G_workbook = client.open("StudentAttendance2526")  # name of workbook
    G_sheet_checklist = G_workbook.worksheet("Checklist")  # name of worksheet
    G_checklist = G_sheet_checklist.get_all_records()

    # fix up to string
    for member in G_checklist:
        member["HBID"] = str(member["HBID"])

    return G_checklist


def student_data(member):
    # general requirements
    outreach_target = 20
    tech_target = 125
    pre_target = 30
    biz_target = 3

    # 8 week build season
    jv_build = 24  # 8x3
    v_build = 72  # 8x9

    # honors - blanket across the board, so could live somewhere else. or here
    biz_honors = 6
    outreach_honors = 35
    tech_honors = 250

    # team meeting count - blanket across the board, so could live somehwere else. or here
    team_meeting = 8  # 8x1

    name = member["Name"]

    if member["Rookie"] == "TRUE":
        outreach_target = 10

    if member["Leadership"] == "TRUE":
        v_build = 96  # 8x12
        tech_target = 175

    pre_hrs = member["Pre-Season"]
    build_hrs = member["Build Season"]
    tech_hrs = member["Total Tech Hours"]
    outreach_hrs = member["Outreach"]
    business_obj = member["Business"]
    business_proof = member["Proofread"]
    business_fundraising = member["Value"]
    outreach_ec = False
    meet_attendance = member["Team Meetings"]

    if member["Outreach EC"] == "TRUE":
        outreach_ec = True

    data = {
        "name": name,
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
        "biz_fund": business_fundraising,
        "biz_proof": business_proof,
        "outreach_ec": outreach_ec,
        "meet_attendance": meet_attendance,
    }
    return data


def student_checklist(member):
    try:
        FIRST = member["FIRST"]
        SC = member["SC"]
        PC = member["PC"]
        bison = member["695"]
        battery = member["Battery"]

        checklist = {
            "FIRST Online Registration": FIRST,
            "2399 Student Contract": SC,
            "2399 Parent Contract": PC,
            "695 Liability Waiver": bison,
            "Battery Safety Training": battery,
        }

        return checklist
    except Exception as e:
        print("Error loading checklist: " + str(e))
        return {}


if __name__ == "__main__":
    app.run(host="0.0.0.0")
