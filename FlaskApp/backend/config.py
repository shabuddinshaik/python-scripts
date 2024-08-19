import os

class Config:
    # Twilio configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_twilio_account_sid')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_twilio_auth_token')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', 'your_twilio_phone_number')
    ALERT_PHONE_NUMBER = os.getenv('ALERT_PHONE_NUMBER', 'your_alert_phone_number')
    
    # Outlook configuration
    OUTLOOK_USERNAME = os.getenv('OUTLOOK_USERNAME', 'your_outlook_username')
    OUTLOOK_PASSWORD = os.getenv('OUTLOOK_PASSWORD', 'your_outlook_password')
