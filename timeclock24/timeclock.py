# imports needed to make web requests
import requests
import urllib
import json
import re
import math

# imports needed for google docs
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# imports needed for system functions
import os
import time
import sys
import locale
import threading
import queue
import datetime
from pathlib import Path

# imports for UI
from tkinter import *
from tkinter import ttk

def disable_event():
    pass

# tkinter keypress event (the barcode reader functions as a keyboard) - only allow digits for the user id's
def keydown(e):
#    global G_win_mode
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

if __name__ == "__main__":

    mypath = "C:/Users/Owner/Documents/GitHub/UniTime/timeclock24/"

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
    creds = ServiceAccountCredentials.from_json_keyfile_name(mypath + '2399_secret.json', scope)
    client = gspread.authorize(creds)

    # open workbook
    G_workbook = client.open("StudentAttendance2425")

    # get workbook tabs
    G_sheet_roster = G_workbook.worksheet("Roster")
    # G_sheet_timelog = G_workbook.worksheet("TimeLog")

    # roster memory structure
    G_roster = {}

    # try loading from local json
    try:
        f = open("roster.json", "r")
        G_roster = json.load(f)
        f.close()
        print("Roster loaded from local file roster.json.  Delete to load from google.")
    except:
        G_roster = G_sheet_roster.get_all_records()
        print("Local file roster.json not found.  Roster loaded from google.")

        # fixup numerics to strings for later comparisons
        for member in G_roster:
            member["HBID"] = str(member["HBID"])
        #     member["StudentCell"] = str(member["StudentCell"])
        #     member["ParentCell"] = str(member["ParentCell"])

    rows, cols = (8, 7)
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

    for r in range(0, 8):
        for c in range(0,7):
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
            width = 10,
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

        # user id must be 3 digits, so just loop if nothing to look up yet
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

                        l = G_member["HBID"] + "\t" + G_member["StudentFirst"] + "\t" + G_member["ClockIn"] + "\t" + G_member["ClockOut"] + "\t" + str(delta) + "\r"
                        f = open("logs/{d.year}{d.month:02}{d.day:02}.log".format(d=datetime.datetime.now()), "a")
                        f.write(l)
                        f.close()
                        child['fg'] = "lightgrey"
                        print(G_member["ClockOut"] + " CLOCK OUT: " + G_member["StudentFirst"])
                        del G_member["ClockIn"]
                        del G_member["ClockOut"]
                    f = open("roster.json", "w")
                    f.write(json.dumps(G_roster, indent=4))
                    f.close()