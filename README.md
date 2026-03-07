# Meetings Module — Backend

A FastAPI-based meeting booking service that integrates Google Calendar, Supabase, Google Gemini AI, and Make.com webhooks to provide a fully automated client scheduling system.

---

## Features

- **Google Calendar Integration** — checks real-time availability and creates Google Meet events automatically
- **Supabase Storage** — stores all meeting records with client info, status, and AI-generated context
- **Gemini AI Context Generation** — generates structured meeting preparation notes based on the meeting purpose
- **Make.com Webhooks** — triggers confirmation and reminder emails automatically
- **Conflict Prevention** — cross-checks both Google Calendar and Supabase to prevent double bookings
- **Admin Endpoints** — fetch all meetings, update status, and send manual reminders

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Server | Uvicorn |
| Calendar | Google Calendar API v3 |
| Database | Supabase (PostgreSQL) |
| AI | Google Gemini 1.5 Flash |
| Email Automation | Make.com Webhooks |
| HTTP Client | HTTPX |
| Auth | Google OAuth2 Refresh Token |

---

## Project Structure

```
meetings_module/
├── main.py                        # FastAPI app and all endpoints
├── config.py                      # Environment variable loading
├── services/
│   ├── google_calendar.py         # Google Calendar API integration
│   └── gemini_context.py          # Gemini AI context generation
├── creds.json                     # Google OAuth credentials (never commit)
├── .env                           # Environment variables (never commit)
├── requirements.txt
└── README.md
```

---

## Environment Variables

Create a `.env` file in the root directory:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
MAKE_WEBHOOK_URL=https://hook.eu2.make.com/your-webhook-id
GEMINI_API_KEY=your_gemini_api_key
```

---

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable the **Google Calendar API**
3. Create an **OAuth 2.0 Client ID** of type **Desktop App**
4. Download the credentials as `creds.json`
5. Run the following script to generate your refresh token:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']
flow = InstalledAppFlow.from_client_secrets_file('creds.json', SCOPES)
creds = flow.run_local_server(port=8080)
print("REFRESH TOKEN:", creds.refresh_token)
```

6. Paste the refresh token into your `.env`
7. In Google Cloud Console, set the OAuth consent screen to **Production** to prevent token expiry

---

## Supabase Table Setup

Run this SQL in your Supabase SQL Editor:

```sql
CREATE TABLE meetings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_name TEXT NOT NULL,
    client_email TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    google_event_id TEXT UNIQUE,
    meet_link TEXT,
    status TEXT DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'completed', 'canceled')),
    purpose TEXT,
    extra_context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/meetings_module.git
cd meetings_module

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env and creds.json (see above)

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

API docs available at: `http://localhost:8001/docs`

---

## API Endpoints

### Calendar

#### `GET /calendar/available`
Returns available 30-minute slots for a given day. Cross-checks Google Calendar and Supabase to prevent double bookings.

**Query Parameters:**
| Parameter | Type | Example |
|---|---|---|
| day | string | `2026-03-10` |

**Response:**
```json
{
  "available_slots": [
    { "start": "2026-03-10T09:00:00", "end": "2026-03-10T09:30:00" },
    { "start": "2026-03-10T10:00:00", "end": "2026-03-10T10:30:00" }
  ]
}
```

---

#### `GET /calendar/month`
Returns all busy slots for a given month from Google Calendar.

**Query Parameters:**
| Parameter | Type | Example |
|---|---|---|
| year | int | `2026` |
| month | int | `3` |

---

#### `POST /calendar/book`
Books a meeting, creates a Google Meet event, runs Gemini AI context generation, stores in Supabase, and triggers the confirmation email webhook.

**Query Parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| client_name | string | Yes | Full name of the client |
| client_email | string | Yes | Email address |
| start | string | Yes | ISO datetime e.g. `2026-03-10T10:00:00` |
| end | string | Yes | ISO datetime e.g. `2026-03-10T10:30:00` |
| purpose | string | Yes | One of the 6 meeting purposes |
| user_input | string | No | Raw context — Gemini expands this into structured notes |

