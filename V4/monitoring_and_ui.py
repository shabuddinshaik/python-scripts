import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import threading
import time
import requests
from twilio.rest import Client

# Logging setup
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables
twilio_accounts = {}
monitoring_jobs = {}
alerts = []
silence_periods = []

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
    menu = alert_twilio_account_option_menu['menu']
    menu.delete(0, 'end')
    accounts = list(twilio_accounts.keys())
    for account in accounts:
        menu.add_command(label=account, command=tk._setit(alert_twilio_account_var, account))

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
    menu = alert_url_option_menu['menu']
    menu.delete(0, 'end')
    jobs = list(monitoring_jobs.keys())
    for job in jobs:
        menu.add_command(label=job, command=tk._setit(alert_url_var, job))

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

    alert = {
        'alert_name': alert_name,
        'job_name': job_name,
        'twilio_account': twilio_account,
        'scrape_interval': scrape_interval,
        'response_codes': response_codes,
        'monitoring': True
    }
    alerts.append(alert)
    threading.Thread(target=monitor_alert, args=(alert,)).start()

    save_data()
    update_alert_list()
    logging.info(f"Added alert and started monitoring: {alert_name}")
    messagebox.showinfo("Success", "Alert added and monitoring started.")

def update_alert_list():
    for widget in alert_frame.winfo_children():
        widget.destroy()
    for alert in alerts:
        alert_frame_inner = tk.Frame(alert_frame)
        alert_frame_inner.pack(fill='x', pady=2)

        tk.Label(alert_frame_inner, text=alert['alert_name']).pack(side='left', padx=10)
        tk.Button(alert_frame_inner, text="Start", command=lambda a=alert['alert_name']: start_monitoring(a)).pack(side='left', padx=5)
        tk.Button(alert_frame_inner, text="Pause", command=lambda a=alert['alert_name']: pause_monitoring(a)).pack(side='left', padx=5)
        tk.Button(alert_frame_inner, text="Stop", command=lambda a=alert['alert_name']: stop_monitoring(a)).pack(side='left', padx=5)

# Function to monitor alerts
def monitor_alert(alert):
    url = monitoring_jobs[alert['job_name']]['url']
    scrape_interval = alert['scrape_interval']
    account_info = twilio_accounts[alert['twilio_account']]
    client = Client(account_info['account_sid'], account_info['auth_token'])

    while alert['monitoring']:
        try:
            response = requests.get(url, proxies={"http": monitoring_jobs[alert['job_name']].get('proxy', ''),
                                                 "https": monitoring_jobs[alert['job_name']].get('proxy', '')})
            if response.status_code not in [int(code) for code in alert['response_codes']]:
                raise requests.HTTPError(f"Unexpected response code: {response.status_code}")
            logging.info(f"Monitoring {alert['alert_name']}: URL {url} is reachable.")
        except Exception as e:
            logging.error(f"Monitoring {alert['alert_name']} failed: {e}")
            send_alert(alert, client, account_info)

        time.sleep(scrape_interval)

def send_alert(alert, client, account_info):
    message = "Alert: URL is not reachable!"
    for method in account_info['methods']:
        for number in account_info['recipient_numbers']:
            try:
                if method == 'call':
                    client.calls.create(
                        to=number,
                        from_=account_info['twilio_number'],
                        url='http://demo.twilio.com/docs/voice.xml'
                    )
                elif method == 'sms':
                    client.messages.create(
                        to=number,
                        from_=account_info['twilio_number'],
                        body=message
                    )
                elif method == 'email':
                    # Assuming you have a function to send emails
                    send_email(number, message)
            except Exception as e:
                logging.error(f"Failed to send {method} alert to {number}: {e}")

def send_email(to_address, message):
    # Implement your email sending logic here
    pass

def start_monitoring(alert_name):
    for alert in alerts:
        if alert['alert_name'] == alert_name:
            alert['monitoring'] = True
            logging.info(f"Started monitoring for alert: {alert_name}")
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
            break

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

# GUI setup
root = tk.Tk()
root.title("Monitoring Dashboard")

# Notebook (Tabs) setup
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# Twilio Configuration Tab
twilio_tab = ttk.Frame(notebook)
notebook.add(twilio_tab, text="Twilio Configuration")

tk.Label(twilio_tab, text="Account Name").grid(row=0, column=0, padx=5, pady=5)
account_name_entry = tk.Entry(twilio_tab)
account_name_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(twilio_tab, text="Account SID").grid(row=1, column=0, padx=5, pady=5)
account_sid_entry = tk.Entry(twilio_tab)
account_sid_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(twilio_tab, text="Auth Token").grid(row=2, column=0, padx=5, pady=5)
auth_token_entry = tk.Entry(twilio_tab, show="*")
auth_token_entry.grid(row=2, column=1, padx=5, pady=5)

tk.Label(twilio_tab, text="Twilio Number").grid(row=3, column=0, padx=5, pady=5)
twilio_number_entry = tk.Entry(twilio_tab)
twilio_number_entry.grid(row=3, column=1, padx=5, pady=5)

