
import os
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = Flask(__name__)
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
channel_id = os.environ['SLACK_CHANNEL_ID']

# In-memory store for weekly totals
weekly_totals = {}

def get_current_week():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())  # Monday
    return start.strftime('%Y-%m-%d')

def extract_amount(text):
    match = re.search(r'\$([0-9]+(?:\.[0-9]{2})?)', text)
    if match:
        return float(match.group(1))
    return None

def update_total(user, amount):
    week = get_current_week()
    if week not in weekly_totals:
        weekly_totals[week] = 0.0
    weekly_totals[week] += amount
    return weekly_totals[week]

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.get_json()
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data['challenge']})
    
    if 'event' in data:
        event = data['event']
        if event.get('type') == 'message' and 'bot_id' not in event:
            text = event.get('text', '')
            amount = extract_amount(text)
            if amount:
                total = update_total(event['user'], amount)
                try:
                    client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=event['ts'],
                        text=f"New total for this week: ${total:.2f}"
                    )
                except SlackApiError as e:
                    print(f"Error posting message: {e.response['error']}")
    
    return '', 200

@app.route('/weekly_summary', methods=['GET'])
def weekly_summary():
    week = get_current_week()
    total = weekly_totals.get(week, 0.0)
    try:
        client.chat_postMessage(
            channel=channel_id,
            text=f"<@yourbossid> Karen's reimbursement total this week is: ${total:.2f}"
        )
    except SlackApiError as e:
        return f"Error: {e.response['error']}", 500
    return "Summary sent", 200

if __name__ == '__main__':
    app.run(port=3000)
