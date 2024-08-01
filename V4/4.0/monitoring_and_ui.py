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

def save_config():
    config = {
        'twilio_details': twilio_details,
        'urls_to_monitor': urls_to_monitor,
        'intranet_urls_to_monitor': intranet_urls_to_monitor,
        'evaluation_interval': evaluation_interval,
        'proxy_settings': proxy_settings,
        'mail_check_enabled': mail_check_enabled,
        'mail_labels': mail_labels,
        'silence_period': [silence_period[0].strftime('%Y-%m-%d %H:%M:%S'), silence_period[1].strftime('%Y-%m-%d %H:%M:%S')] if silence_period else None
    }
    with open('config.json', 'w') as f:
        json.dump(config, f)
    logger.info("Configuration saved.")

def load_config():
    global twilio_details, urls_to_monitor, intranet_urls_to_monitor, evaluation_interval, proxy_settings, mail_check_enabled, mail_labels, silence_period
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            config = json.load(f)
        twilio_details = config.get('twilio_details', twilio_details)
        urls_to_monitor = config.get('urls_to_monitor', urls_to_monitor)
        intranet_urls_to_monitor = config.get('intranet_urls_to_monitor', intranet_urls_to_monitor)
        evaluation_interval = config.get('evaluation_interval', evaluation_interval)
        proxy_settings = config.get('proxy_settings', proxy_settings)
        mail_check_enabled = config.get('mail_check_enabled', mail_check_enabled)
        mail_labels = config.get('mail_labels', mail_labels)
        silence_period = config.get('silence_period')
        if silence_period:
            silence_period = (datetime.strptime(silence_period[0], '%Y-%m-%d %H:%M:%S'), datetime.strptime(silence_period[1], '%Y-%m-%d %H:%M:%S'))
        logger.info("Configuration loaded.")

