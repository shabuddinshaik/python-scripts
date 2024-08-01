import os
import time
import logging
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
import json
import re
from twilio.rest import Client
from threading import Thread
import win32com.client

# Define logger
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            'name': record.name,
            'filename': record.pathname,
            'lineno': record.lineno
        }
        return json.dumps(log_record)

logger = logging.getLogger('url-monitor')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('url-monitor.log', when='midnight', interval=1)
handler.suffix = "%Y%m%d"
handler.setLevel(logging.DEBUG)
formatter = JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

# Global variables for Twilio and monitoring
twilio_accounts = {}
monitoring_jobs = {}
alerts = []
monitoring_active = True
silence_period = None
evaluation_interval = 300  # Default to 5 minutes
proxy_settings = {}
regex_patterns = {}

# Helper functions
def load_data():
    global twilio_accounts, monitoring_jobs, alerts, proxy_settings, regex_patterns
    try:
        with open('monitor_config.json', 'r') as f:
            config = json.load(f)
            twilio_accounts = config.get('twilio_accounts', {})
            monitoring_jobs = config.get('monitoring_jobs', {})
            alerts = config.get('alerts', [])
            proxy_settings = config.get('proxy_settings', {})
            regex_patterns = config.get('regex_patterns', {})
    except FileNotFoundError:
        pass

def save_data():
    config = {
        'twilio_accounts': twilio_accounts,
        'monitoring_jobs': monitoring_jobs,
        'alerts': alerts,
        'proxy_settings': proxy_settings,
        'regex_patterns': regex_patterns
    }
    with open('monitor_config.json', 'w') as f:
        json.dump(config, f)

def send_alert(alert_type, url, message, account_name):
    try:
        account = twilio_accounts.get(account_name)
        if not account:
            raise ValueError("Twilio account not found")
        
        client = Client(account['account_sid'], account['auth_token'])
        for number in account['recipient_numbers']:
            if alert_type == 'call':
                call = client.calls.create(
                    to=number,
                    from_=account['twilio_number'],
                    url='http://demo.twilio.com/docs/voice.xml'
                )
                logger.info(f"Call alert sent to {number} for URL: {url}")
            elif alert_type == 'sms':
                client.messages.create(
                    body=message,
                    from_=account['twilio_number'],
                    to=number
                )
                logger.info(f"SMS alert sent to {number} for URL: {url}")
            elif alert_type == 'email':
                # Implement email sending logic here
                logger.info(f"Email alert sent to {number} for URL: {url}")
    except Exception as e:
        logger.error(f"Failed to send {alert_type} alert: {e}")

def check_url(url, regex=None):
    try:
        response = subprocess.run(['curl', '-I', url], capture_output=True, text=True)
        status_code = response.stdout.split()[1]
        if response.returncode == 0:
            logger.info(f"URL {url} is reachable with status code {status_code}.")
            if regex:
                page_content = subprocess.run(['curl', url], capture_output=True, text=True).stdout
                if re.search(regex, page_content):
                    logger.info(f"Regex {regex} matched for URL {url}.")
                    return status_code, True
                else:
                    logger.error(f"Regex {regex} did not match for URL {url}.")
                    return status_code, False
            return status_code, True
        else:
            logger.error(f"URL {url} is not reachable with status code {status_code}.")
            return status_code, False
    except Exception as e:
        logger.error(f"Failed to check URL {url}: {e}")
        return None, False

def check_intranet_url(url):
    try:
        response = subprocess.run(
            ['ping', '-n', '1', url],
            capture_output=True,
            text=True,
            env={**os.environ, 'http_proxy': proxy_settings.get('http_proxy', ''), 'https_proxy': proxy_settings.get('https_proxy', '')}
        )
        if response.returncode == 0:
            logger.info(f"Intranet URL {url} is reachable.")
            return True
        else:
            logger.error(f"Intranet URL {url} is not reachable.")
            return False
    except Exception as e:
        logger.error(f"Failed to check intranet URL {url}: {e}")
        return False

