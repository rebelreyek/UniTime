# imports needed to make web requests
import requests
import urllib
import json
import re

# imports needed for google docs
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# imports needed for system functions
import os
import time
import sys
import csv
import locale
import threading
import queue
import datetime

if __name__ == "__main__":

    mypath = Path(__file__).parent.as_posix()
    logfiles = mypath + "/logs/"

    # set our credentials to access google docs
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(mypath + '/2399_secret.json', scope)
    client = gspread.authorize(creds)

    # open workbook
    G_workbook = client.open("StudentAttendance2526")

    # get workbook timelog tab
    preseason_timelog = G_workbook.worksheet("PreSeason")
    tech_timelog = G_workbook.worksheet("TechHours")

    # loop to upload any log files
    # files are deleted if uploaded successfully
    directory = os.fsencode(logfiles)
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith("A.log"):
            content = list(csv.reader(open(logfiles + filename), delimiter='\t'))
            try:
                preseason_timelog.append_rows(content, value_input_option="USER_ENTERED")
                os.remove(logfiles + filename)
            except:
                pass
        else:
            content = list(csv.reader(open(logfiles + filename), delimiter='\t'))
            try:
                tech_timelog.append_rows(content, value_input_option="USER_ENTERED")
                os.remove(logfiles + filename)
            except:
                pass
