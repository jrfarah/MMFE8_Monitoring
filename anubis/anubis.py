######################################################################################
# ANUBIS
# Program for monitoring low voltage power source in real time and over entire runs
# Created by Joseph Farah
#
# Written on: [Thursday, August 17th, 2017]
# Last updated: [Thursday, August 24th, 2017] by [Joseph Farah]
# Requires several files to run:
#   * db_loc.txt: contains a single line pointing both ANUBIS and the Matlab script 
#                 to the correct database  
#   * speed_run.m: a minimized data collection script, needs to be running while the 
#                  run is going
#
# Function arguments: --rnum, --threshold
#   * --rnum: the current run number, defaults to "notrun" if none is provided
#   * --threshold: the maximum voltage allowed before the program proceeds to 
#                  piss itself
#
# Example usage: python anubis.py --rnum 3522 --threshold 1.4e-3
######################################################################################



# module imports
from Tkinter import *
import sys
import os
import subprocess
from tkFileDialog import askopenfilename as selectFILE
from tkFileDialog import askdirectory as selectFOLDER
import tkMessageBox as tkmb
import random
import string
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import datetime
import argparse

# the only module that probably isn't installed default, yagmail
try:
    import yagmail
except: 
    print 'WARNING: CANNOT IMPORT YAGMAIL, CANNOT NOTIFY OF THRESHOLD VIOLATIONS'
    sys.exit()
# lppc automated email, lppcautomated@gmail.com, 42oxford

# for defaults, grab the most recently used database file
with open('db_loc.txt') as f:
    database_file = f.readline()

# a valve variable is used for temporary value storage while 
# applying a new value to a previously created class
valve = ""    

# lets the program know if its on the first iteration or not
# could be useful in the future for improved time reading
check_start = 1
start_time = 0
check_limit = 0

# default limit, can be changed either with command line
# args or by using the GUI
LIMIT = 1.5e-4

# email list, needs to be global
emails = []
uname = ""
passwd = ""

