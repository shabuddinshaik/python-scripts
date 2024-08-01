import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import threading
import time
import re
import subprocess
from twilio.rest import Client
import win32com.client

# Logging setup
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables
twilio_accounts = {}
monitoring_jobs = {}
alerts = []
silence_periods = {}

# Load configuration from file
def load_data():
    global twilio_accounts, monitoring_jobs, alerts, silence_periods
    try:
        with open('config.json', 'r') as f:
            data = json.load(f)
            twilio_accounts = data.get('twilio_accounts', {})
            monitoring_jobs = data.get('monitoring_jobs', {})
            alerts = data.get('alerts', [])
            silence_periods = data.get('silence_periods', [])
        logging.info("Configuration loaded successfully.")
    except FileNotFoundError:
        logging.warning("Configuration file not found. Starting with empty configuration.")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from configuration file: {e}")

# Save configuration to file
def save_data():
    global twilio_accounts, monitoring_jobs, alerts, silence_periods
    data = {
        'twilio_accounts': twilio_accounts,
        'monitoring_jobs': monitoring_jobs,
        'alerts': alerts,
        'silence_periods': silence_periods
    }
    try:
        with open('config.json', 'w') as f:
            json.dump(data, f, indent=4)
        logging.info("Configuration saved successfully.")
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")

# Add a Twilio account
def add_twilio_account():
    account_name = account_name_entry.get()
    account_sid = account_sid_entry.get()
    auth_token = auth_token_entry.get()
    twilio_number = twilio_number_entry.get()
    recipient_numbers = recipient_numbers_entry.get().split(',')
    selected_methods = [method for method, var in method_vars.items() if var.get()]

    if not (account_name and account_sid and auth_token and twilio_number):
        messagebox.showerror("Error", "All fields are required.")
        return

    twilio_accounts[account_name] = {
        'account_sid': account_sid,
        'auth_token': auth_token,
        'twilio_number': twilio_number,
        'recipient_numbers': recipient_numbers,
        'methods': selected_methods
    }

    save_data()
    update_twilio_account_options()
    logging.info(f"Added Twilio account: {account_name}")
    messagebox.showinfo("Success", "Twilio account added.")

def update_twilio_account_options():
    alert_twilio_account_option_menu['values'] = list(twilio_accounts.keys())

# Add a monitoring job
def add_monitoring_job():
    job_name = job_name_entry.get()
    url_type = url_type_var.get()
    url = url_entry.get()
    regex = regex_entry.get()
    proxy = proxy_entry.get()

    if not (job_name and url):
        messagebox.showerror("Error", "Job Name and URL are required.")
        return

    monitoring_jobs[job_name] = {
        'url': url,
        'url_type': url_type,
        'regex': regex,
        'proxy': proxy
    }

    save_data()
    update_monitoring_job_options()
    logging.info(f"Added monitoring job: {job_name}")
    messagebox.showinfo("Success", "Monitoring job added.")

def update_monitoring_job_options():
    alert_url_option_menu['values'] = list(monitoring_jobs.keys())

# Add an alert
def add_alert():
    alert_name = alert_name_entry.get()
    job_name = alert_url_var.get()
    twilio_account = alert_twilio_account_var.get()
    scrape_interval = int(alert_interval_entry.get()) * 60
    response_codes = alert_response_codes_entry.get().split(',')

    if not (alert_name and job_name and twilio_account):
        messagebox.showerror("Error", "Alert Name, Job Name, and Twilio Account are required.")
        return

    alerts.append({
        'alert_name': alert_name,
        'job_name': job_name,
        'twilio_account': twilio_account,
        'scrape_interval': scrape_interval,
        'response_codes': response_codes,
        'monitoring': False
    })

    save_data()
    update_alert_list()
    logging.info(f"Added alert: {alert_name}")
    messagebox.showinfo("Success", "Alert added.")

def update_alert_list():
    for widget in alert_list_frame.winfo_children():
        widget.destroy()
    for alert in alerts:
        alert_frame = tk.Frame(alert_list_frame)
        alert_frame.pack(fill='x', pady=2)

        tk.Label(alert_frame, text=alert['alert_name']).pack(side='left', padx=10)
        tk.Button(alert_frame, text="Start", command=lambda a=alert['alert_name']: start_monitoring(a)).pack(side='left', padx=5)
        tk.Button(alert_frame, text="Pause", command=lambda a=alert['alert_name']: pause_monitoring(a)).pack(side='left', padx=5)
        tk.Button(alert_frame, text="Stop", command=lambda a=alert['alert_name']: stop_monitoring(a)).pack(side='left', padx=5)

