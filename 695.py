# imports needed to make web requests
import requests
import urllib
import json

# imports needed for google docs
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# imports needed for system functions
import time
import sys
import locale
import threading
import queue
from datetime import datetime

# imports for UI
from tkinter import *
from tkinter import ttk

# clockout timer to write to google sheets (in seconds)
# (this is the amount of time to wait for the user to sms their notes before writing to the time log)
def get_clockout_timer():
    return(1800) # (the user gets 30 minutes to sms...)

# tkinter keypress event (the qr reader functions as a keyboard) - only allow digits for the user id's
def keydown(e):
    keys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    for k in keys:
        if (e.char == k):
            key_queue.put(k)
            break
    # set the '*' key to a test user (281=Hanna)
    if (e.char == '*'):
        key_queue.put('2')
        key_queue.put('8')
        key_queue.put('1')

# function to display currently logged in users
def user_display_update(roster):
    rosterlist = []
    for lp in range(0, len(G_team)):
        if 'ClockIn' in G_team[lp] and 'ClockOut' not in G_team[lp]:
            rosterlist.append(G_team[lp]["StudentLast"].strip() + ", " + G_team[lp]["StudentFirst"].strip() + " (" + G_team[lp]["ClockIn"] + ")")
    rosterlist.sort()
    txt = ""
    for t in rosterlist:
        if txt != "":
            txt = txt + "\n"
        txt = txt + t
    roster.config(text=txt)

# main loop thread waits for someone to scan their qr
def app_main_loop(roster):

    user_id = ""
    while True:

        if not key_queue.empty():
            user_id = user_id + key_queue.get()
        else:
            user_id = ""

        if len(user_id) >= 6:

            # look for user in team roster
            for lp in range(0, len(G_team)):

                if user_id == str(G_team[lp]["HBID"]):

                    # if user has already clocked in, save clockout time and start the clockout timer
                    if "ClockIn" in G_team[lp]:
                        G_team[lp]["ClockOut"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        G_team[lp]["ClockOutTimer"] = get_clockout_timer()

                    # otherwise, clock in user
                    else:
                        G_team[lp]["ClockIn"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	# refresh clocked in user display                
                    user_display_update(roster)
                    break

        # run this loop every 100 msec for timely qr clock in/out processing
        time.sleep(0.1)

# background loop to look for clocked out users to write to google sheets
def app_post_loop():

    while True:

        # loop runs on a 1 second interval to maintain the clockout timers
        time.sleep(1)

        # loop to process user clock outs
        for lp in range(0, len(G_team)):

            stucell = G_team[lp]["StudentCell"].strip()

            # check if user is clocked out
            if "ClockOutTimer" in G_team[lp]:

                # check if user just clocked out
                if G_team[lp]["ClockOutTimer"] == get_clockout_timer():

                    # send reminder text to the user to enter their notes
                    if stucell != "":
                        d = {'remote' : stucell, 'text' : 'Hello ' + G_team[lp]["StudentFirst"].strip() + ', please reply with a summary of your work today.'}
                        rsp = requests.post("https://1.terazero.com/smssend", headers={'Content-Type': 'application/json'}, data=json.dumps(d))

                # check if user clockout period has timed out
                if G_team[lp]["ClockOutTimer"] == 0:

                    # get user's notes
                    if not "ClockOutNotes" in G_team[lp]:
                        d = {'remote' : stucell}
                        rsp = requests.post("https://1.terazero.com/smsread", headers={'Content-Type': 'application/json'}, data=json.dumps(d))
                        jd = json.loads(rsp.text)
                        G_team[lp]["ClockOutNotes"] = jd.get("text", "*no notes*")

                    # try to write record to sheets (this may fail due to google rate limiting, so it will just keep retrying each cycle)
                    row = [ G_team[lp]['HBID'], G_team[lp]["ClockIn"], G_team[lp]["ClockOut"], G_team[lp]["ClockOutNotes"] ]
                    try:
                        G_sheet_timelog.append_row(row)
                        del G_team[lp]["ClockIn"]
                        del G_team[lp]["ClockOut"]
                        del G_team[lp]["ClockOutTimer"]
                        del G_team[lp]["ClockOutNotes"]
                    except:
                        pass

                # otherwise, just decrement timeout period
                else:
                    G_team[lp]["ClockOutTimer"] = G_team[lp]["ClockOutTimer"] - 1       

if __name__ == "__main__":

    key_queue = queue.Queue()

    # set our credentials to access google docs
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
    client = gspread.authorize(creds)

    # open workbook - workbook name
    G_workbook = client.open("StudentAttendance2324")

    # get workbook tabs
    G_sheet_roster = G_workbook.worksheet("Roster")
    G_sheet_timelog = G_workbook.worksheet("TimeLog")

    # extract all rows from roster tab into json memory structure "G_team"
    G_team = G_sheet_roster.get_all_records()

    # fixup numeric phone numbers to strings for later comparisons
    for member in G_team:
        member["StudentCell"] = str(member["StudentCell"])
        member["ParentCell"] = str(member["ParentCell"])

    # dump local copy for diagnostics
    with open('G_team.json', 'w') as f:
        json.dump(G_team, f, indent=4)

    # Create the ui
    global G_win
    G_win = Tk()
    G_win.title("2399 Timeclock")
    G_win.bind("<KeyPress>", keydown)
#    G_win.geometry("640x480")
    G_win.attributes("-fullscreen", True)
    G_win.attributes("-topmost", True)
    G_win.configure(background="lightblue")

    label1 = Label(G_win, text="Team 2399 Members Currently Clocked-in:", bg="lightblue", font='Arial 24 bold', anchor='w')
    label1.place(x=10, y=10)

    roster = Label(G_win, text=" ", bg="lightblue", font='Arial 16', anchor='w')
    roster.place(x=10, y=50)

    # run the main logic loop in a different thread
    main_loop_thread = threading.Thread(target=app_main_loop, args=(roster,))
    main_loop_thread.daemon = True
    main_loop_thread.start()
    
    # run the post logic loop in a different thread
    post_loop_thread = threading.Thread(target=app_post_loop)
    post_loop_thread.daemon = True
    post_loop_thread.start()
    
    # run the UI's main loop
    G_win.mainloop()

