import serial
import time
import re
import requests
import json

MODEM = '/dev/ttyUSB2'  # Modem hardware device
MODEM_BAUD_RATE = 115200  # Modem port speed
MODEM_CHAR_ENCODING = 'iso-8859-1'  # May or may not be your modem manufacturer's default encoding scheme
MODEM_CHAR_SET = 'AT+CSCS="IRA"'  # May or may not be your modem manufacturer's default character set
MODEM_TXT_MODE_PARAM = 'AT+CSMP=17,167,0,0'  # Typically your modem manufacturer's default text mode parameters
MODEM_MSG_FORMAT = 'AT+CMGF=1'  # Set the modem SMS mode to text or PDU format, typically this is =1 for text

# Function to send AT command to modem and get response
def send_at_command(command):
    modem.write(command.encode(MODEM_CHAR_ENCODING) + b'\r')
    time.sleep(1)
    response = modem.read_all().decode(MODEM_CHAR_ENCODING)
    return response

# Initialise modem connection
print("modem init")
modem = serial.Serial(MODEM, MODEM_BAUD_RATE, timeout=5)

# Send modem setup commands
print("modem setup")
send_at_command(MODEM_CHAR_SET)
#send_at_command(MODEM_TXT_MODE_PARAM)
send_at_command(MODEM_MSG_FORMAT)

# main loop
pollcnt = 60
while True:

    pollcnt = pollcnt + 1
    if pollcnt < 60:
        time.sleep(1)
        continue
    pollcnt = 0

    # query for messages
    print("")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("begin sms query")
    try:
        response = send_at_command("AT+CMGL=\"ALL\"")
    except:
        response = ""

    # parse messages
    print("\tparse")
    matches = re.findall("\+CMGL:(.*)", response)
    for m in matches:

        try:
            id = re.findall("(\d+),", m)
            msg = send_at_command("AT+CMGR=" + id[0])
            m = re.search("\+CMGR: \"(.+)\",\"(.+)\",,\"(.+)\"(.+)\nOK", msg, re.DOTALL)
            print(m.group(1))
            print("Numb: " + m.group(2))
            print("Date: " + m.group(3))
            print("Text: " + m.group(4).strip())
            requests.post("https://1.terazero.com/sms", json={"remote":m.group(2), "text":m.group(4).strip()})
            send_at_command("AT+CMGD=" + id[0])
            print("\t" + id[0] + ": " + m.group(4).strip())
        except:
            print("\tmsg bad: {" + m + "}")
            pass

    print("end sms query")

    #try:
    r = requests.post("https://1.terazero.com/smspoll")
    print(r)
    if 'remote' in r.json():
        print(r.json())
        send_at_command('AT+CMGS="{}"'.format(r.json()['remote']))
        modem.write(r.json()['text'].encode(MODEM_CHAR_ENCODING))
        modem.write(bytes([26]))  # ASCII code for Ctrl+Z
        time.sleep(1)
        response = modem.read_all().decode(MODEM_CHAR_ENCODING)
        pollcnt = 60
    #except:
    #    pass


# Close modem connection
modem.close()

