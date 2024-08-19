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
import pythoncom
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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

# Access logs for network activities
access_logger = logging.getLogger('access-log')
access_logger.setLevel(logging.DEBUG)
access_handler = TimedRotatingFileHandler('access.log', when='midnight', interval=1)
access_handler.suffix = "%Y%m%d"
access_handler.setLevel(logging.DEBUG)
access_formatter = JsonFormatter()
access_handler.setFormatter(access_formatter)
access_logger.addHandler(access_handler)

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

class LoggingAdapter(HTTPAdapter):
    def send(self, request, **kwargs):
        access_logger.debug(f"Request URL: {request.url}")
        access_logger.debug(f"Request headers: {request.headers}")
        access_logger.debug(f"Request body: {request.body}")

        response = super().send(request, **kwargs)

        access_logger.debug(f"Response status code: {response.status_code}")
        access_logger.debug(f"Response headers: {response.headers}")
        access_logger.debug(f"Response body: {response.text}")

        return response

def send_call_alert(url):
    try:
        for number in twilio_details['recipient_numbers']:
            access_logger.debug(f"Sending call alert to {number} for URL: {url}")
            call = twilio_client.calls.create(
                to=number,
                from_=twilio_details['twilio_number'],
                url=twilio_details['twiml_bin_url']
            )
            logger.info(f"Call alert sent to {number} for URL: {url}")
            access_logger.info(f"Call alert sent to {number} with SID: {call.sid} for URL: {url}")
    except Exception as e:
        logger.error(f"Failed to send call alert: {e}")
        access_logger.error(f"Error sending call alert: {e}")

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
            proxy_client = LoggingAdapter()
            session = requests.Session()
            session.mount('https://', proxy_client)
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
        messagebox.showerror("Error", f"Value error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        messagebox.showerror("Error", f"Unexpected error: {e}")

def save_configuration():
    # Save configuration to file or database if needed
    pass

def load_configuration():
    # Load configuration from file or database if needed
    pass

def setup_ui():
    # Main window setup
    window = tk.Tk()
    window.title("URL Monitoring")

    # Input fields
    global account_sid_entry, auth_token_entry, twilio_number_entry, recipient_numbers_entry, twiml_bin_url_entry
    global urls_entry, evaluation_interval_entry, http_proxy_entry, https_proxy_entry, mail_labels_entry
    global status_label, mail_check_var

    tk.Label(window, text="Account SID:").grid(row=0, column=0)
    account_sid_entry = tk.Entry(window, width=50)
    account_sid_entry.grid(row=0, column=1)

    tk.Label(window, text="Auth Token:").grid(row=1, column=0)
    auth_token_entry = tk.Entry(window, width=50)
    auth_token_entry.grid(row=1, column=1)

    tk.Label(window, text="Twilio Number:").grid(row=2, column=0)
    twilio_number_entry = tk.Entry(window, width=50)
    twilio_number_entry.grid(row=2, column=1)

    tk.Label(window, text="Recipient Numbers (comma separated):").grid(row=3, column=0)
    recipient_numbers_entry = tk.Entry(window, width=50)
    recipient_numbers_entry.grid(row=3, column=1)

    tk.Label(window, text="Twiml Bin URL:").grid(row=4, column=0)
    twiml_bin_url_entry = tk.Entry(window, width=50)
    twiml_bin_url_entry.grid(row=4, column=1)

    tk.Label(window, text="URLs to Monitor (comma separated):").grid(row=5, column=0)
    urls_entry = tk.Entry(window, width=50)
    urls_entry.grid(row=5, column=1)

    tk.Label(window, text="Evaluation Interval (minutes):").grid(row=6, column=0)
    evaluation_interval_entry = tk.Entry(window, width=50)
    evaluation_interval_entry.grid(row=6, column=1)

    tk.Label(window, text="HTTP Proxy:").grid(row=7, column=0)
    http_proxy_entry = tk.Entry(window, width=50)
    http_proxy_entry.grid(row=7, column=1)

    tk.Label(window, text="HTTPS Proxy:").grid(row=8, column=0)
    https_proxy_entry = tk.Entry(window, width=50)
    https_proxy_entry.grid(row=8, column=1)

    tk.Label(window, text="Mail Labels (label:value, comma separated):").grid(row=9, column=0)
    mail_labels_entry = tk.Entry(window, width=50)
    mail_labels_entry.grid(row=9, column=1)

    mail_check_var = tk.IntVar()
    tk.Checkbutton(window, text="Check Mailbox", variable=mail_check_var).grid(row=10, column=0, columnspan=2)

    status_label = tk.Label(window, text="Status: Not Monitoring")
    status_label.grid(row=11, column=0, columnspan=2)

    tk.Button(window, text="Start Monitoring", command=save_and_start_monitoring).grid(row=12, column=0, columnspan=2)

    window.mainloop()

if __name__ == "__main__":
    setup_ui()
