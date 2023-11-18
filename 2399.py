# imports needed to make web requests
import requests
import urllib
import json
import re

# imports needed for google docs
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# imports needed for system functions
import time
import sys
import locale
import threading
import queue
import datetime

# imports for UI
from tkinter import *
from tkinter import ttk

# sms timeout:  the amount of time to wait for the user to sms their notes before closing the time log row
def sms_timeout():
    return(7200) # (2 hours)

# tkinter keypress event (the barcode reader functions as a keyboard) - only allow digits for the user id's
def keydown(e):
    global G_win_mode
    keys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    for k in keys:
        if (e.char == k):
            key_queue.put(k)
            break
    # set the '*' key to a test user
    if (e.char == '*'):
        key_queue.put('2')
        key_queue.put('8')
        key_queue.put('0')

    if (e.char == '^'):
        if G_win_mode == "full":
            G_win_mode = "windowed"
            G_win.attributes("-fullscreen", False)
        else:
            G_win_mode = "full"
            G_win.attributes("-fullscreen", True)

# function to display currently logged in users
def user_display_update(roster):
    global G_roster
    global G_events
    rosterlist = []

    with roster_lock:
        for e in list(G_events):
            user_found = False
            for lp in range(0, len(G_roster)):
                if e == G_roster[lp]['HBID']:
                    user_found = True
                    if 'ClockIn' in G_events[e] and 'ClockOut' not in G_events[e]:
                        rosterlist.append(G_roster[lp]["StudentLast"].strip() + ", " + G_roster[lp]["StudentFirst"].strip() + " (" + G_events[e]["ClockIn"] + ")")
                    break
            if user_found == False:
                continue

    rosterlist.sort()
    rcnt = 0
    txt = ""
    for t in rosterlist:
        if txt != "":
            txt = txt + "\n"
        rcnt = rcnt + 1
        txt = txt + str(rcnt) + "." + t
    roster.config(text=txt)
    roster.place(x=10, y=70)

# main loop thread waits for someone to scan their barcode to create a clock event
def app_main_loop(roster):
    global G_events

    user_id = ""
    while True:

        # run this loop every 100 msec for timely barcode clock in/out processing
        time.sleep(0.1)

        if not key_queue.empty():
            user_id = user_id + key_queue.get()
        else:
            user_id = ""

        # user id must be 7 digits, so just loop if nothing to look up yet
        if len(user_id) != 7:
            continue

        # confirm valid user 
        with roster_lock:
            user_found = False
            for lp in range(0, len(G_roster)):
                if user_id == G_roster[lp]['HBID']:
                    user_found = True
                    break
            if user_found == False:
                continue

        # if user not yet clocked in, create new record
        if user_id not in G_events:
            G_events[user_id] = {}
            G_events[user_id]["ClockIn"] = datetime.datetime.now().strftime(timeformat)

        # else clock out
        else:
            if "ClockOut" not in G_events[user_id]:
                G_events[user_id]["ClockOut"] = datetime.datetime.now().strftime(timeformat)

        # refresh user display                
        user_display_update(roster)

