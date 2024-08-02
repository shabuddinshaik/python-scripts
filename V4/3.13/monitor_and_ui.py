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
    'recipient_numbers': []
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
    try:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # 6 refers to the inbox
        folders = [inbox] + [inbox.Folders.Item(i) for i in range(1, inbox.Folders.Count + 1)]
        
        for folder in folders:
            messages = folder.Items
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
    app_logger.info("Mailbox monitoring started.")

def save_and_start_monitoring():
    global twilio_client, mail_check_enabled, mail_labels, evaluation_interval, proxy_settings
    twilio_details['account_sid'] = account_sid_entry.get()
    twilio_details['auth_token'] = auth_token_entry.get()
    twilio_details['twilio_number'] = twilio_number_entry.get()
    twilio_details['recipient_numbers'] = recipient_numbers_entry.get().split(',')

    twilio_client = Client(twilio_details['account_sid'], twilio_details['auth_token'])

    urls = urls_entry.get().split(',')
    evaluation_interval = int(evaluation_interval_entry.get()) * 60  # Convert minutes to seconds

    proxy_settings['http_proxy'] = http_proxy_entry.get()
    proxy_settings['https_proxy'] = https_proxy_entry.get()

    if 1 <= len(urls) <= 50 and 1 <= len(twilio_details['recipient_numbers']) <= 10:
        urls_to_monitor.extend(urls)
        start_monitoring()
        if mail_check_var.get() == 1:
            mail_check_enabled = True
            mail_labels = dict(item.split(':') for item in mail_labels_entry.get().split(','))
            start_mail_monitoring()
        save_configuration()
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
        'silence_period': silence_period
    }
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file)
    app_logger.info("Configuration saved.")

def load_configuration():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
            twilio_details.update(config.get('twilio_details', {}))
            urls_to_monitor.extend(config.get('urls_to_monitor', []))
            global evaluation_interval
            evaluation_interval = config.get('evaluation_interval', 300)
            proxy_settings.update(config.get('proxy_settings', {}))
            global mail_check_enabled
            mail_check_enabled = config.get('mail_check_enabled', False)
            mail_labels.update(config.get('mail_labels', {}))
            global silence_period
            silence_period = tuple(config.get('silence_period', (None, None)))

app = tk.Tk()
app.title("URL Monitor Configuration")
app.geometry('600x400')

load_configuration()

notebook = ttk.Notebook(app)
notebook.pack(pady=10, expand=True)

# Twilio Account Details Tab
twilio_frame = ttk.Frame(notebook, width=400, height=280)
twilio_frame.pack(fill='both', expand=True)

ttk.Label(twilio_frame, text="Twilio Account SID").pack()
account_sid_entry = ttk.Entry(twilio_frame)
account_sid_entry.insert(0, twilio_details['account_sid'])
account_sid_entry.pack()

ttk.Label(twilio_frame, text="Twilio Auth Token").pack()
auth_token_entry = ttk.Entry(twilio_frame, show="*")
auth_token_entry.insert(0, twilio_details['auth_token'])
auth_token_entry.pack()

ttk.Label(twilio_frame, text="Twilio Number").pack()
twilio_number_entry = ttk.Entry(twilio_frame)
twilio_number_entry.insert(0, twilio_details['twilio_number'])
twilio_number_entry.pack()

ttk.Label(twilio_frame, text="Recipient Numbers (comma-separated, max 10)").pack()
recipient_numbers_entry = ttk.Entry(twilio_frame)
recipient_numbers_entry.insert(0, ','.join(twilio_details['recipient_numbers']))
recipient_numbers_entry.pack()

notebook.add(twilio_frame, text='Twilio')

# URLs to Monitor Tab
urls_frame = ttk.Frame(notebook, width=400, height=280)
urls_frame.pack(fill='both', expand=True)

ttk.Label(urls_frame, text="URLs to Monitor (comma-separated, max 50)").pack()
urls_entry = ttk.Entry(urls_frame)
urls_entry.insert(0, ','.join(urls_to_monitor))
urls_entry.pack()

notebook.add(urls_frame, text='URLs')

# Proxy Settings Tab
proxy_frame = ttk.Frame(notebook, width=400, height=280)
proxy_frame.pack(fill='both', expand=True)

ttk.Label(proxy_frame, text="HTTP Proxy").pack()
http_proxy_entry = ttk.Entry(proxy_frame)
http_proxy_entry.insert(0, proxy_settings.get('http_proxy', ''))
http_proxy_entry.pack()

ttk.Label(proxy_frame, text="HTTPS Proxy").pack()
https_proxy_entry = ttk.Entry(proxy_frame)
https_proxy_entry.insert(0, proxy_settings.get('https_proxy', ''))
https_proxy_entry.pack()

notebook.add(proxy_frame, text='Proxy')

# Mailbox Check Tab
mail_frame = ttk.Frame(notebook, width=400, height=280)
mail_frame.pack(fill='both', expand=True)

mail_check_var = tk.IntVar(value=1 if mail_check_enabled else 0)
ttk.Checkbutton(mail_frame, text="Enable Mailbox Check", variable=mail_check_var).pack()

ttk.Label(mail_frame, text="Mail Body Labels (comma-separated key:value pairs)").pack()
mail_labels_entry = ttk.Entry(mail_frame)
mail_labels_entry.insert(0, ','.join(f"{k}:{v}" for k, v in mail_labels.items()))
mail_labels_entry.pack()

notebook.add(mail_frame, text='Mailbox')

# Silence Period Tab
silence_frame = ttk.Frame(notebook, width=400, height=280)
silence_frame.pack(fill='both', expand=True)

ttk.Label(silence_frame, text="Silence Start Time (UTC, YYYY-MM-DD HH:MM:SS)").pack()
silence_start_entry = ttk.Entry(silence_frame)
silence_start_entry.insert(0, silence_period[0].strftime('%Y-%m-%d %H:%M:%S') if silence_period and silence_period[0] else '')
silence_start_entry.pack()

ttk.Label(silence_frame, text="Silence End Time (UTC, YYYY-MM-DD HH:MM:SS)").pack()
silence_end_entry = ttk.Entry(silence_frame)
silence_end_entry.insert(0, silence_period[1].strftime('%Y-%m-%d %H:%M:%S') if silence_period and silence_period[1] else '')
silence_end_entry.pack()

ttk.Button(silence_frame, text="Set Silence Period", command=set_silence_period).pack()

notebook.add(silence_frame, text='Silence Period')

# Evaluation Interval and Start/Stop Buttons Tab
eval_frame = ttk.Frame(notebook, width=400, height=280)
eval_frame.pack(fill='both', expand=True)

ttk.Label(eval_frame, text="Evaluation Interval (minutes)").pack()
evaluation_interval_entry = ttk.Entry(eval_frame)
evaluation_interval_entry.insert(0, str(evaluation_interval // 60))
evaluation_interval_entry.pack()

ttk.Button(eval_frame, text="Start Monitoring", command=save_and_start_monitoring).pack()
ttk.Button(eval_frame, text="Stop Monitoring", command=stop_monitoring).pack()

status_label = ttk.Label(eval_frame, text="Status: Not Monitoring")
status_label.pack()

notebook.add(eval_frame, text='Settings')

app.mainloop()
