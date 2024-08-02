import os
import time
import logging
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
import json
from twilio.rest import Client
from threading import Thread
import win32com.client
import pythoncom  # Import pythoncom for COM initialization

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

app_logger = logging.getLogger('app-log')
app_logger.setLevel(logging.DEBUG)
app_handler = TimedRotatingFileHandler('app.log', when='midnight', interval=1)
app_handler.suffix = "%Y%m%d"
app_handler.setLevel(logging.DEBUG)
app_formatter = JsonFormatter()
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)

# Global variables for Twilio and monitoring
twilio_client = None
twilio_details = {
    'account_sid': '',
    'auth_token': '',
    'twilio_number': '',
    'recipient_numbers': [],
    'twiml_bin_url': ''
}
urls_to_monitor = []
monitoring_active = True
silence_period = None
mail_check_enabled = False
mail_labels = {}
evaluation_interval = 300  # Default to 5 minutes
proxy_settings = {}

def send_call_alert(url):
    try:
        for number in twilio_details['recipient_numbers']:
            call = twilio_client.calls.create(
                to=number,
                from_=twilio_details['twilio_number'],
                url=twilio_details['twiml_bin_url']  # Use the TwiML Bin URL from Twilio details
            )
            logger.info(f"Call alert sent to {number} for URL: {url}")
    except Exception as e:
        logger.error(f"Failed to send call alert: {e}")

def check_url(url):
    try:
        response = subprocess.run(['ping', '-n', '1', url], capture_output=True, text=True)
        if response.returncode == 0:
            logger.info(f"URL {url} is reachable.")
            return True
        else:
            logger.error(f"URL {url} is not reachable.")
            return False
    except Exception as e:
        logger.error(f"Failed to check URL {url}: {e}")
        return False

def monitor_urls():
    while monitoring_active:
        for url in urls_to_monitor:
            current_time = datetime.utcnow()
            if silence_period and silence_period[0] <= current_time <= silence_period[1]:
                status_label.config(text=f"{url}: Monitoring (Silenced)")
                continue

            status = check_url(url)
            status_label.config(text=f"{url}: {'Reachable' if status else 'Not Reachable'}")

            if not status:
                time.sleep(5 * 60)  # 5 minutes
                if not check_url(url):
                    send_call_alert(url)
                    
        time.sleep(evaluation_interval)

def start_monitoring():
    global monitoring_thread
    monitoring_thread = Thread(target=monitor_urls)
    monitoring_thread.daemon = True
    monitoring_thread.start()
    app_logger.info("Monitoring started.")

def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    app_logger.info("Monitoring stopped.")
    messagebox.showinfo("Stopped", "Monitoring stopped.")

def check_mailbox():
    pythoncom.CoInitialize()  # Initialize COM library
    try:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # 6 refers to the inbox

        current_time = datetime.utcnow()
        five_minutes_ago = current_time - timedelta(minutes=5)

        for message in inbox.Items:
            received_time = message.ReceivedTime
            if received_time >= five_minutes_ago and received_time <= current_time:
                subject = message.Subject.lower()
                body = message.Body.lower()

                for label, value in mail_labels.items():
                    if label.lower() in subject and value.lower() in body:
                        for number in twilio_details['recipient_numbers']:
                            send_call_alert(f"Email alert: {label} - {value}")
                        break
    except Exception as e:
        logger.error(f"Failed to check mailbox: {e}")
    finally:
        pythoncom.CoUninitialize()  # Uninitialize COM library

def monitor_mailbox():
    while monitoring_active and mail_check_enabled:
        check_mailbox()
        time.sleep(300)  # Check every 5 minutes

def start_mail_monitoring():
    global mail_monitoring_thread
    mail_monitoring_thread = Thread(target=monitor_mailbox)
    mail_monitoring_thread.daemon = True
    mail_monitoring_thread.start()
    app_logger.info("Mailbox monitoring started.")