def start_monitoring(alert_name):
    for alert in alerts:
        if alert['alert_name'] == alert_name:
            alert['monitoring'] = True
            logging.info(f"Started monitoring for alert: {alert_name}")
            # Implement logic to start monitoring (e.g., pinging)
            threading.Thread(target=monitor_alert, args=(alert,)).start()
            break

def pause_monitoring(alert_name):
    for alert in alerts:
        if alert['alert_name'] == alert_name:
            alert['monitoring'] = False
            logging.info(f"Paused monitoring for alert: {alert_name}")
            break

def stop_monitoring(alert_name):
    for alert in alerts:
        if alert['alert_name'] == alert_name:
            alert['monitoring'] = False
            logging.info(f"Stopped monitoring for alert: {alert_name}")
            # Stop the monitoring thread if running
            break

def monitor_alert(alert):
    url = monitoring_jobs[alert['job_name']]['url']
    scrape_interval = alert['scrape_interval']
    
    while alert['monitoring']:
        try:
            response = subprocess.check_output(['ping', '-n', '1', url], stderr=subprocess.STDOUT)
            logging.info(f"Monitoring {alert['alert_name']}: {response.decode().strip()}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Monitoring {alert['alert_name']} failed: {e.output.decode().strip()}")

        time.sleep(scrape_interval)

# Set silence period
def set_silence_period():
    start = silence_start_entry.get()
    end = silence_end_entry.get()
    reason = silence_reason_entry.get()

    try:
        silence_periods.append({
            'start': start,
            'end': end,
            'reason': reason
        })
        save_data()
        logging.info(f"Silence period set from {start} to {end}. Reason: {reason}")
        messagebox.showinfo("Success", "Silence period set.")
    except Exception as e:
        logging.error(f"Error setting silence period: {e}")
        messagebox.showerror("Error", "Failed to set silence period.")

# Check email labels
def check_email_labels():
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox = outlook.Folders("Your Outlook Account").Folders("Inbox")

    for alert in alerts:
        if alert['alert_type'] == 'email':
            for label in alert.get('response_codes', []):
                messages = inbox.Items
                for msg in messages:
                    if label in msg.Subject or label in msg.Body:
                        start_monitoring(alert['alert_name'])
                        break

# UI setup
root = tk.Tk()
root.title("URL Monitor")

tab_control = ttk.Notebook(root)
accounts_tab = ttk.Frame(tab_control)
monitoring_tab = ttk.Frame(tab_control)
alerts_tab = ttk.Frame(tab_control)
silence_tab = ttk.Frame(tab_control)

tab_control.add(accounts_tab, text="Accounts")
tab_control.add(monitoring_tab, text="Monitoring")
tab_control.add(alerts_tab, text="Alerts")
tab_control.add(silence_tab, text="Silence")

tab_control.pack(expand=1, fill='both')

# Accounts Tab
tk.Label(accounts_tab, text="Account Name:").grid(row=0, column=0, padx=10, pady=10)
account_name_entry = tk.Entry(accounts_tab)
account_name_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(accounts_tab, text="Account SID:").grid(row=1, column=0, padx=10, pady=10)
account_sid_entry = tk.Entry(accounts_tab)
account_sid_entry.grid(row=1, column=1, padx=10, pady=10)

tk.Label(accounts_tab, text="Auth Token:").grid(row=2, column=0, padx=10, pady=10)
auth_token_entry = tk.Entry(accounts_tab)
auth_token_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Label(accounts_tab, text="Twilio Number:").grid(row=3, column=0, padx=10, pady=10)
twilio_number_entry = tk.Entry(accounts_tab)
twilio_number_entry.grid(row=3, column=1, padx=10, pady=10)