def monitor_urls():
    while monitoring_active:
        for alert in alerts:
            current_time = datetime.utcnow()
            if silence_period and silence_period[0] <= current_time <= silence_period[1]:
                continue

            job = monitoring_jobs.get(alert['job_name'])
            if not job:
                continue
            
            url = job['url']
            regex = job.get('regex')
            status_code, status = check_url(url, regex) if job['url_type'] == 'internet' else (None, check_intranet_url(url))
            if status:
                for code in alert['response_codes']:
                    if str(status_code) == code:
                        break
                else:
                    send_alert(alert['alert_type'], url, f"URL {url} is down.", alert['twilio_account'])
            else:
                send_alert(alert['alert_type'], url, f"URL {url} is down.", alert['twilio_account'])

        time.sleep(evaluation_interval)

def start_monitoring():
    global monitoring_thread
    monitoring_thread = Thread(target=monitor_urls)
    monitoring_thread.daemon = True
    monitoring_thread.start()
    logger.info("Started monitoring URLs.")

def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    messagebox.showinfo("Stopped", "Monitoring stopped.")
    logger.info("Stopped monitoring URLs.")

def set_silence_period():
    start_time_str = silence_start_entry.get()
    end_time_str = silence_end_entry.get()
    reason = silence_reason_entry.get()
    try:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        if start_time < end_time:
            global silence_period
            silence_period = (start_time, end_time, reason)
            messagebox.showinfo("Success", "Silence period set.")
        else:
            messagebox.showerror("Error", "End time must be after start time.")
    except ValueError:
        messagebox.showerror("Error", "Invalid date/time format. Use YYYY-MM-DD HH:MM:SS.")

def add_twilio_account():
    account_name = account_name_entry.get()
    account_sid = account_sid_entry.get()
    auth_token = auth_token_entry.get()
    twilio_number = twilio_number_entry.get()
    recipient_numbers = recipient_numbers_entry.get().split(',')

    if len(twilio_accounts) >= 150:
        messagebox.showerror("Error", "Maximum number of accounts reached (150).")
        return

    if account_name in twilio_accounts:
        messagebox.showerror("Error", "Account name already exists.")
        return

    twilio_accounts[account_name] = {
        'account_sid': account_sid,
        'auth_token': auth_token,
        'twilio_number': twilio_number,
        'recipient_numbers': recipient_numbers
    }

    save_data()
    messagebox.showinfo("Success", "Twilio account added.")

def add_monitoring_job():
    job_name = job_name_entry.get()
    url_type = url_type_var.get()
    url = url_entry.get()
    regex = regex_entry.get()
    proxy = proxy_entry.get()

    if job_name in monitoring_jobs:
        messagebox.showerror("Error", "Job name already exists.")
        return

    monitoring_jobs[job_name] = {
        'url_type': url_type,
        'url': url,
        'regex': regex,
        'proxy': proxy
    }

    proxy_settings[url] = proxy

    save_data()
    update_alert_url_options()
    messagebox.showinfo("Success", "Monitoring job added.")

def add_alert():
    alert_name = alert_name_entry.get()
    job_name = alert_url_var.get()
    twilio_account = alert_twilio_account_var.get()
    scrape_interval = int(alert_interval_entry.get()) * 60
    response_codes = alert_response_codes_entry.get().split(',')

    alerts.append({
        'alert_name': alert_name,
        'job_name': job_name,
        'twilio_account': twilio_account,
        'scrape_interval': scrape_interval,
        'response_codes': response_codes
    })

    save_data()
    messagebox.showinfo("Success", "Alert added.")

def update_alert_url_options():
    alert_url_option_menu['values'] = list(monitoring_jobs.keys())

def update_alert_twilio_account_options():
    alert_twilio_account_option_menu['values'] = list(twilio_accounts.keys())

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
recipient_numbers_entry = tk.Entry(accounts_tab, width=100)
recipient_numbers_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Button(accounts_tab, text="Add Twilio Account", command=add_twilio_account).grid(row=5, column=1, padx=10, pady=10)

