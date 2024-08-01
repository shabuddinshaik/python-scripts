import os
import time
import logging
import requests
from twilio.rest import Client
from logging.handlers import TimedRotatingFileHandler
from configparser import ConfigParser

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[TimedRotatingFileHandler('url_monitor.log', when='midnight', interval=1, backupCount=7)])

# Twilio configuration
twilio_config_file = 'twilio_config.ini'
config = ConfigParser()
config.read(twilio_config_file)

TWILIO_ACCOUNT_SID = config.get('twilio', 'account_sid')
TWILIO_AUTH_TOKEN = config.get('twilio', 'auth_token')
TWILIO_FROM_NUMBER = config.get('twilio', 'from_number')
TO_NUMBERS = config.get('twilio', 'to_numbers').split(',')

# Function to check URL status
def check_url(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True, f"URL '{url}' is reachable."
        else:
            return False, f"URL '{url}' returned status code {response.status_code}."
    except requests.exceptions.RequestException as e:
        return False, f"Failed to reach URL '{url}': {str(e)}"

# Function to send SMS using Twilio
def send_twilio_sms(message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for number in TO_NUMBERS:
            message = client.messages.create(body=message, from_=TWILIO_FROM_NUMBER, to=number)
            logging.info(f"SMS sent to {number} with SID {message.sid}.")
    except Exception as e:
        logging.error(f"Failed to send SMS: {str(e)}")

# Main function to run monitoring
def monitor_urls(urls):
    try:
        while True:
            for url in urls:
                status, message = check_url(url)
                if status:
                    logging.info(message)
                else:
                    logging.error(message)
                    send_twilio_sms(message)
            time.sleep(180)  # 3 minutes interval
    except KeyboardInterrupt:
        logging.info("URL monitoring stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")

# Function to prompt and update configuration
def update_configuration():
    try:
        config = ConfigParser()
        config['twilio'] = {
            'account_sid': input("Enter Twilio Account SID: "),
            'auth_token': input("Enter Twilio Auth Token: "),
            'from_number': input("Enter Twilio From Number: "),
            'to_numbers': input("Enter Twilio To Numbers (comma-separated): ")
        }
        with open(twilio_config_file, 'w') as configfile:
            config.write(configfile)
        logging.info("Twilio configuration updated successfully.")
    except Exception as e:
        logging.error(f"Failed to update Twilio configuration: {str(e)}")

if __name__ == "__main__":
    try:
        urls = []
        while True:
            url = input("Enter URL to monitor (or 'done' to finish): ")
            if url.lower() == 'done':
                break
            urls.append(url.strip())
        
        if not urls:
            logging.warning("No URLs provided. Exiting...")
            exit()

        update_configuration()

        monitor_urls(urls)

    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {str(e)}")
