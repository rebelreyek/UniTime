# imports needed to make web requests
import datetime
import json
import math

# imports needed for system functions
import os
import queue
import time
from pathlib import Path

# imports for UI
from tkinter import *
from tkinter import simpledialog

# imports needed for google docs
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def disable_event():
    pass

def reload_sheeet(sheetname, jsonfile):
    global G_sheet_data
    global G_roster
    global G_dates

    try: 
        # capture current sign-in states so we can preserve them after reload
        curr_status = {}
        try:
            if isinstance(G_roster, list):
                for member in G_roster:
                    if "HBID" in member and "ClockIn" in member:
                        curr_status[str(member["HBID"])] = member["ClockIn"]
        except Exception:
            curr_status = {}

        # open workbook
        G_workbook = client.open("StudentAttendance2627")

        # get workbook tab
        G_sheet_data = G_workbook.worksheet(sheetname)

        # memory structure
        G_sheet = {}

        if sheetname == "Roster":
            G_sheet = G_sheet_data.get_all_records()
            for member in G_sheet:
                if "HBID" in member:
                    member["HBID"] = str(member["HBID"])
                    # restore ClockIn if present in old roster
                    hb = member["HBID"]
                    if hb in curr_status:
                        try:
                            member["ClockIn"] = curr_status[hb]
                        except Exception:
                            pass
            # update in-memory roster so display_refresh sees changes
            G_roster = G_sheet

        elif sheetname == "Dates":
            G_sheet = G_sheet_dates.col_values(1)
            
            G_sheet = G_sheet[1:] # skip header row
            
            for date in G_sheet:
                date = datetime.datetime.strptime(date, "%Y-%m-%d")
            G_dates = G_sheet

        # remove existing file so consumers reload cleanly
        try:
            if os.path.exists(jsonfile):
                os.remove(jsonfile)
        except Exception:
            pass

        # write the freshly fetched sheet data to the jsonfile
        f = open(jsonfile, "w")
        f.write(json.dumps(G_sheet, indent=4))
        f.close()
    except Exception:
        print("Failed to reload " + sheetname + " from google.")

def display_refresh():
    global G_win
    global G_roster

    for child in G_win.winfo_children():
        if type(child) != Label:
            continue

        r = child.grid_info()['row'] + 1
        c = child.grid_info()['column'] + 1

        mtxt = ""
        fgcolor = "lightgrey"
        for member in G_roster:
            if member["grow"] == r and member["gcol"] == c:
                mtxt = member["StudentFirst"]
                if "ClockIn" in member:
                    fgcolor = "mediumvioletred"
                else:
                    fgcolor = "lightgrey"

        child.config(text=mtxt, fg=fgcolor)


def next_grid(roster):
    if not roster:
        return 1, 1

    last_member = roster[-1]
    if "grow" not in last_member or "gcol" not in last_member:
        return 1, 1

    row = int(last_member["grow"])
    col = int(last_member["gcol"])

    if col < 7:
        return row, col + 1

    if row >= 9:
        return None

    return row + 1, 1

def prompt_new_student(user_id):
    global G_main

    first = simpledialog.askstring("New Student", "StudentFirst:", parent=G_main)
    if first is None:
        return None
    first = first.strip()

    last = simpledialog.askstring("New Student", "StudentLast:", parent=G_main)
    if last is None:
        return None
    last = last.strip()

    email = simpledialog.askstring("New Student", "StudentEmail:", parent=G_main)
    if email is None:
        return None
    email = email.strip()

    if not first or not last or not email:
        return None

    return {
        "HBID": str(user_id),
        "StudentFirst": first,
        "StudentLast": last,
        "StudentEmail": email,
    }


def append_new_student_to_roster(member):
    global G_roster
    global G_sheet_data

    if not isinstance(G_roster, list):
        G_roster = []

    slot = next_grid(G_roster)
    if slot is None:
        return False

    row, col = slot

    member["grow"] = row
    member["gcol"] = col
    member["HBID"] = str(member["HBID"])
    member["Leadership"] = "FALSE"
    member["Rookie"] = "FALSE"
    member["StudentCell"] = ""
    member["DOB"] = ""
    member["Grade"] = ""
    member["ParentName1"] = ""
    member["ParentCell1"] = ""
    member["ParentEmail1"] = ""
    member["ParentName2"] = ""
    member["ParentCell2"] = ""
    member["ParentEmail2"] = ""
    member["ParentName3"] = ""
    member["ParentCell3"] = ""
    member["ParentEmail3"] = ""
    member["ParentName4"] = ""
    member["ParentCell4"] = ""
    member["ParentEmail4"] = ""
    member["Varsity?"] = ""

    try:
        headers = G_sheet_data.row_values(1)
    except Exception:
        headers = [
            "HBID",
            "StudentEmail",
            "StudentLast",
            "StudentFirst",
            "Leadership",
            "Rookie",
            "grow",
            "gcol",
            "StudentCell",
            "DOB",
            "Grade",
            "ParentName1",
            "ParentCell1",
            "ParentEmail1",
            "ParentName2",
            "ParentCell2",
            "ParentEmail2",
            "ParentName3",
            "ParentCell3",
            "ParentEmail3",
            "ParentName4",
            "ParentCell4",
            "ParentEmail4",
            "Varsity?",
        ]

    row_values = []
    for header in headers:
        value = member.get(header, "")
        if value is None:
            value = ""
        row_values.append(value)

    G_sheet_data.append_row(row_values, value_input_option="USER_ENTERED")
    G_roster.append(member)

    f = open("roster.json", "w")
    f.write(json.dumps(G_roster, indent=4))
    f.close()

    return True