# Monitoring Tab
tk.Label(monitoring_tab, text="Job Name:").grid(row=0, column=0, padx=10, pady=10)
job_name_entry = tk.Entry(monitoring_tab)
job_name_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="URL Type:").grid(row=1, column=0, padx=10, pady=10)
url_type_var = tk.StringVar(value='internet')
url_type_option_menu = ttk.Combobox(monitoring_tab, textvariable=url_type_var, values=['internet', 'intranet'])
url_type_option_menu.grid(row=1, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="URL:").grid(row=2, column=0, padx=10, pady=10)
url_entry = tk.Entry(monitoring_tab, width=100)
url_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="Regex to Match (Optional):").grid(row=3, column=0, padx=10, pady=10)
regex_entry = tk.Entry(monitoring_tab, width=100)
regex_entry.grid(row=3, column=1, padx=10, pady=10)

tk.Label(monitoring_tab, text="Proxy URL (Optional):").grid(row=4, column=0, padx=10, pady=10)
proxy_entry = tk.Entry(monitoring_tab, width=100)
proxy_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Button(monitoring_tab, text="Add Monitoring Job", command=add_monitoring_job).grid(row=5, column=1, padx=10, pady=10)

# Alerts Tab
tk.Label(alerts_tab, text="Alert Name:").grid(row=0, column=0, padx=10, pady=10)
alert_name_entry = tk.Entry(alerts_tab)
alert_name_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(alerts_tab, text="Job Name:").grid(row=1, column=0, padx=10, pady=10)
alert_url_var = tk.StringVar()
alert_url_option_menu = ttk.Combobox(alerts_tab, textvariable=alert_url_var)
alert_url_option_menu.grid(row=1, column=1, padx=10, pady=10)
update_alert_url_options()

tk.Label(alerts_tab, text="Twilio Account:").grid(row=2, column=0, padx=10, pady=10)
alert_twilio_account_var = tk.StringVar()
alert_twilio_account_option_menu = ttk.Combobox(alerts_tab, textvariable=alert_twilio_account_var)
alert_twilio_account_option_menu.grid(row=2, column=1, padx=10, pady=10)
update_alert_twilio_account_options()

tk.Label(alerts_tab, text="Scrape Interval (minutes):").grid(row=3, column=0, padx=10, pady=10)
alert_interval_entry = tk.Entry(alerts_tab)
alert_interval_entry.grid(row=3, column=1, padx=10, pady=10)

tk.Label(alerts_tab, text="Response Codes (comma-separated):").grid(row=4, column=0, padx=10, pady=10)
alert_response_codes_entry = tk.Entry(alerts_tab, width=100)
alert_response_codes_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Button(alerts_tab, text="Add Alert", command=add_alert).grid(row=5, column=1, padx=10, pady=10)

# Silence Tab
tk.Label(silence_tab, text="Silence Period Start (YYYY-MM-DD HH:MM:SS):").grid(row=0, column=0, padx=10, pady=10)
silence_start_entry = tk.Entry(silence_tab)
silence_start_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(silence_tab, text="Silence Period End (YYYY-MM-DD HH:MM:SS):").grid(row=1, column=0, padx=10, pady=10)
silence_end_entry = tk.Entry(silence_tab)
silence_end_entry.grid(row=1, column=1, padx=10, pady=10)

tk.Label(silence_tab, text="Reason for Silence:").grid(row=2, column=0, padx=10, pady=10)
silence_reason_entry = tk.Entry(silence_tab, width=100)
silence_reason_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Button(silence_tab, text="Set Silence Period", command=set_silence_period).grid(row=3, column=1, padx=10, pady=10)

# Control Buttons
tk.Button(root, text="Start Monitoring", command=start_monitoring).pack(side=tk.LEFT, padx=10, pady=10)
tk.Button(root, text="Stop Monitoring", command=stop_monitoring).pack(side=tk.LEFT, padx=10, pady=10)
tk.Button(root, text="Save Configuration", command=save_data).pack(side=tk.LEFT, padx=10, pady=10)
tk.Button(root, text="Load Configuration", command=load_data).pack(side=tk.LEFT, padx=10, pady=10)

root.mainloop()