**Response:**
```json
{
  "meet_link": "https://meet.google.com/abc-defg-hij"
}
```

---

### Meetings Admin

#### `GET /meetings/getAll`
Returns all meetings from Supabase.

**Response:**
```json
{
  "meetings": [
    {
      "id": "uuid",
      "client_name": "John Smith",
      "client_email": "john@example.com",
      "start_time": "2026-03-10T10:00:00+00:00",
      "end_time": "2026-03-10T10:30:00+00:00",
      "google_event_id": "abc123",
      "meet_link": "https://meet.google.com/abc-defg-hij",
      "status": "upcoming",
      "purpose": "Client Consultation",
      "extra_context": "## Project Overview\n..."
    }
  ]
}
```

---

#### `POST /meetings/updateStatus`
Updates the status of a meeting.

**Query Parameters:**
| Parameter | Type | Values |
|---|---|---|
| event_id | string | Google Calendar event ID |
| status | string | `upcoming`, `completed`, `canceled` |

---

#### `POST /meetings/sendReminder`
Manually triggers a reminder email for a specific meeting via Make.com webhook.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| event_id | string | Google Calendar event ID |

---

#### `GET /meetings/todays-reminder`
Returns all upcoming meetings scheduled for today. Used by Make.com scheduled trigger to send 9 PM reminders.

---

## Gemini AI Context Generation

When a client provides `user_input` during booking, the backend calls Gemini with a purpose-specific prompt and stores the structured markdown output as `extra_context`.

| Purpose | Generated Output |
|---|---|
| Client Consultation | Project Overview, Key Requirements, Questions to Ask, Suggested Approach |
| Technical Interview | Position Summary, Required Skills, Technical Questions, Evaluation Criteria |
| Sales Demo | Value Propositions, Pain Points, Talking Points, Objection Handling |
| Support Call | Problem Summary, Root Causes, Diagnostic Questions, Suggested Solutions |
| HR Interview | Raw input stored as-is |
| General Discussion | Raw input stored as-is |

---

## Make.com Webhook Setup

Two scenarios are required in Make.com:

**Scenario 1 — Booking Confirmation**
- Trigger: Custom Webhook (instant)
- Action: Send email with meet link, date, time, and purpose

**Scenario 2 — Daily Reminder**
- Trigger: Schedule — every day at 9:00 PM (Asia/Karachi)
- Action: HTTP GET → `http://your-ec2-ip:8001/meetings/todays-reminder` → Iterator → Send reminder email to each meeting

Webhook payload fields: `client_name`, `client_email`, `meet_link`, `start_time`, `end_time`, `purpose`, `extra_context`

---

## Production Deployment (EC2)

### Run as a systemd service

```bash
sudo nano /etc/systemd/system/meetings.service
```

```ini
[Unit]
Description=Meetings Module FastAPI
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/meetings_module
Environment="PATH=/home/ubuntu/meetings_module/venv/bin"
EnvironmentFile=/home/ubuntu/meetings_module/.env
ExecStart=/home/ubuntu/meetings_module/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable meetings
sudo systemctl start meetings
sudo systemctl status meetings
```

### CORS Configuration

Add this to `main.py` before defining routes:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-vercel-app.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Working Hours

Configured in `config.py`:

```python
TIMEZONE = "Asia/Karachi"
WORK_START_HOUR = 9    # 9:00 AM
WORK_END_HOUR = 18     # 6:00 PM
```

Weekends are automatically excluded. Slots are generated in 30-minute intervals.

---

## Security Notes

- Never commit `.env` or `creds.json` to version control
- Add both to `.gitignore` immediately
- If accidentally pushed, regenerate all credentials from Google Cloud Console
- The admin panel uses a fixed password — consider upgrading to JWT auth for production
