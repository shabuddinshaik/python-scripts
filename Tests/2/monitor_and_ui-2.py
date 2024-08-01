import os
import time
import logging
import subprocess
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
import json
from twilio.rest import Client
from threading import Thread
import win32com.client

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

# Configure logger for URL monitoring
logger = logging.getLogger('url-monitor')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('url-monitor.log', when='midnight', interval=1)
handler.suffix = "%Y%m%d"
handler.setLevel(logging.DEBUG)
formatter = JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

# Global variables for Twilio and monitoring
twilio_client = None
twilio_details = {
    'account_sid': '',
    'auth_token': '',
    'twilio_number': '',
    'recipient_numbers': []
}
urls_to_monitor = []
intranet_urls_to_monitor = []
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
                url='http://demo.twilio.com/docs/voice.xml'
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
    while True:
        if not monitoring_active:
            break
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

        for url in intranet_urls_to_monitor:
            current_time = datetime.utcnow()
            if silence_period and silence_period[0] <= current_time <= silence_period[1]:
                status_label.config(text=f"{url}: Monitoring (Silenced)")
                continue

            status = check_intranet_url(url)
            status_label.config(text=f"{url}: {'Reachable' if status else 'Not Reachable'}")

            if not status:
                time.sleep(5 * 60)  # 5 minutes
                if not check_intranet_url(url):
                    send_call_alert(url)
                    
        time.sleep(evaluation_interval)

def start_monitoring():
    global monitoring_thread
    monitoring_thread = Thread(target=monitor_urls)
    monitoring_thread.daemon = True
    monitoring_thread.start()

def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    messagebox.showinfo("Stopped", "Monitoring stopped.")

def check_mailbox():
    try:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.Folders.Item(1).Folders["Inbox"]
        messages = inbox.Items
        messages.Sort("[ReceivedTime]", True)
        
        for message in messages:
            if "grafana" in message.Subject.lower():
                for key, value in mail_labels.items():
                    if key in message.Body and value in message.Body:
                        for number in twilio_details['recipient_numbers']:
                            send_call_alert(f"Grafana alert: {key} - {value}")
                        break
    except Exception as e:
        logger.error(f"Failed to check mailbox: {e}")

def monitor_mailbox():
    while True:
        if not monitoring_active or not mail_check_enabled:
            break
        check_mailbox()
        time.sleep(300)  # Check every 5 minutes

def start_mail_monitoring():
    global mail_monitoring_thread
    mail_monitoring_thread = Thread(target=monitor_mailbox)
    mail_monitoring_thread.daemon = True
    mail_monitoring_thread.start()

def save_and_start_monitoring():
    global twilio_client, mail_check_enabled, mail_labels, evaluation_interval, proxy_settings
    twilio_details['account_sid'] = account_sid_entry.get()
    twilio_details['auth_token'] = auth_token_entry.get()
    twilio_details['twilio_number'] = twilio_number_entry.get()
    twilio_details['recipient_numbers'] = recipient_numbers_entry.get().split(',')

    twilio_client = Client(twilio_details['account_sid'], twilio_details['auth_token'])

    urls = urls_entry.get().split(',')
    intranet_urls = intranet_urls_entry.get().split(',')
    evaluation_interval = int(evaluation_interval_entry.get()) * 60  # Convert minutes to seconds

    proxy_settings['http_proxy'] = http_proxy_entry.get()
    proxy_settings['https_proxy'] = https_proxy_entry.get()

    if 1 <= len(urls) <= 50 and 1 <= len(twilio_details['recipient_numbers']) <= 10 and 1 <= len(intranet_urls) <= 50:
        urls_to_monitor.extend(urls)
        intranet_urls_to_monitor.extend(intranet_urls)
        start_monitoring()
        if mail_check_var.get() == 1:
            mail_check_enabled = True
            mail_labels = dict(item.split(':') for item in mail_labels_entry.get().split(','))
            start_mail_monitoring()
        messagebox.showinfo("Success", "Monitoring started.")
    else:
        messagebox.showerror("Error", "Invalid input. Please check the limits.")

def set_silence_period():
    start_time_str = silence_start_entry.get()
    end_time_str = silence_end_entry.get()
    try:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        if start_time < end_time:
            global silence_period
            silence_period = (start_time, end_time)
            messagebox.showinfo("Success", "Silence period set.")
        else:
            messagebox.showerror("Error", "End time must be after start time.")
    except ValueError:
        messagebox.showerror("Error", "Invalid date/time format. Use YYYY-MM-DD HH:MM:SS.")

app = tk.Tk()
app.title("URL Monitor Configuration")

tk.Label(app, text="Twilio Account SID").pack()
account_sid_entry = tk.Entry(app)
account_sid_entry.pack()

tk.Label(app, text="Twilio Auth Token").pack()
auth_token_entry = tk.Entry(app, show="*")
auth_token_entry.pack()

tk.Label(app, text="Twilio Number").pack()
twilio_number_entry = tk.Entry(app)
twilio_number_entry.pack()

tk.Label(app, text="Recipient Numbers (comma-separated, max 10)").pack()
recipient_numbers_entry = tk.Entry(app)
recipient_numbers_entry.pack()

tk.Label(app, text="URLs to Monitor (comma-separated, max 50)").pack()
urls_entry = tk.Entry(app)
urls_entry.pack()

tk.Label(app, text="Intranet URLs to Monitor (comma-separated, max 50)").pack()
intranet_urls_entry = tk.Entry(app)
intranet_urls_entry.pack()

tk.Label(app, text="HTTP Proxy").pack()
http_proxy_entry = tk.Entry(app)
http_proxy_entry.pack()

tk.Label(app, text="HTTPS Proxy").pack()
https_proxy_entry = tk.Entry(app)
https_proxy_entry.pack()

tk.Label(app, text="Evaluation Interval (minutes)").pack()
evaluation_interval_entry = tk.Entry(app)
evaluation_interval_entry.pack()

mail_check_var = tk.IntVar()
tk.Checkbutton(app, text="Enable Mailbox Check", variable=mail_check_var).pack()

tk.Label(app, text="Mail Body Labels (comma-separated key:value pairs)").pack()
mail_labels_entry = tk.Entry(app)
mail_labels_entry.pack()

tk.Label(app, text="Silence Start Time (UTC, YYYY-MM-DD HH:MM:SS)").pack()
silence_start_entry = tk.Entry(app)
silence_start_entry.pack()

tk.Label(app, text="Silence End Time (UTC, YYYY-MM-DD HH:MM:SS)").pack()
silence_end_entry = tk.Entry(app)
silence_end_entry.pack()

tk.Button(app, text="Start Monitoring", command=save_and_start_monitoring).pack()
tk.Button(app, text="Stop Monitoring", command=stop_monitoring).pack()
tk.Button(app, text="Set Silence Period", command=set_silence_period).pack()

status_label = tk.Label(app, text="Status: Not Monitoring")
status_label.pack()

app.mainloop()
