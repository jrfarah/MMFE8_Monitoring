######################################################################################
# ANUBIS
# Program for monitoring low voltage power source in real time and over entire runs
# Created by Joseph Farah
#
# Written on: [Thursday, August 17th, 2017]
# Last updated: [Monday, September 4th, 2017] by [Joseph Farah]
# Requires several files to run:
#   * db_loc.txt: contains a single line pointing both ANUBIS and the Matlab script 
#                 to the correct database  
#   * speed_run.m: a minimized data collection script, needs to be running while the 
#                  run is going
#   * graphing/: contains the code needed to use ROOT to graph the entire dataset
#
# Function arguments: 
#   * \item--rnum: the current run number, defaults to "notrun" if none is provided
#   * \item--threshold: the maximum voltage allowed before the program proceeds to 
#                  piss itself
#   * \item--lower: the minimum voltage allowed before the program alerts
#   * \item--emails: the list of emails, separated by commas
#   * \item--user: the username for the alert system (must be gmail)
#   * \item--pass: the password for the alert system account
#   * \item--totref: time interal between the total dataset graph refreshes
#   * \item--nographs: NO ARGUMENT, doesn't display all graphs on startup
#   * \item--startnow: starts the matlab script automatically and displays graphs
#
# Example commands: 
#   (1) To begin run 3522 immediately, begin monitoring immediately, display 
#       graphs, give two emails, provide upper and lower thresholds, and wait 5 minutes in between each total graph 
#       refresh: 
# python anubis.py --rnum 3522 --threshold 1.0 --lower 0.2 --user lppcautomated --pass 42oxford --totref 300000 --startnow --emails email@email.ch,another@email.ch
#
#   (2) To run the program and do everything from the GUI:
# python anubis.py
#
# IMPORTANT: DO NOT RUN THE MATLAB SCRIPT IN ANY WAY BEFORE A DATABASE HAS BEEN GENERATED FOR THE RUN.  
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
from matplotlib.ticker import FormatStrFormatter
import datetime
import argparse
import thread
from threading import Timer

# the only module that probably isn't installed default, yagmail
try:
    import yagmail
except: 
    print 'WARNING: CANNOT IMPORT YAGMAIL, CANNOT NOTIFY OF THRESHOLD VIOLATIONS'
    sys.exit()

# for defaults, grab the most recently used database file
with open('db_loc.txt') as f:
    database_file = f.readline()
    if os.path.isfile(database_file):
        print 'Previous file found, creating backup'
        os.system('mv {0} {0}.bak'.format(database_file))

# a valve variable is used for temporary value storage while 
# applying a new value to a previously created class
valve = ""    

# lets the program know if its on the first iteration or not
# could be useful in the future for improved time reading
check_start = 1
start_time = 0
check_limit = 1
show_upper_bound = 0
show_lower_bound = 0
show_all_graphs = 1
start_immediately = 1

# default limit, can be changed either with command line
# args or by using the GUI
LIMIT = 1.5e-4
total_refresh = int(3e5)

# email list, needs to be global
emails = []
uname = ""
passwd = ""

# path to matlab exe (CHANGE THIS DEPENDING ON WHERE YOU INSTALLED MATLAB)
# ideally should remain constant throughout the run
MATLAB_PATH = "/mnt/c/Program\ Files/MATLAB/R2017a/bin/matlab.exe"
matlab_command = MATLAB_PATH + " -nodisplay -nosplash -nodesktop -r speed_run"

