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
regex_patterns = {}

def send_alert(alert_type, url, message):
    try:
        for number in twilio_details['recipient_numbers']:
            if alert_type == 'call':
                call = twilio_client.calls.create(
                    to=number,
                    from_=twilio_details['twilio_number'],
                    url='http://demo.twilio.com/docs/voice.xml'
                )
                logger.info(f"Call alert sent to {number} for URL: {url}")
            elif alert_type == 'sms':
                twilio_client.messages.create(
                    body=message,
                    from_=twilio_details['twilio_number'],
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
                    return True
                else:
                    logger.error(f"Regex {regex} did not match for URL {url}.")
                    return False
            return True
        else:
            logger.error(f"URL {url} is not reachable with status code {status_code}.")
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
    while monitoring_active:
        for url, regex in urls_to_monitor:
            current_time = datetime.utcnow()
            if silence_period and silence_period[0] <= current_time <= silence_period[1]:
                status_label.config(text=f"{url}: Monitoring (Silenced)")
                continue

            status = check_url(url, regex)
            status_label.config(text=f"{url}: {'Reachable' if status else 'Not Reachable'}")

            if not status:
                time.sleep(5 * 60)  # 5 minutes
                if not check_url(url, regex):
                    send_alert('call', url, f"URL {url} is down.")

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
                    send_alert('call', url, f"Intranet URL {url} is down.")
                    
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
                            send_alert('call', f"Grafana alert: {key} - {value}")
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

    urls = [(url.strip(), regex_patterns.get(url.strip())) for url in urls_entry.get().split(',')]
    intranet_urls = [url.strip() for url in intranet_urls_entry.get().split(',')]
    evaluation_interval = int(evaluation_interval_entry.get()) * 60  # Convert minutes to seconds

    proxy_settings['http_proxy'] = http_proxy_entry.get()
    proxy_settings['https_proxy'] = https_proxy_entry.get()

    if 1 <= len(urls) <= 50 and 1 <= len(twilio_details['recipient_numbers']) <= 10 and 0 <= len(intranet_urls) <= 50:
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

def save_config():
    config = {
        'twilio_details': twilio_details,
        'urls_to_monitor': urls_to_monitor,
        'intranet_urls_to_monitor': intranet_urls_to_monitor,
        'mail_labels': mail_labels,
        'evaluation_interval': evaluation_interval,
        'proxy_settings': proxy_settings,
        'silence_period': (silence_start_entry.get(), silence_end_entry.get())
    }
    with open('monitor_config.json', 'w') as f:
        json.dump(config, f)
    messagebox.showinfo("Success", "Configuration saved.")

def load_config():
    global twilio_details, urls_to_monitor, intranet_urls_to_monitor, mail_labels, evaluation_interval, proxy_settings, silence_period
    try:
        with open('monitor_config.json', 'r') as f:
            config = json.load(f)
            twilio_details = config['twilio_details']
            urls_to_monitor = config['urls_to_monitor']
            intranet_urls_to_monitor = config['intranet_urls_to_monitor']
            mail_labels = config['mail_labels']
            evaluation_interval = config['evaluation_interval']
            proxy_settings = config['proxy_settings']
            silence_period = tuple(datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t in config['silence_period'])
        messagebox.showinfo("Success", "Configuration loaded.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load configuration: {e}")

# GUI setup
root = tk.Tk()
root.title("URL Monitoring Tool")

tab_control = ttk.Notebook(root)

main_tab = ttk.Frame(tab_control)
twilio_tab = ttk.Frame(tab_control)
mail_tab = ttk.Frame(tab_control)
proxy_tab = ttk.Frame(tab_control)

tab_control.add(main_tab, text="Main")
tab_control.add(twilio_tab, text="Twilio")
tab_control.add(mail_tab, text="Mail")
tab_control.add(proxy_tab, text="Proxy")

tab_control.pack(expand=1, fill='both')

# Main Tab
tk.Label(main_tab, text="URLs to Monitor (comma-separated):").grid(row=0, column=0, padx=10, pady=10)
urls_entry = tk.Entry(main_tab, width=100)
urls_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(main_tab, text="Intranet URLs to Monitor (comma-separated):").grid(row=1, column=0, padx=10, pady=10)
intranet_urls_entry = tk.Entry(main_tab, width=100)
intranet_urls_entry.grid(row=1, column=1, padx=10, pady=10)

tk.Label(main_tab, text="Evaluation Interval (minutes):").grid(row=2, column=0, padx=10, pady=10)
evaluation_interval_entry = tk.Entry(main_tab)
evaluation_interval_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Button(main_tab, text="Save and Start Monitoring", command=save_and_start_monitoring).grid(row=3, column=0, padx=10, pady=10)
tk.Button(main_tab, text="Stop Monitoring", command=stop_monitoring).grid(row=3, column=1, padx=10, pady=10)

tk.Label(main_tab, text="Silence Period Start (YYYY-MM-DD HH:MM:SS):").grid(row=4, column=0, padx=10, pady=10)
silence_start_entry = tk.Entry(main_tab)
silence_start_entry.grid(row=4, column=1, padx=10, pady=10)

tk.Label(main_tab, text="Silence Period End (YYYY-MM-DD HH:MM:SS):").grid(row=5, column=0, padx=10, pady=10)
silence_end_entry = tk.Entry(main_tab)
silence_end_entry.grid(row=5, column=1, padx=10, pady=10)

tk.Button(main_tab, text="Set Silence Period", command=set_silence_period).grid(row=6, column=0, padx=10, pady=10)
tk.Button(main_tab, text="Save Configuration", command=save_config).grid(row=6, column=1, padx=10, pady=10)
tk.Button(main_tab, text="Load Configuration", command=load_config).grid(row=6, column=2, padx=10, pady=10)

status_label = tk.Label(main_tab, text="Status: Not Monitoring")
status_label.grid(row=7, column=0, columnspan=3, padx=10, pady=10)

# Twilio Tab
tk.Label(twilio_tab, text="Account SID:").grid(row=0, column=0, padx=10, pady=10)
account_sid_entry = tk.Entry(twilio_tab)
account_sid_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(twilio_tab, text="Auth Token:").grid(row=1, column=0, padx=10, pady=10)
auth_token_entry = tk.Entry(twilio_tab)
auth_token_entry.grid(row=1, column=1, padx=10, pady=10)

tk.Label(twilio_tab, text="Twilio Number:").grid(row=2, column=0, padx=10, pady=10)
twilio_number_entry = tk.Entry(twilio_tab)
twilio_number_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Label(twilio_tab, text="Recipient Numbers (comma-separated):").grid(row=3, column=0, padx=10, pady=10)
recipient_numbers_entry = tk.Entry(twilio_tab, width=100)
recipient_numbers_entry.grid(row=3, column=1, padx=10, pady=10)

# Mail Tab
mail_check_var = tk.IntVar()
tk.Checkbutton(mail_tab, text="Enable Mail Checking", variable=mail_check_var).grid(row=0, column=0, padx=10, pady=10)

tk.Label(mail_tab, text="Mail Labels (key:value, comma-separated):").grid(row=1, column=0, padx=10, pady=10)
mail_labels_entry = tk.Entry(mail_tab, width=100)
mail_labels_entry.grid(row=1, column=1, padx=10, pady=10)

# Proxy Tab
tk.Label(proxy_tab, text="HTTP Proxy:").grid(row=0, column=0, padx=10, pady=10)
http_proxy_entry = tk.Entry(proxy_tab, width=100)
http_proxy_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(proxy_tab, text="HTTPS Proxy:").grid(row=1, column=0, padx=10, pady=10)
https_proxy_entry = tk.Entry(proxy_tab, width=100)
https_proxy_entry.grid(row=1, column=1, padx=10, pady=10)

root.mainloop()