tk.Label(accounts_tab, text="Recipient Numbers (comma-separated):").grid(row=4, column=0, padx=10, pady=10)
recipient_numbers_entry = tk.Entry(accounts_tab, width=50)
recipient_numbers_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Label(accounts_tab, text="Alert Methods:").grid(row=5, column=0, padx=10, pady=10)
method_vars = {'call': tk.BooleanVar(), 'sms': tk.BooleanVar(), 'email': tk.BooleanVar()}
tk.Checkbutton(accounts_tab, text='Call', variable=method_vars['call']).grid(row=5, column=1, sticky='w')
tk.Checkbutton(accounts_tab, text='SMS', variable=method_vars['sms']).grid(row=5, column=1)
tk.Checkbutton(accounts_tab, text='Email', variable=method_vars['email']).grid(row=5, column=1, sticky='e')

tk.Button(accounts_tab, text="Add Twilio Account", command=add_twilio_account).grid(row=6, column=0, columnspan=2, pady=20)

# Monitoring Tab
tk.Label(monitoring_tab, text="Job Name:").grid(row=0, column=0, padx=10, pady=10)
job_name_entry = tk.Entry(monitoring_tab)
job_name_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="URL Type:").grid(row=1, column=0, padx=10, pady=10)
url_type_var = tk.StringVar(value="http")
ttk.Combobox(monitoring_tab, textvariable=url_type_var, values=["http", "https"]).grid(row=1, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="URL:").grid(row=2, column=0, padx=10, pady=10)
url_entry = tk.Entry(monitoring_tab)
url_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="Regex (optional):").grid(row=3, column=0, padx=10, pady=10)
regex_entry = tk.Entry(monitoring_tab)
regex_entry.grid(row=3, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="Proxy (optional):").grid(row=4, column=0, padx=10, pady=10)
proxy_entry = tk.Entry(monitoring_tab)
proxy_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Button(monitoring_tab, text="Add Monitoring Job", command=add_monitoring_job).grid(row=5, column=0, columnspan=2, pady=20)

# Alerts Tab
tk.Label(alerts_tab, text="Alert Name:").grid(row=0, column=0, padx=10, pady=10)
alert_name_entry = tk.Entry(alerts_tab)
alert_name_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(alerts_tab, text="Monitoring Job:").grid(row=1, column=0, padx=10, pady=10)
alert_url_var = tk.StringVar()
alert_url_option_menu = ttk.Combobox(alerts_tab, textvariable=alert_url_var)
alert_url_option_menu.grid(row=1, column=1, padx=10, pady=10)

tk.Label(alerts_tab, text="Twilio Account:").grid(row=2, column=0, padx=10, pady=10)
alert_twilio_account_var = tk.StringVar()
alert_twilio_account_option_menu = ttk.Combobox(alerts_tab, textvariable=alert_twilio_account_var)
alert_twilio_account_option_menu.grid(row=2, column=1, padx=10, pady=10)

tk.Label(alerts_tab, text="Scrape Interval (minutes):").grid(row=3, column=0, padx=10, pady=10)
alert_interval_entry = tk.Entry(alerts_tab)
alert_interval_entry.grid(row=3, column=1, padx=10, pady=10)

tk.Label(alerts_tab, text="Response Codes (comma-separated):").grid(row=4, column=0, padx=10, pady=10)
alert_response_codes_entry = tk.Entry(alerts_tab)
alert_response_codes_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Button(alerts_tab, text="Add Alert", command=add_alert).grid(row=5, column=0, columnspan=2, pady=20)

alert_list_frame = tk.Frame(alerts_tab)
alert_list_frame.grid(row=6, column=0, columnspan=2, pady=10)

# Silence Tab
tk.Label(silence_tab, text="Start (HH:MM):").grid(row=0, column=0, padx=10, pady=10)
silence_start_entry = tk.Entry(silence_tab)
silence_start_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(silence_tab, text="End (HH:MM):").grid(row=1, column=0, padx=10, pady=10)
silence_end_entry = tk.Entry(silence_tab)
silence_end_entry.grid(row=1, column=1, padx=10, pady=10)

tk.Label(silence_tab, text="Reason:").grid(row=2, column=0, padx=10, pady=10)
silence_reason_entry = tk.Entry(silence_tab)
silence_reason_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Button(silence_tab, text="Set Silence Period", command=set_silence_period).grid(row=3, column=0, columnspan=2, pady=20)

# Load initial data
load_data()
update_twilio_account_options()
update_monitoring_job_options()
update_alert_list()

# Main loop
try:
    root.mainloop()
except Exception as e:
    logging.error(f"Unexpected error during application runtime: {e}")
    messagebox.showerror("Error", f"Unexpected error: {e}")