def update_ui_with_config():
    account_sid_entry.insert(0, twilio_details['account_sid'])
    auth_token_entry.insert(0, twilio_details['auth_token'])
    twilio_number_entry.insert(0, twilio_details['twilio_number'])
    recipient_numbers_entry.insert(0, ','.join(twilio_details['recipient_numbers']))
    urls_entry.insert(0, ','.join(urls_to_monitor))
    intranet_urls_entry.insert(0, ','.join(intranet_urls_to_monitor))
    evaluation_interval_entry.insert(0, str(evaluation_interval // 60))
    http_proxy_entry.insert(0, proxy_settings.get('http_proxy', ''))
    https_proxy_entry.insert(0, proxy_settings.get('https_proxy', ''))
    if mail_check_enabled:
        mail_check_var.set(1)
        mail_labels_entry.insert(0, ','.join(f"{k}:{v}" for k, v in mail_labels.items()))
    if silence_period:
        silence_start_entry.insert(0, silence_period[0].strftime('%Y-%m-%d %H:%M:%S'))
        silence_end_entry.insert(0, silence_period[1].strftime('%Y-%m-%d %H:%M:%S'))

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
    logger.info("Monitoring started.")

def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    messagebox.showinfo("Stopped", "Monitoring stopped.")
    logger.info("Monitoring stopped.")

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
    logger.info("Mailbox monitoring started.")

def save_and_start_monitoring():
    global twilio_client, mail_check_enabled, mail_labels, evaluation_interval, proxy_settings
    twilio_details['account_sid'] = account_sid_entry.get()
    twilio_details['auth_token'] = auth_token_entry.get()
    twilio_details['twilio_number'] = twilio_number_entry.get()
    twilio_details['recipient_numbers'] = recipient_numbers_entry.get().split(',')

    urls_to_monitor.extend(urls_entry.get().split(','))
    intranet_urls_to_monitor.extend(intranet_urls_entry.get().split(','))
    evaluation_interval = int(evaluation_interval_entry.get()) * 60

    proxy_settings['http_proxy'] = http_proxy_entry.get()
    proxy_settings['https_proxy'] = https_proxy_entry.get()

    if mail_check_var.get():
        mail_check_enabled = True
        mail_labels = dict(item.split(":") for item in mail_labels_entry.get().split(","))
    else:
        mail_check_enabled = False

    silence_start = silence_start_entry.get()
    silence_end = silence_end_entry.get()
    if silence_start and silence_end:
        silence_period = (
            datetime.strptime(silence_start, '%Y-%m-%d %H:%M:%S'),
            datetime.strptime(silence_end, '%Y-%m-%d %H:%M:%S')
        )

    twilio_client = Client(twilio_details['account_sid'], twilio_details['auth_token'])

    save_config()
    start_monitoring()
    if mail_check_enabled:
        start_mail_monitoring()

def main():
    global account_sid_entry, auth_token_entry, twilio_number_entry, recipient_numbers_entry
    global urls_entry, intranet_urls_entry, evaluation_interval_entry, http_proxy_entry, https_proxy_entry
    global mail_check_var, mail_labels_entry, silence_start_entry, silence_end_entry, status_label

    root = tk.Tk()
    root.title("URL Monitor")

    ttk.Label(root, text="Twilio Account SID").grid(row=0, column=0, padx=10, pady=5)
    account_sid_entry = ttk.Entry(root, width=50)
    account_sid_entry.grid(row=0, column=1, padx=10, pady=5)

    ttk.Label(root, text="Twilio Auth Token").grid(row=1, column=0, padx=10, pady=5)
    auth_token_entry = ttk.Entry(root, width=50, show='*')
    auth_token_entry.grid(row=1, column=1, padx=10, pady=5)

    ttk.Label(root, text="Twilio Number").grid(row=2, column=0, padx=10, pady=5)
    twilio_number_entry = ttk.Entry(root, width=50)
    twilio_number_entry.grid(row=2, column=1, padx=10, pady=5)

    ttk.Label(root, text="Recipient Numbers (comma separated)").grid(row=3, column=0, padx=10, pady=5)
    recipient_numbers_entry = ttk.Entry(root, width=50)
    recipient_numbers_entry.grid(row=3, column=1, padx=10, pady=5)

    ttk.Label(root, text="URLs to Monitor (comma separated)").grid(row=4, column=0, padx=10, pady=5)
    urls_entry = ttk.Entry(root, width=50)
    urls_entry.grid(row=4, column=1, padx=10, pady=5)

    ttk.Label(root, text="Intranet URLs to Monitor (comma separated)").grid(row=5, column=0, padx=10, pady=5)
    intranet_urls_entry = ttk.Entry(root, width=50)
    intranet_urls_entry.grid(row=5, column=1, padx=10, pady=5)

    ttk.Label(root, text="Evaluation Interval (minutes)").grid(row=6, column=0, padx=10, pady=5)
    evaluation_interval_entry = ttk.Entry(root, width=50)
    evaluation_interval_entry.grid(row=6, column=1, padx=10, pady=5)

    ttk.Label(root, text="HTTP Proxy").grid(row=7, column=0, padx=10, pady=5)
    http_proxy_entry = ttk.Entry(root, width=50)
    http_proxy_entry.grid(row=7, column=1, padx=10, pady=5)

    ttk.Label(root, text="HTTPS Proxy").grid(row=8, column=0, padx=10, pady=5)
    https_proxy_entry = ttk.Entry(root, width=50)
    https_proxy_entry.grid(row=8, column=1, padx=10, pady=5)

    mail_check_var = tk.IntVar()
    ttk.Checkbutton(root, text="Enable Mail Check", variable=mail_check_var).grid(row=9, column=0, columnspan=2, padx=10, pady=5)

    ttk.Label(root, text="Mail Labels (format: label1:content1,label2:content2)").grid(row=10, column=0, padx=10, pady=5)
    mail_labels_entry = ttk.Entry(root, width=50)
    mail_labels_entry.grid(row=10, column=1, padx=10, pady=5)

    ttk.Label(root, text="Silence Period Start (YYYY-MM-DD HH:MM:SS)").grid(row=11, column=0, padx=10, pady=5)
    silence_start_entry = ttk.Entry(root, width=50)
    silence_start_entry.grid(row=11, column=1, padx=10, pady=5)

    ttk.Label(root, text="Silence Period End (YYYY-MM-DD HH:MM:SS)").grid(row=12, column=0, padx=10, pady=5)
    silence_end_entry = ttk.Entry(root, width=50)
    silence_end_entry.grid(row=12, column=1, padx=10, pady=5)

    status_label = ttk.Label(root, text="Status: Idle")
    status_label.grid(row=13, column=0, columnspan=2, padx=10, pady=5)

    ttk.Button(root, text="Save and Start Monitoring", command=save_and_start_monitoring).grid(row=14, column=0, padx=10, pady=5)
    ttk.Button(root, text="Stop Monitoring", command=stop_monitoring).grid(row=14, column=1, padx=10, pady=5)

    load_config()
    update_ui_with_config()

    root.mainloop()

if __name__ == '__main__':
    main()