def save_and_start_monitoring():
    global twilio_client, mail_check_enabled, mail_labels, evaluation_interval, proxy_settings
    try:
        twilio_details['account_sid'] = account_sid_entry.get().strip() or None
        twilio_details['auth_token'] = auth_token_entry.get().strip() or None
        twilio_details['twilio_number'] = twilio_number_entry.get().strip() or None
        recipient_numbers = recipient_numbers_entry.get().split(',')
        twilio_details['recipient_numbers'] = [num.strip() for num in recipient_numbers if num.strip()]
        twilio_details['twiml_bin_url'] = twiml_bin_url_entry.get().strip() or None

        # Ensure none of the required details are None
        if not all([twilio_details['account_sid'], twilio_details['auth_token'], twilio_details['twilio_number'], twilio_details['twiml_bin_url']]):
            raise ValueError("Twilio details are incomplete. Please fill in all the required fields.")

        # Initialize Twilio client with proxy settings if provided
        if proxy_settings.get('http_proxy') or proxy_settings.get('https_proxy'):
            from twilio.http.http_client import TwilioHttpClient
            proxy_client = TwilioHttpClient(proxy={
                'http': proxy_settings.get('http_proxy', ''),
                'https': proxy_settings.get('https_proxy', '')
            })
            twilio_client = Client(twilio_details['account_sid'], twilio_details['auth_token'], http_client=proxy_client)
        else:
            twilio_client = Client(twilio_details['account_sid'], twilio_details['auth_token'])

        urls = [url.strip() for url in urls_entry.get().split(',')]
        if not urls:
            raise ValueError("URLs list is empty. Please provide at least one URL.")

        evaluation_interval = int(evaluation_interval_entry.get().strip()) * 60  # Convert minutes to seconds

        proxy_settings['http_proxy'] = http_proxy_entry.get().strip()
        proxy_settings['https_proxy'] = https_proxy_entry.get().strip()

        if 1 <= len(urls) <= 50 and 1 <= len(twilio_details['recipient_numbers']) <= 10:
            urls_to_monitor.extend(urls)
            monitoring_active = True
            start_monitoring()
            if mail_check_var.get() == 1:
                mail_check_enabled = True
                mail_labels = dict(item.split(':') for item in mail_labels_entry.get().split(',') if ':' in item)
                start_mail_monitoring()
            save_configuration()
            messagebox.showinfo("Success", "Monitoring started.")
        else:
            raise ValueError("Invalid input. Please check the limits.")
    except ValueError as e:
        logger.error(f"Value error: {e}")
        messagebox.showerror("Error", str(e))
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        messagebox.showerror("Error", f"Failed to start monitoring: {e}")

def set_silence_period():
    start_time_str = silence_start_entry.get()
    end_time_str = silence_end_entry.get()
    try:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        if start_time < end_time:
            global silence_period
            silence_period = (start_time, end_time)
            save_configuration()
            messagebox.showinfo("Success", "Silence period set.")
        else:
            messagebox.showerror("Error", "End time must be after start time.")
    except ValueError:
        messagebox.showerror("Error", "Invalid date/time format. Use YYYY-MM-DD HH:MM:SS.")

def save_configuration():
    config = {
        'twilio_details': twilio_details,
        'urls_to_monitor': urls_to_monitor,
        'evaluation_interval': evaluation_interval,
        'proxy_settings': proxy_settings,
        'mail_check_enabled': mail_check_enabled,
        'mail_labels': mail_labels,
        'silence_period': [silence_period[0].isoformat(), silence_period[1].isoformat()] if silence_period else None
    }
    with open('config.json', 'w') as f:
        json.dump(config, f)
    app_logger.info("Configuration saved.")

def load_configuration():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        global twilio_details, urls_to_monitor, evaluation_interval, proxy_settings, mail_check_enabled, mail_labels, silence_period
        twilio_details = config.get('twilio_details', twilio_details)
        urls_to_monitor = config.get('urls_to_monitor', [])
        evaluation_interval = config.get('evaluation_interval', 300)
        proxy_settings = config.get('proxy_settings', {})
        mail_check_enabled = config.get('mail_check_enabled', False)
        mail_labels = config.get('mail_labels', {})
        silence_period = config.get('silence_period', None)
        if silence_period:
            silence_period = (datetime.fromisoformat(silence_period[0]), datetime.fromisoformat(silence_period[1]))
    except FileNotFoundError:
        app_logger.info("No configuration file found. Using defaults.")
    except json.JSONDecodeError:
        app_logger.error("Failed to decode configuration file. Using defaults.")

# Load configuration on startup
load_configuration()

# UI Setup
root = tk.Tk()
root.title("URL Monitoring Tool")
root.geometry("800x600")

tab_control = ttk.Notebook(root)

# Monitoring tab
monitoring_tab = ttk.Frame(tab_control)
tab_control.add(monitoring_tab, text="Monitoring")