# command line argument stuff
parser = argparse.ArgumentParser(usage=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--rnum", default="notrun", help="run number")
parser.add_argument("--threshold", help="threshold value")
parser.add_argument("--lower", help="lower threshold limit")
parser.add_argument("--emails", default="", help="list of emails, separated by commas. example: email@cern.ch,email.cern.ch")
parser.add_argument("--user", default="", help="username for alert system")
parser.add_argument("--pass", default="",help="password for alert system")
parser.add_argument("--totref", default=total_refresh, help="how often the realtime graph of the total dataset refreshes")
parser.add_argument("--nographs", action='store_true')
parser.add_argument("--startnow", action='store_true')
parser.add_argument("--matlabpath", default = MATLAB_PATH, help="path to the matlab executable")

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
        self.lower_threshold = limit/2
        self.alerts_list = []

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

    def add_alert(self, line_num):
        self.alerts_list.append(line_num)

# defining the tkinter window
main = Tk()

current_run = newRun(1)

def get_current_date():
    '''gets the current date and returns it in a human readable format'''
    return time.strftime("%d-%m-%Y")

def tail(f, n):
    '''grabs the last n lines from any file, formats it, and checks to see 
        if the voltage is more than the specified threshold'''
    try:
        result = subprocess.check_output("tail -n "+n+" "+f, shell=True)
        lines = result.splitlines()
        try:
            limit = current_run.limit
        except:
            limit = LIMIT

        if check_limit == 1:
            for line in lines:
                try:
                    y, x = line.split(',')
                except ValueError:
                    continue
                if float(y) > float(limit) or float(y) < float(current_run.lower_threshold):
                    with open(current_run.db_file_name, "r") as f:
                        data = f.readlines()
                    try:
                        index = data.index(line+"\n")
                    except ValueError:
                        continue

                    if data.index(line+"\n") in current_run.alerts_list:
                        # print 'I found a value that exceeds a threshold, but I already notified you about it.'
                        continue
                    else:
                        # send_alert(time.strftime("%d/%m/%Y"),time.strftime("%I:%M:%S"), y,limit, emails, uname, passwd)
                        current_run.add_alert(data.index(str(line+"\n")))
                        # print current_run.alerts_list
                        # print "VOLTAGE ABOUT THRESHOLD FOUND! Sending email now."

        return result
    except:
        return "PROBLEM LOADING DATABASE, CARRY ON"

def send_alert(date, time, voltage, threshold, email_list, username, password):
    '''email-sending protocol, simplified using yagmail'''
    yag = yagmail.SMTP(username, password)
    message = 'ALERT: ANUBIS recorded a voltage on {0} at {1} on [whatever circuit] that was not within the set thresholds of {2} V and {4} V. The recorded voltage was {3} V'.format(str(date), str(time), str(threshold), str(voltage), str(current_run.lower_threshold))
    contents = [message]
    yag.send(email_list, 'Test alert', contents)

def update_voltage_db():
    '''update the voltage database view. helpful for checking to see if the 
       matlab program is actually receiving any data'''
    global voltage_db_view
    voltage_db_view.delete('1.0', END)
    # try:
    voltage_db_view.insert(INSERT, tail(database_file,'100'))
    # except:
    #     print 'problem with tailing file'
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
    print current_run.limit
    print current_run.lower_threshold
    print total_refresh
    tkmb.showinfo("Current object info", "{0}\n{1}\n{2}\n".format(current_run.date, current_run.run_number, current_run.db_file_name))

def generate_new_empty_database():
    '''writes a new empty database file with the function built into the Run object'''
    current_run.generate_new_file()
    tkmb.showinfo("Success", "Database successfully generated, filename {0}".format(current_run.db_file_name))

def graph_data_real_time():
    '''call the animation that allows the graph to display real time data'''
    fig = plt.figure()
    ax1 = fig.add_subplot(1,1,1)
    ax1.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ani = animation.FuncAnimation(fig, animate, interval=125, fargs=(ax1,))
    plt.show(block=True)

def animate(i, ax1):
    '''the animation function'''
    global current_run, check_start, start_time
    # change this value to change the number of data points shown in the 
    # real time graph window
    MAX_LENGTH = 50
    try:
        LIMIT = current_run.limit
        l_bound = current_run.lower_threshold
    except:
        LIMIT = 1.5e-3
        l_bound = LIMIT/2
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
    ls = []
    time_since_beginning = len(lines)/4
    for line in lines:
        # if line == lines[-1]:
        #     break
        if len(line) > 1:
            try:
                y, x = line.split(',')
                ys.append(float(y))
                xs.append(format_x(x))
            except:
                pass
            zs.append(LIMIT)
            ls.append(l_bound)
    if len(ys) > MAX_LENGTH:
        ys = ys[len(ys)-MAX_LENGTH:]
        xs = xs[len(ys)-MAX_LENGTH:]
        zs = zs[len(zs)-MAX_LENGTH:]
        ls = ls[len(ls)-MAX_LENGTH:]
    ax1.clear()
    ax1.plot(ys)
    if show_upper_bound == 1:
        ax1.plot(zs)
    if show_lower_bound == 1:
        ax1.plot(ls)
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

def graph_total_dataset_real_time():
    try:
        response = subprocess.check_output("./graphing/graph_total ../{0}".format(current_run.db_file_name), shell=True)
        if response: print response
    except:
        print "real_time graphing didn't work"
    print 'Working (sort of)'
    main.after(total_refresh, graph_total_dataset_real_time)


def change_threshold():
    '''change the limit attribute of the current run'''
    global current_run
    element_input(main, "Please input the new UPPER voltage threshold.")
    current_run.limit = valve
    print current_run.limit
    element_input(main, "Please input the new LOWER voltage threshold.")
    current_run.lower_threshold = valve
    print current_run.lower_threshold


def format_x(x_val):
    '''make the date graphable, instead of human readable'''
    global start_time
    x_s = x_val[1:-1]
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

def ping():
    element_input(main, "Please input the number of pings.")
    num_ping = valve
    element_input(main, "Please input the IP you want to ping.")
    ip_ping = valve
    response = subprocess.check_output("ping -c {0} {1}".format(num_ping, ip_ping), shell=True)
    tkmb.showinfo("Result", response)

def run_matlab_script():
    # uncomment this for debugging purposes
    subprocess.check_output("nohup python fake_data_generator.py &", shell=True)
    # subprocess.check_output(matlab_command, shell=True)

def check_args():
    '''check the function arguments provided when the software was run'''
    global LIMIT, current_run, emails, show_lower_bound, show_upper_bound, total_refresh, show_all_graphs, MATLAB_PATH
    args = parser.parse_args()
    if len(sys.argv) > 4:
        LIMIT = args.threshold
        current_run = newRun(get_current_date())
        current_run.change_run_number(args.rnum)
        if args.threshold is not None:
            current_run.limit = LIMIT
            show_upper_bound = 1
        if args.lower is not None:
            current_run.lower_threshold = args.lower
            show_lower_bound = 1
        if args.totref is not None:
            total_refresh = args.totref
        if args.nographs is True:
            show_all_graphs = 0
        current_run.generate_new_file()
        if args.emails is not None:
            tmp = args.emails
            emails = tmp.split(',')
        else:
            emails = ['dummy@email.garbage']
        MATLAB_PATH = args.matlabpath
        if args.startnow is True:
            thread.start_new_thread(run_matlab_script, ())
            if show_all_graphs == 1:
                main.after(5000,graph_data_real_time)


# GUI button and entry definitions, add to here if you want to implement functions as buttons
# database dataset live view entry controls
voltage_db_view = Text(main, bg = "white", fg = "black", insertbackground = "white",tabs = ("1c"))
voltage_db_view.grid(row = 0, column = 1, rowspan=10)

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

# ping within the software
ping_button = Button(main, text="Ping IP", command=ping)
ping_button.grid(row=7, column=0)

# see who's on the email list
elist_button = Button(main, text="Who are emails being sent to?", command=view_email_list)
elist_button.grid(row=8, column=0)

# button to start the MATLAB script
script_run_button = Button(main, text="Start matlab script", command=lambda:thread.start_new_thread(run_matlab_script, ()))
script_run_button.grid(row=9,column=0)



# check for the arguments before anything gets going
main.after(100, check_args)
# constantly update the voltage database entry window and check for above threshold values
main.after(2500,update_voltage_db)
main.after(total_refresh, graph_total_dataset_real_time)
main.wm_title('ANUBIS: real time low-voltage monitoring system')
main.mainloop()
print 'Exiting'