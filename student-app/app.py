import importlib.util
import multiprocessing
from pathlib import Path

import gspread
from flask import Flask, jsonify, render_template, request
from oauth2client.service_account import ServiceAccountCredentials


def load_local_secrets_module():
    secrets_path = Path(__file__).resolve().with_name("secrets.py")
    spec = importlib.util.spec_from_file_location("student_app_secrets", secrets_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load secrets module from {secrets_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


secrets = load_local_secrets_module()

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates"),
)


def resolve_secret_path():
    candidates = [
        Path(__file__).resolve().parent.parent / "timeclock24" / "2399_secret.json",
        Path(__file__).resolve().parent.parent / "2399_secret.json",
        Path("/app/timeclock24/2399_secret.json"),
        Path("/app/2399_secret.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


secretpath = resolve_secret_path()
if not secretpath.exists():
    raise FileNotFoundError(f"Google service account file not found at {secretpath}")

# Define the scope and credentials for Google Sheets API
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(str(secretpath), scope)
client = gspread.authorize(credentials)


G_workbook = client.open("StudentAttendance2627")  # name of workbook
G_sheet_data = G_workbook.worksheet(
    "Cumulative"
)  # name of worksheet with cumulative data
G_sheet_checklist = G_workbook.worksheet(
    "Checklist"
)  # name of worksheet with checklist items

def refresh_sheet(sheet, _lock=multiprocessing.Lock()):
    with _lock:
        data = sheet.get_all_records()
        # fix up to string
        for member in data:
            member["HBID"] = str(member["HBID"])
        return data

G_data = refresh_sheet(G_sheet_data)
G_checklist = refresh_sheet(G_sheet_checklist)


@app.route("/refresh", methods=["POST"])
def refresh():
    global G_data, G_checklist
    G_data = refresh_sheet(G_sheet_data)
    G_checklist = refresh_sheet(G_sheet_checklist)
    refresh = len(G_data)
    return jsonify({"refreshed": refresh})

@app.route("/")
def home():
    return render_template("homepage.html.jinja")


@app.route("/resources")
def resources():
    resource_links = [
        {
            "title": "Team Handbook",
            "description": "Read the team handbook and key policies.",
            "url": secrets.handbook_link,
        },
        {
            "title": "Student/Parent Contracts",
            "description": "Read the handbook and submit your student/parent contracts.",
            "url": secrets.contract_link,
        },
        {
            "title": "Team Registration",
            "description": "Register for the team with FIRST.",
            "url": secrets.first_link,
        },
        {
            "title": "V3 Off-Season Registration",
            "description": "Register for V3, held on October 18th.",
            "url": secrets.v3_registration_link,
        },
        {
            "title": "Pre-Season Attendance Sheet",
            "description": "Please fill out your weekly Pre-Season Attendance.",
            "url": secrets.preseason_attendance_link,
        },
        {
            "title": "Discord",
            "description": "Join the team Discord.",
            "url": secrets.discord_link,
        },
    ]
    return render_template("resources.html.jinja", resources=resource_links)


@app.route("/calendar")
def calendar():
    return render_template("calendar.html.jinja")


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
        discord = member["Discord"]

        checklist = {
            "FIRST Online Registration": [FIRST, "Register for the team with FIRST", secrets.first_link],
            "2399 Student Contract": [SC, "Read our handbook and the team contracts", secrets.contract_link],
            "2399 Parent Contract": [PC, "Read our handbook and the team contracts", secrets.contract_link],
            "Discord": [discord, "Join the team Discord", secrets.discord_link],
            "Battery Safety Training": [battery, "Battery saftey training quiz", secrets.battery_quiz],
            "695 Liability Waiver (Optional)": [bison, "", ""]
        }

        for item in checklist:
            if checklist[item] == "TRUE":
                checklist[item] = True
            else:
                checklist[item] = False

        return checklist
    except Exception as e:
        print("Error loading checklist: " + str(e))
        return {}
    
def student_meetings(member):
    try:
        pass
    except Exception as e:
        print("Error loading meetings: " + str(e))
        return {}


if __name__ == "__main__":
    app.run(host="0.0.0.0")