# background loop to look for user clock events to write to google sheets
def app_post_loop(who, clock):
    global G_roster
    global G_events
    global G_win

    smspoll = 0
    sms = {}
    rosterreload = 0

    clockx = 1
    clockdx = 60
    clocky = 1
    clockdy = 20
    clockcolor = 'blue'

    while True:

        # loop runs on a 1 second interval to maintain the clockout timers
        time.sleep(1)

        # update on screen clock
        curtime = datetime.datetime.now().strftime('%H:%M:%S')
        clock.config(text=curtime)

        # do smspoll
        smspoll = smspoll + 1
        if smspoll == 5:
            smspoll = 0

            print(curtime + " : Processing sms")

            # loop through all rows that are pending sms
            try:
                cells = G_sheet_timelog.findall(re.compile('_sms'), in_column=1)
            except:
                cells = None

            for cell in cells:

                # extract user id for this row
                match = re.search('(.*)_', cell.value)
                user_id = match.group(1)

                # if row is past sms time collection window, close it to complete it
                if (datetime.datetime.now() - datetime.datetime.strptime(G_sheet_timelog.cell(cell.row, 3).value, timeformat)).total_seconds() >= sms_timeout():
                    try:
                        sts = G_sheet_timelog.update("A" + str(cell.row), user_id)
                    except:
                        pass

                    continue

                # find user's cell number
                user_cell = ""
                for member in G_roster:
                    if user_id == member["HBID"]:
                        user_cell = member["StudentCell"]
                        break

                # user cell number found, so poll it for inbound sms
                if user_cell != "":
                    d = {'remote' : user_cell}
                    srow = str(cell.row)
                    rsp = requests.post("https://1.terazero.com/smsread", headers={'Content-Type': 'application/json'}, data=json.dumps(d))
                    jd = json.loads(rsp.text)
                    if "text" in jd:
                        if srow not in sms:
                             sms[srow] = jd["text"]
                        else:
                            sms[srow] = sms[srow] + jd["text"]

                    # attempt to update google sheet with sms
                    try:
                        cursms = G_sheet_timelog.acell("D" + srow).value
                        if cursms == None:
                            cursms = sms[srow]
                        else:
                            cursms = cursms + sms[srow]
                        G_sheet_timelog.update("D" + srow, cursms)
                        del sms[srow]
                    except:
                        pass

        # don't do anything if no outstanding events
        if len(list(G_events)) == 0 and len(list(G_roster)) != 0:
            who.place_forget()

            clock.config(fg=clockcolor, font='Arial 56 bold')
            clock.place(x=clockx, y=clocky)
            colorchange = False

            tx = G_win.winfo_width()
            if clockx + clockdx < 0 or clockx + clockdx > tx - clock.winfo_width():
                clockdx *= -1
                colorchange = True
            clockx = clockx + clockdx

            ty = G_win.winfo_height()
            if clocky + clockdy < 0 or clocky + clockdy > ty - clock.winfo_height():
                clockdy *= -1
                colorchange = True
            clocky = clocky + clockdy

            if colorchange == True:
                if clockcolor == 'blue':
                    clockcolor = 'red'
                else:
                    clockcolor = 'blue'                

            continue
        else:
            who.place(x=5, y=5)
            clock.config(fg='yellow', font='Arial 24 bold')
            clock.place(x=G_win.winfo_width() - clock.winfo_width(), y=1)
            pass

        # roster is reloaded every 10 minutes when there are open events
        rosterreload = rosterreload + 1
        if rosterreload == 600 or len(list(G_roster)) == 0:
            print(curtime + " : roster reload")
            rosterreload = 0
            with roster_lock:
                try:
                    # pull roster in two steps in case google rate limits
                    roster_tmp = G_sheet_roster.get_all_records()
                    G_roster = roster_tmp
                except:
                    pass

                # fixup numerics to strings for later comparisons
                for member in G_roster:
                    member["HBID"] = str(member["HBID"])
                    member["StudentCell"] = str(member["StudentCell"])
                    member["ParentCell"] = str(member["ParentCell"])

        # loop to process clock events
        for e in list(G_events):

            # find user belonging to this event
            user_id = ""
            user_first = ""
            user_cell = ""
            for lp in range(0, len(G_roster)):
                if e == G_roster[lp]['HBID']:
                    user_id = e
                    user_first = G_roster[lp]["StudentFirst"].strip()
                    user_cell = G_roster[lp]["StudentCell"].strip()
                    break

            # not a valid user, so dump event
            if user_id == "":
                del G_events[e]
                continue

            # process new clock in event
            if "ClockIn" in G_events[e] and not "_clockout" in G_events[e]:
                print(curtime + " : new clock in")
                # update or add pending row to time log (this may fail due to google rate limiting, so it will keep retrying each cycle)
                try:
                    row = [user_id + "_clockout", G_events[e]["ClockIn"], "", ""]
                    cell = G_sheet_timelog.find(user_id + "_clockout")
                    if cell:
                        srow = str(cell.row)
                        sts = G_sheet_timelog.update("A" + srow + ":D" + srow, [row])
                    else:
                        sts = G_sheet_timelog.append_row(row)
                    G_events[e]["_clockout"] = True
                except:
                    pass

            # process new clock out event
            if "ClockOut" in G_events[e]:
                print(curtime + " : new clock out")

                # send reminder text to the user to enter their notes
                if user_cell != "" and not "sms_sent" in G_events[e]:
                    try:
                        d1 = datetime.datetime.strptime(G_events[e]["ClockIn"], timeformat)
                        d2 = datetime.datetime.strptime(G_events[e]["ClockOut"], timeformat)
                        diff = str(datetime.timedelta(seconds=(d2 - d1).total_seconds() + 60))
                        tmsg = "Hi " + user_first + ", reply with how you spent your " + diff[:-3] + " today at robotics."
                        d = {"remote" : user_cell, "text" : tmsg}
                        rsp = requests.post("https://1.terazero.com/smssend", headers={'Content-Type': 'application/json'}, data=json.dumps(d))
                        G_events[e]["sms_sent"] = True
                    except:
                        pass
                
                # update pending row in time log (this may fail due to google rate limiting, so it will keep retrying each cycle)
                cell = G_sheet_timelog.find(user_id + "_clockout")
                if cell:
                    row = [user_id + "_sms", G_events[e]["ClockIn"], G_events[e]["ClockOut"], ""]
                    srow = str(cell.row)
                    sts = G_sheet_timelog.update("A" + srow + ":D" + srow, [row])
                del G_events[e]


if __name__ == "__main__":

    timeformat = "%Y-%m-%d %H:%M:%S"
    key_queue = queue.Queue()

    # set our credentials to access google docs
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
    client = gspread.authorize(creds)

    # open workbook
    G_workbook = client.open("StudentAttendance2324")

    # get workbook tabs
    G_sheet_roster = G_workbook.worksheet("Roster")
    G_sheet_timelog = G_workbook.worksheet("TimeLog")

    # roster memory structure
    G_roster = {}
    roster_lock = threading.Lock()

    # events memory structure
    G_events = {}

    # Create the ui
    global G_win_mode
    G_win_mode = "windowed"
    global G_win
    G_win = Tk()
    G_win.title("2399 Timeclock")
    G_win.bind("<KeyPress>", keydown)
    G_win.attributes("-topmost", True)
    G_win.geometry("640x480")
    G_win.configure(cursor="none", background="black")

    who = Label(G_win, text="Who's here today:", fg="cyan", bg="black", font='Arial 32 bold', anchor='w')
    clock = Label(G_win, text="00:00:00", bg="black", font='Arial 24 bold', anchor='w')
    roster = Label(G_win, text=" ", fg="green", bg="black", font='Arial 18', anchor='w')

    # run the main logic loop in a different thread
    main_loop_thread = threading.Thread(target=app_main_loop, args=(roster,))
    main_loop_thread.daemon = True
    main_loop_thread.start()
    
    # run the post logic loop in a different thread
    post_loop_thread = threading.Thread(target=app_post_loop, args=(who, clock,))
    post_loop_thread.daemon = True
    post_loop_thread.start()
    
    # run the UI's main loop
    G_win.mainloop()