# tkinter keypress event (the barcode reader functions as a keyboard) - only allow digits for the user id's
def keydown(e):
    global G_roster
    keys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    for k in keys:
        if (e.char == k):
            key_queue.put(k)
            break
    # set the '*' key to a test user
    if (e.char == '*'):
        key_queue.put('2')
        key_queue.put('3')
        key_queue.put('9')
        key_queue.put('9')
        key_queue.put('6')
        key_queue.put('9')
        key_queue.put('5')
    if (e.char == '!'):
        reload_sheeet("Dates", "dates.json")
        reload_sheeet("Roster", "roster.json")
        display_refresh()
        print("Reloaded data from google.")
    

def checkdate(dates):
    log_name = "logs/{d.year}{d.month:02}{d.day:02}".format(d=datetime.datetime.now())
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    for date in dates:
        if date == today:
            log_name = log_name + "A"
            break
    log_name = log_name + ".log"

    return log_name

if __name__ == "__main__":

    mypath = Path(__file__).parent.as_posix()

    if os.environ.get('DISPLAY','') == '':
        print('no display found. Using :0.0')
        os.environ.__setitem__('DISPLAY', ':0.0')

    timeformat = "%Y-%m-%d %H:%M:%S"
    key_queue = queue.Queue()

    clockx = 1
    clockdx = 6
    clocky = 1
    clockdy = 2
    clockcolor = 'dodgerblue'

    # set our credentials to access google docs
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(mypath + '/2399_secret.json', scope)
    client = gspread.authorize(creds)

    # open workbook
    G_workbook = client.open("StudentAttendance2627")

    # get workbook tabs
    G_sheet_data = G_workbook.worksheet("Roster")
    G_sheet_dates = G_workbook.worksheet("Dates")

    # memory structure
    G_roster = {}
    G_dates = {}

    # try loading from local json
    try:
        f = open("roster.json", "r")
        G_roster = json.load(f)
        f.close()
        print("Roster loaded from local file roster.json.  Delete to load from google.")
    except:
        G_roster = G_sheet_data.get_all_records()
        print("Local file roster.json not found.  Roster loaded from google.")

        # fixup numerics to strings for later comparisons
        for member in G_roster:
            member["HBID"] = str(member["HBID"])
        #     member["StudentCell"] = str(member["StudentCell"])
        #     member["ParentCell"] = str(member["ParentCell"])

    # load special dates from local json
    try:
        f = open("dates.json", "r")
        G_dates = json.load(f)
        f.close()
        print("Special dates loaded from local file dates.json.")
    except:
        G_dates = G_sheet_dates.col_values(1)
        print("Local file dates.json not found.  Dates loaded from google.")

        G_dates = G_dates[1:] # skip header row

        for date in G_dates:
            date = datetime.datetime.strptime(date, "%Y-%m-%d")

    rows, cols = (9, 7)
    arr = rows * [[0] * cols]

    G_main = Tk()
    G_main.configure(cursor="none", background="black")
    G_main.attributes("-fullscreen", True)
    G_main.bind("<KeyPress>", keydown)
    clock = Label(G_main, text="00:00:00", bg="black", anchor='w')
    who = Label(G_main, text="Who's here today", fg="SteelBlue1", bg="black", font='Arial 40 bold', anchor='w')
    image = PhotoImage(file = "2399.png")
    imagelab = Label(G_main, image=image, borderwidth=0)

    G_win = Toplevel(G_main)
    G_win.geometry("1366x768") # pi screen is 800x480, 2399-ds is 1366x768
    G_win.configure(cursor="none", background="black")
    G_win.transient(G_main)
    G_win.overrideredirect(1)

    for r in range(0, 9):
        for c in range(0, 7):
            mtxt = ""
            for member in G_roster:
                if member["grow"] == r + 1 and member["gcol"] == c + 1:
                    mtxt = member["StudentFirst"]
                    #mtxt = member["StudentFirst"][0] + member["StudentLast"][0]
                    if "ClockIn" in member:
                        fgcolor = "mediumvioletred"
                    else:
                        fgcolor = "lightgrey"
            Label(G_win,
            text = mtxt,
            font = ("Arial", 20, "bold"),
            fg = fgcolor,
            bg = "lavenderblush",
            justify = "center",
            width = 9,
            height = 2).grid(row = r, column = c, sticky = W, padx = 2, pady = 2)

    # main program loop
    user_id = ""
    while True:

        # run this loop every 100 msec for timely barcode clock in/out processing
        # keep window at the foreground
        #G_win.grab_set()
        G_win.geometry("+40+60")

        G_main.update()

        time.sleep(0.1)

        screensave = True
        for member in G_roster:
            if "ClockIn" in member:
                screensave = False
                break

        curtime = datetime.datetime.now().strftime('%H:%M:%S')
        clock.config(text=curtime)
        if screensave == True:
            G_win.withdraw()
            who.place_forget()
            clock.place_forget()
            #clock.config(fg=clockcolor, font='Arial 20 bold')
            #clock.place(x=clockx, y=clocky)
            imagelab.place(x=clockx, y=clocky)
            colorchange = False

            tx = G_main.winfo_width()
            if clockx + clockdx < 0 or clockx + clockdx > tx - imagelab.winfo_width():
                clockdx *= -1
                colorchange = True
            clockx = clockx + clockdx

            ty = G_main.winfo_height()
            if clocky + clockdy < 0 or clocky + clockdy > ty - imagelab.winfo_height():
                clockdy *= -1
                colorchange = True
            clocky = clocky + clockdy

            if colorchange == True:
                if clockcolor == 'blue':
                    clockcolor = 'red'
                else:
                    clockcolor = 'blue'

        else:
            G_win.deiconify()
            who.place(x=1, y=1)
            imagelab.place_forget()
            clock.config(fg='firebrick1', font='Arial 20 bold')
            clock.place(x=G_main.winfo_width() - clock.winfo_width(), y=1)
        
        if key_queue.empty():
            user_id = ""
        else:
            while not key_queue.empty():
                user_id = user_id + key_queue.get()

        # user id must be 7 digits, so just loop if nothing to look up yet
        if len(user_id) != 7:
            continue

        # confirm valid user 
        user_found = False
        for member in G_roster:
            if member["HBID"] == user_id:
                user_found = True
                G_member = member
                grow = member["grow"]
                gcol = member["gcol"]
                break

        if user_found == True:
            for child in G_win.winfo_children():

                if type(child) != Label:
                    continue

                r = child.grid_info()['row'] + 1
                c = child.grid_info()['column'] + 1

                if r == grow and c == gcol:
                    if "ClockIn" not in G_member:
                        G_member["ClockIn"] = datetime.datetime.now().strftime(timeformat)
                        child['fg'] = "mediumvioletred"
                        print(G_member["ClockIn"] + " CLOCK IN:  " + G_member["StudentFirst"])
                    else:
                        # calculate total time spent at robotics
                        G_member["ClockOut"] = datetime.datetime.now().strftime(timeformat)
                        delta = datetime.datetime.strptime(G_member["ClockOut"], timeformat) - datetime.datetime.strptime(G_member["ClockIn"], timeformat)
                        delta = delta.total_seconds() / 60.0

                        # round to the upper 5 minutes
                        delta = int(math.ceil(delta / 5.0)) * 5

                        # write logs longer than 12hrs or shorter than 5min as 0
                        if delta <= 5 or delta > 720:
                            delta = 0
                        logname = checkdate(G_dates)
                        l = G_member["HBID"] + "\t" + G_member["StudentFirst"] + "\t" + G_member["ClockIn"] + "\t" + G_member["ClockOut"] + "\t" + str(delta) + "\r"
                        f = open(logname, "a")
                        f.write(l)
                        f.close()
                        child['fg'] = "lightgrey"
                        print(G_member["ClockOut"] + " CLOCK OUT: " + G_member["StudentFirst"])
                        del G_member["ClockIn"]
                        del G_member["ClockOut"]
                    f = open("roster.json", "w")
                    f.write(json.dumps(G_roster, indent=4))
                    f.close()
        else:
            newbie = prompt_new_student(user_id)
            if newbie is not None:
                try:
                    if append_new_student_to_roster(newbie):
                        reload_sheeet("Roster", "roster.json")
                        display_refresh()
                        print("ADDED NEW STUDENT: " + newbie["StudentFirst"] + " " + newbie["StudentLast"] + " (" + user_id + ")")
                except Exception as exc:
                    print("Failed to add unknown student to roster: " + str(exc))
            else:
                print("Unknown barcode ignored: " + user_id)