from flask import Flask, jsonify, request
from utils.monitor import monitor_endpoints
from utils.outlook import check_outlook_inbox
from twilio.rest import Client
import os

app = Flask(__name__)

# Load configurations
app.config.from_object('config.Config')

# Twilio client
client = Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])

@app.route('/monitor', methods=['POST'])
def monitor():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    result = monitor_endpoints(url)
    return jsonify(result)

@app.route('/outlook_check', methods=['POST'])
def outlook_check():
    label = request.json.get('label')
    result = check_outlook_inbox(label)
    if result:
        # Trigger Twilio alert
        message = client.messages.create(
            to=app.config['ALERT_PHONE_NUMBER'],
            from_=app.config['TWILIO_PHONE_NUMBER'],
            body=f'Alert: Label {label} found in Outlook inbox'
        )
        return jsonify({"status": "Alert sent", "message_sid": message.sid})
    return jsonify({"status": "No matching label found"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
