from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, SCOPES, TIMEZONE

def get_credentials():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )
    creds.refresh(Request())
    return creds

def get_busy_slots(start, end):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    body = {
        "timeMin": start.isoformat() + "Z",
        "timeMax": end.isoformat() + "Z",
        "timeZone": TIMEZONE,
        "items": [{"id": "primary"}]
    }

    freebusy = service.freebusy().query(body=body).execute()
    return freebusy['calendars']['primary']['busy']

def create_event(client_name, client_email, start, end):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": f"Meeting with {client_name}",
        "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        "attendees": [{"email": client_email}] if client_email else [],
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{start.timestamp()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1
    ).execute()

    return created_event.get("hangoutLink"), created_event.get("id")