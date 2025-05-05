import os
import random
import string
from flask import Flask, request, redirect, send_from_directory, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

app = Flask(__name__, static_folder='public')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = 'credentials.json'

flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
)


@app.route('/auth/google')
def auth_google():
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return redirect(auth_url)


@app.route('/oauth2callback')
def oauth2callback():
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    refresh_token = credentials.refresh_token

    return f'''
    <html>
        <head><title>Google OAuth Successful</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>✅ Authentication Successful</h2>
            <p><strong>Copy your refresh token below and keep it secure:</strong></p>
            <textarea rows="5" cols="100" readonly>{refresh_token}</textarea>
            <p style="color: red;"><strong>Note:</strong> Do not share this token. It provides long-term access to your Google Calendar.</p>
        </body>
    </html>
    '''


@app.route('/create-meeting', methods=['POST'])
def create_meeting():
    data = request.json
    summary = data.get('summary')
    description = data.get('description')
    start_time = data.get('startTime')
    end_time = data.get('endTime')
    attendee_email = data.get('attendeeEmail')

    try:
        creds = Credentials(
            None,
            refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )

        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_time, 'timeZone': 'Asia/Kolkata'},
            'attendees': [{'email': attendee_email}],
            'conferenceData': {
                'createRequest': {
                    'requestId': ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }

        response = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()

        meeting_link = response.get('hangoutLink')

        # Send Email
        send_email(summary, description, start_time, end_time, attendee_email, meeting_link)

        return {'success': True, 'meetingLink': meeting_link}
    except Exception as e:
        print("Error:", str(e))
        return {'success': False, 'error': str(e)}, 500


def send_email(summary, description, start_time, end_time, to_email, meeting_link):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Meeting Invitation: {summary}"
    msg['From'] = os.getenv("ZOHO_USER")
    msg['To'] = to_email

    start_fmt = datetime.fromisoformat(start_time).astimezone(pytz.timezone('Asia/Kolkata')).strftime('%c')
    end_fmt = datetime.fromisoformat(end_time).astimezone(pytz.timezone('Asia/Kolkata')).strftime('%c')

    html_body = render_template('invitation_email.html',
                                summary=summary,
                                description=description,
                                start=start_fmt,
                                end=end_fmt,
                                meeting_link=meeting_link,
                                logo_url=f"https://{request.host}/logo-hynux.png")

    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP('smtp.zoho.in', 587) as server:
        server.starttls()
        server.login(os.getenv("ZOHO_USER"), os.getenv("ZOHO_PASS"))
        server.send_message(msg)

@app.route("/health")
def health():
    return "OK", 200

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    print("🚀 Flask app is starting on port 8080...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
