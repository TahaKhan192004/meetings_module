from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

flow = InstalledAppFlow.from_client_secrets_file(
    'smart_cred.json',
    SCOPES
)

creds = flow.run_local_server(port=800)

print("REFRESH TOKEN:", creds.refresh_token)