tk.Label(twilio_tab, text="Recipient Numbers (comma-separated)").grid(row=4, column=0, padx=5, pady=5)
recipient_numbers_entry = tk.Entry(twilio_tab)
recipient_numbers_entry.grid(row=4, column=1, padx=5, pady=5)

tk.Label(twilio_tab, text="Methods").grid(row=5, column=0, padx=5, pady=5)
method_vars = {
    'Call': tk.BooleanVar(),
    'SMS': tk.BooleanVar(),
    'Email': tk.BooleanVar()
}
for i, (method, var) in enumerate(method_vars.items()):
    tk.Checkbutton(twilio_tab, text=method, variable=var).grid(row=5, column=1+i, padx=5, pady=5)

tk.Button(twilio_tab, text="Add Twilio Account", command=add_twilio_account).grid(row=6, column=0, columnspan=2, pady=10)

# Monitoring Jobs Tab
monitoring_tab = ttk.Frame(notebook)
notebook.add(monitoring_tab, text="Monitoring Jobs")

tk.Label(monitoring_tab, text="Job Name").grid(row=0, column=0, padx=5, pady=5)
job_name_entry = tk.Entry(monitoring_tab)
job_name_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(monitoring_tab, text="URL").grid(row=1, column=0, padx=5, pady=5)
url_entry = tk.Entry(monitoring_tab)
url_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(monitoring_tab, text="URL Type").grid(row=2, column=0, padx=5, pady=5)
url_type_var = tk.StringVar(value="text")
tk.Radiobutton(monitoring_tab, text="Text", variable=url_type_var, value="text").grid(row=2, column=1, padx=5, pady=5)
tk.Radiobutton(monitoring_tab, text="JSON", variable=url_type_var, value="json").grid(row=2, column=2, padx=5, pady=5)

tk.Label(monitoring_tab, text="Regex (optional)").grid(row=3, column=0, padx=5, pady=5)
regex_entry = tk.Entry(monitoring_tab)
regex_entry.grid(row=3, column=1, padx=5, pady=5)

tk.Label(monitoring_tab, text="Proxy (optional)").grid(row=4, column=0, padx=5, pady=5)
proxy_entry = tk.Entry(monitoring_tab)
proxy_entry.grid(row=4, column=1, padx=5, pady=5)

tk.Button(monitoring_tab, text="Add Monitoring Job", command=add_monitoring_job).grid(row=5, column=0, columnspan=2, pady=10)

# Alerts Tab
alerts_tab = ttk.Frame(notebook)
notebook.add(alerts_tab, text="Alerts")

alert_frame = tk.Frame(alerts_tab)
alert_frame.pack(fill='both', expand=True)

tk.Label(alerts_tab, text="Alert Name").pack(pady=5)
alert_name_entry = tk.Entry(alerts_tab)
alert_name_entry.pack(pady=5)

tk.Label(alerts_tab, text="Select URL").pack(pady=5)
alert_url_var = tk.StringVar(value="Select URL")
alert_url_option_menu = tk.OptionMenu(alerts_tab, alert_url_var, *[])
alert_url_option_menu.pack(pady=5)

tk.Label(alerts_tab, text="Select Twilio Account").pack(pady=5)
alert_twilio_account_var = tk.StringVar(value="Select Account")
alert_twilio_account_option_menu = tk.OptionMenu(alerts_tab, alert_twilio_account_var, *[])
alert_twilio_account_option_menu.pack(pady=5)

tk.Label(alerts_tab, text="Scrape Interval (minutes)").pack(pady=5)
alert_interval_entry = tk.Entry(alerts_tab)
alert_interval_entry.pack(pady=5)

tk.Label(alerts_tab, text="Response Codes (comma-separated)").pack(pady=5)
alert_response_codes_entry = tk.Entry(alerts_tab)
alert_response_codes_entry.pack(pady=5)

tk.Button(alerts_tab, text="Add Alert", command=add_alert).pack(pady=10)

# Silence Period Tab
silence_tab = ttk.Frame(notebook)
notebook.add(silence_tab, text="Silence Period")

tk.Label(silence_tab, text="Start Time").grid(row=0, column=0, padx=5, pady=5)
silence_start_entry = tk.Entry(silence_tab)
silence_start_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(silence_tab, text="End Time").grid(row=1, column=0, padx=5, pady=5)
silence_end_entry = tk.Entry(silence_tab)
silence_end_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(silence_tab, text="Reason").grid(row=2, column=0, padx=5, pady=5)
silence_reason_entry = tk.Entry(silence_tab)
silence_reason_entry.grid(row=2, column=1, padx=5, pady=5)

tk.Button(silence_tab, text="Set Silence Period", command=set_silence_period).grid(row=3, column=0, columnspan=2, pady=10)

# Initial Data Load
load_data()
update_twilio_account_options()
update_monitoring_job_options()

root.mainloop()