# command line argument stuff
parser = argparse.ArgumentParser(usage=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--rnum", default="notrun", help="run number")
parser.add_argument("--threshold", default=LIMIT, help="threshold value")
parser.add_argument("--emails", default="", help="list of emails, separated by commas. example: email@cern.ch,email.cern.ch", required=True)
parser.add_argument("--user", default="", help="username for alert system", required=True)
parser.add_argument("--pass", default="",help="password for alert system", required=True )

# class to allow user input for any variable
class element_input(object):
    def __init__(self, parent, text_to_display):
        top = self.top = Toplevel(parent)
        self.parent = parent
        Label(top, text=text_to_display).pack()
        self.e = Entry(top)
        self.e.pack(padx=5)
        b = Button(top, text="submit", command=self.enter_element)
        b.pack(pady=5)
        self.parent.wait_window(self.top)

    def enter_element(self):
        global valve
        valve = self.e.get()
        self.top.destroy()

# create a new run, can assign current date, threshold, and database file name/run_num
class newRun(object):
    def __init__(self, date, limit=1.5e-3):
        self.run_number = 0
        self.date = date
        self.db_file_name = ""
        self.limit = limit

    def generate_new_file(self):
        global database_file
        file_name = 'anubis_low-voltage_{0}_{1}.db'.format(self.run_number, self.date)
        command = 'touch {0}'.format(file_name)
        output = subprocess.check_output(command, shell=True)
        if output: print output
        self.db_file_name = file_name
        with open('db_loc.txt', "w") as db_loc:
            db_loc.write(self.db_file_name)

        database_file = self.db_file_name

    def change_run_number(self, new_rnum):
        self.run_number = new_rnum

# defining the tkinter window
main = Tk()

current_run = newRun(1)

def get_current_date():
    '''gets the current date and returns it in a human readable format'''
    return time.strftime("%d-%m-%Y")

def tail(f, n):
    '''grabs the last n lines from any file, formats it, and checks to see 
        if the voltage is more than the specified threshold'''
    result = subprocess.check_output("tail -n "+n+" "+f, shell=True)
    lines = result.splitlines()
    try:
        limit = current_run.limit
    except:
        limit = LIMIT

    print limit
    if check_limit == 1:
        for line in lines:
            y, x = line.split(',')
            if float(y) > float(limit):
                send_alert(time.strftime("%d/%m/%Y"),time.strftime("%I:%M:%S"), y,limit, emails, uname, passwd)
    return result

def send_alert(date, time, voltage, threshold, email_list, username, password):
    '''email-sending protocol, simplified using yagmail'''
    yag = yagmail.SMTP(username, password)
    message = 'ALERT: ANUBIS recorded a voltage on {0} at {1} on [whatever circuit] that exceeded the threshold of {2} V. The recorded voltage was {3} V'.format(str(date), str(time), str(threshold), str(voltage))
    contents = [message]
    yag.send(email_list, 'Test alert', contents)

def update_voltage_db():
    '''update the voltage database view. helpful for checking to see if the 
       matlab program is actually receiving any data'''
    global voltage_db_view
    voltage_db_view.delete('1.0', END)
    try:
        voltage_db_view.insert(INSERT, tail(database_file,'10'))
    except:
        print 'problem with tailing file'
    voltage_db_view.see(END)
    main.after(2500, update_voltage_db)

def new_run_function():
    '''generates a new Run object and walks the user through configuring the run correctly'''
    global current_run, valve
    current_run = newRun(get_current_date())
    element_input(main, "Please input the run number.\nDo not start the data collection until this step is complete.")
    current_run.change_run_number(valve)
    tkmb.showinfo("Run number change", "You have selected the current number as {0}".format(current_run.run_number))
    element_input(main, "Please input the voltage threshold in volts (V).\nDo not start the data collection until this step is complete.")
    current_run.limit = valve
    print current_run.limit

def get_current_run_info():
    '''display all current run object attributes, in terminal and in GUI'''
    global current_run
    print current_run.date
    print current_run.run_number
    print current_run.db_file_name
    tkmb.showinfo("Current object info", "{0}\n{1}\n{2}\n".format(current_run.date, current_run.run_number, current_run.db_file_name))

def generate_new_empty_database():
    '''writes a new empty database file with the function built into the Run object'''
    current_run.generate_new_file()
    tkmb.showinfo("Success", "Database successfully generated, filename {0}".format(current_run.db_file_name))

def graph_data_real_time():
    '''call the animation that allows the graph to display real time data'''
    fig = plt.figure()
    ax1 = fig.add_subplot(1,1,1)
    ani = animation.FuncAnimation(fig, animate, interval=500, fargs=(ax1,))
    plt.show(block=True)

def animate(i, ax1):
    '''the animation function'''
    global current_run, check_start, start_time
    # change this value to change the number of data points shown in the 
    # real time graph window
    MAX_LENGTH = 50
    try:
        LIMIT = current_run.limit
    except:
        LIMIT = 1.5e-3
    try:
        with open(current_run.db_file_name,'r') as gd:
            graph_data = gd.read()
    except IOError:
        with open(database_file,'r') as gd:
            graph_data = gd.read()
    lines = graph_data.split('\n')
    y, x = lines[0].split(',')
    if check_start == 1:
        start_time = format_x(x)
        check_start = 0
    xs = []
    ys = []
    # the "zs" is the function that graphs the threshold
    zs = []
    time_since_beginning = len(lines)/4
    for line in lines:
        if len(line) > 1:
            try:
                y, x = line.split(',')
                ys.append(float(y))
                xs.append(format_x(x))
            except:
                pass
            zs.append(LIMIT)
    if len(ys) > MAX_LENGTH:
        ys = ys[len(ys)-MAX_LENGTH:]
        xs = xs[len(ys)-MAX_LENGTH:]
        zs = zs[len(zs)-MAX_LENGTH:]
    ax1.clear()
    ax1.plot(ys)
    ax1.plot(zs)
    ax1.set_xlabel("{0} seconds since the start of the run".format(str(time_since_beginning)))
    ax1.set_ylabel("Voltage (volts)")

def graph_data_total_set():
    '''graph entire dataset in one shot--does NOT update automatically, needs refreshing'''
    fig = plt.figure()
    ax1 = fig.add_subplot(1,1,1)
    try:
        LIMIT = current_run.limit
    except:
        LIMIT = 1.5e-3
    try:
        with open(current_run.db_file_name,'r') as gd:
            graph_data = gd.read()
    except IOError:
        with open(database_file,'r') as gd:
            graph_data = gd.read()
    lines = graph_data.split('\n')
    y, x = lines[0].split(',')
    xs = []
    ys = []
    zs = []
    time_since_beginning = len(lines)/4.0
    for line in lines:
        if len(line) > 1:
            try:
                y, x = line.split(',')
                ys.append(float(y))
                # working on this part
                xs.append((lines.index(line)/4.0)/86400.0)
                print float(y), float(time_since_beginning)
            except:
                pass
            zs.append(LIMIT)
    ax1.clear()
    # ax1.set_xlim(xmin=0)
    ax1.plot(xs,ys)
    # ax1.plot(zs)
    ax1.set_xlabel("{0} seconds since the start of the run".format(str(time_since_beginning)))
    ax1.set_ylabel("Voltage (volts)")
    plt.show(block = False)


def change_threshold():
    '''change the limit attribute of the current run'''
    global current_run
    element_input(main, "Please input the new voltage threshold.")
    current_run.limit = valve
    print current_run.limit


def format_x(x_val):
    '''make the date graphable, instead of human readable'''
    global start_time
    x_s = x_val[1:-2]
    x_s = x_s.split(' ')
    for element in x_s:
        x_s[x_s.index(element)] = int(float(element))
    return float(datetime.datetime(x_s[0],x_s[1],x_s[2],x_s[3],x_s[4]).strftime('%s')) - start_time


def change_check():
    global check_limit
    if check_limit == 1:
        check_limit = 0
        tkmb.showinfo("Alert", "Monitoring is now OFF. You will not receive any emails.")
    elif check_limit == 0:
        check_limit = 1
        tkmb.showinfo("Alert", "Monitoring is now ON. You will receive email alerts as necessary.")
    else:
        print 'Something is REALLY wrong. Quitting.'
        sys.exit()

def view_email_list():
    tkmb.showinfo("Emails are being sent to these emails", emails)


def check_args():
    '''check the function arguments provided when the software was run'''
    global LIMIT, current_run, emails
    args = parser.parse_args()
    if len(sys.argv) > 4:
        LIMIT = args.threshold
        current_run = newRun(get_current_date())
        current_run.change_run_number(args.rnum)
        current_run.limit = LIMIT
        current_run.generate_new_file()
        tmp = args.emails
        emails = tmp.split(',')
        get_current_run_info()
    else:
        print 'NOT ENOUGH ARGS GIVEN. EMAILS, USER, PASS REQUIRED. EXITING.'
        sys.exit()


# GUI button and entry definitions, add to here if you want to implement functions as buttons
# database dataset live view entry controls
voltage_db_view = Text(main, bg = "white", fg = "black", insertbackground = "white",tabs = ("1c"))
voltage_db_view.grid(row = 0, column = 1, rowspan=8)

# button to generate new runs, creates a newRun object
new_run_button = Button(main, text="Start New Run", command=new_run_function)
new_run_button.grid(row=0,column=0)

# button to generate empty dataset, function is within newRun object
generate_empty_database_file = Button(main, text="Generate new database", command=generate_new_empty_database)
generate_empty_database_file.grid(row=1, column=0)

# button to display all current run information
get_current_run_info_button = Button(main, text="Get current run info", command=get_current_run_info)
get_current_run_info_button.grid(row=2, column=0)

# button to change the threshold
ch_thresh_button = Button(main, text="Change threshold", command=change_threshold)
ch_thresh_button.grid(row=3, column=0)

# button to initalize realtime database view (graph)
graph_button_real_time = Button(main, text="Graph voltage, real time", command=graph_data_real_time)
graph_button_real_time.grid(row=4, column=0)

# button to initialize static, full database view (graph)
graph_button_total = Button(main, text="Graph all data", command=graph_data_total_set)
graph_button_total.grid(row=5, column=0)

# toggles sending of alerts to everyone on the email list
monitoring_button = Button(main, text="START/STOP MONITORING", command=change_check)
monitoring_button.grid(row=6, column=0, rowspan=1)

# see who's on the email list
elist_button = Button(main, text="Who are emails being sent to?", command=view_email_list)
elist_button.grid(row=7, column=0)


# check for the arguments before anything gets going
main.after(100, check_args)
# constantly update the voltage database entry window and check for above threshold values
main.after(2500,update_voltage_db)
main.wm_title('ANUBIS: real time low-voltage monitoring system')
main.mainloop()