urls_label = tk.Label(monitoring_tab, text="URLs to Monitor (comma separated):")
urls_label.pack(pady=5)
urls_entry = tk.Entry(monitoring_tab, width=50)
urls_entry.pack(pady=5)

evaluation_interval_label = tk.Label(monitoring_tab, text="Evaluation Interval (minutes):")
evaluation_interval_label.pack(pady=5)
evaluation_interval_entry = tk.Entry(monitoring_tab, width=10)
evaluation_interval_entry.pack(pady=5)

# Twilio tab
twilio_tab = ttk.Frame(tab_control)
tab_control.add(twilio_tab, text="Twilio")

account_sid_label = tk.Label(twilio_tab, text="Account SID:")
account_sid_label.pack(pady=5)
account_sid_entry = tk.Entry(twilio_tab, width=50)
account_sid_entry.pack(pady=5)

auth_token_label = tk.Label(twilio_tab, text="Auth Token:")
auth_token_label.pack(pady=5)
auth_token_entry = tk.Entry(twilio_tab, width=50)
auth_token_entry.pack(pady=5)

twilio_number_label = tk.Label(twilio_tab, text="Twilio Number:")
twilio_number_label.pack(pady=5)
twilio_number_entry = tk.Entry(twilio_tab, width=50)
twilio_number_entry.pack(pady=5)

recipient_numbers_label = tk.Label(twilio_tab, text="Recipient Numbers (comma separated):")
recipient_numbers_label.pack(pady=5)
recipient_numbers_entry = tk.Entry(twilio_tab, width=50)
recipient_numbers_entry.pack(pady=5)

twiml_bin_url_label = tk.Label(twilio_tab, text="TwiML Bin URL:")
twiml_bin_url_label.pack(pady=5)
twiml_bin_url_entry = tk.Entry(twilio_tab, width=50)
twiml_bin_url_entry.pack(pady=5)

# Proxy tab
proxy_tab = ttk.Frame(tab_control)
tab_control.add(proxy_tab, text="Proxy Settings")

http_proxy_label = tk.Label(proxy_tab, text="HTTP Proxy:")
http_proxy_label.pack(pady=5)
http_proxy_entry = tk.Entry(proxy_tab, width=50)
http_proxy_entry.pack(pady=5)

https_proxy_label = tk.Label(proxy_tab, text="HTTPS Proxy:")
https_proxy_label.pack(pady=5)
https_proxy_entry = tk.Entry(proxy_tab, width=50)
https_proxy_entry.pack(pady=5)

# Silence tab
silence_tab = ttk.Frame(tab_control)
tab_control.add(silence_tab, text="Silence Period")

silence_start_label = tk.Label(silence_tab, text="Silence Start (YYYY-MM-DD HH:MM:SS):")
silence_start_label.pack(pady=5)
silence_start_entry = tk.Entry(silence_tab, width=50)
silence_start_entry.pack(pady=5)

silence_end_label = tk.Label(silence_tab, text="Silence End (YYYY-MM-DD HH:MM:SS):")
silence_end_label.pack(pady=5)
silence_end_entry = tk.Entry(silence_tab, width=50)
silence_end_entry.pack(pady=5)

set_silence_btn = tk.Button(silence_tab, text="Set Silence Period", command=set_silence_period)
set_silence_btn.pack(pady=5)

# Mailbox tab
mailbox_tab = ttk.Frame(tab_control)
tab_control.add(mailbox_tab, text="Mailbox Monitoring")

mail_check_var = tk.IntVar()
mail_check_checkbox = tk.Checkbutton(mailbox_tab, text="Enable Mailbox Monitoring", variable=mail_check_var)
mail_check_checkbox.pack(pady=5)

mail_labels_label = tk.Label(mailbox_tab, text="Mail Labels (Format: label:keyword, comma separated):")
mail_labels_label.pack(pady=5)
mail_labels_entry = tk.Entry(mailbox_tab, width=50)
mail_labels_entry.pack(pady=5)

# Status
status_label = tk.Label(root, text="Status: Not Monitoring", anchor="w", justify="left")
status_label.pack(fill="x", pady=5)

# Buttons
start_btn = tk.Button(root, text="Start Monitoring", command=save_and_start_monitoring)
start_btn.pack(side="left", padx=10, pady=10)

stop_btn = tk.Button(root, text="Stop Monitoring", command=stop_monitoring)
stop_btn.pack(side="left", padx=10, pady=10)

tab_control.pack(expand=1, fill="both")
root.mainloop()
