from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta, time
from services.google_calendar import get_busy_slots, create_event
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, WORK_START_HOUR, WORK_END_HOUR
import httpx
from config import MAKE_WEBHOOK_URL
from services.gemini_context import generate_meeting_context

# inside book_meeting(), after supabase insert:
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="Client Booking Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def home():
    return {"message": "Client booking service running!"}

@app.get("/calendar/month")
def get_month(year: int, month: int):
    start = datetime(year, month, 1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    busy_slots = get_busy_slots(start, end)
    return {"busy_slots": busy_slots}

@app.get("/calendar/available")
def get_available(day: str):
    """
    day: YYYY-MM-DD
    """
    date_obj = datetime.fromisoformat(day)
    start_day = datetime.combine(date_obj.date(), time(WORK_START_HOUR, 0))
    end_day = datetime.combine(date_obj.date(), time(WORK_END_HOUR, 0))

    # Busy slots from Google Calendar
    busy = get_busy_slots(start_day, end_day)

    # Busy slots from Supabase (catches bookings not yet synced to Google)
    result = supabase.table("meetings") \
        .select("start_time, end_time") \
        .gte("start_time", start_day.isoformat()) \
        .lte("start_time", end_day.isoformat()) \
        .execute()

    for row in result.data:
        busy.append({
            "start": row["start_time"],
            "end": row["end_time"]
        })

    # Generate 30-min slots
    slots = []
    slot_start = start_day
    while slot_start + timedelta(minutes=30) <= end_day:
        slot_end = slot_start + timedelta(minutes=30)
        overlap = any(
            datetime.fromisoformat(b['start'].replace("Z", "")).replace(tzinfo=None) < slot_end and
            datetime.fromisoformat(b['end'].replace("Z", "")).replace(tzinfo=None) > slot_start
            for b in busy
        )
        if not overlap:
            slots.append({"start": slot_start.isoformat(), "end": slot_end.isoformat()})
        slot_start += timedelta(minutes=30)

    return {"available_slots": slots}

@app.post("/calendar/book")
def book_meeting(client_name: str, client_email: str, start: str, end: str, purpose: str, user_input: str = ""):
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    # Generate AI context if user provided input
    extra_context = ""
    if user_input.strip():
        extra_context = generate_meeting_context(purpose, user_input)

    try:
        meet_link, event_id = create_event(client_name, client_email, start_dt, end_dt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    supabase.table("meetings").insert({
        "client_name": client_name,
        "client_email": client_email,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "google_event_id": event_id,
        "meet_link": meet_link,
        "status": "upcoming",
        "purpose": purpose,
        "extra_context": extra_context
    }).execute()

    try:
        httpx.post(MAKE_WEBHOOK_URL, json={
            "client_name": client_name,
            "client_email": client_email,
            "meet_link": meet_link,
            "start_time": start_dt.strftime("%B %d, %Y at %I:%M %p"),
            "end_time": end_dt.strftime("%I:%M %p"),
        }, timeout=10)
    except Exception:
        pass

    return {"meet_link": meet_link}



@app.post("/meeting/generate-context")
def generate_context(purpose: str, user_input: str):
    try:
        result = generate_meeting_context(purpose, user_input)
        return {"context": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/meetings/todays-reminder")
def get_todays_meetings():
    today = datetime.now().date()
    start = datetime.combine(today, time(0, 0, 0)).isoformat()
    end = datetime.combine(today, time(23, 59, 59)).isoformat()

    result = supabase.table("meetings") \
        .select("client_name, client_email, meet_link, start_time, end_time") \
        .gte("start_time", start) \
        .lte("start_time", end) \
        .eq("status", "upcoming") \
        .execute()

    meetings = []
    for row in result.data:
        start_dt = datetime.fromisoformat(row["start_time"].replace("Z", ""))
        end_dt = datetime.fromisoformat(row["end_time"].replace("Z", ""))
        meetings.append({
            "client_name": row["client_name"],
            "client_email": row["client_email"],
            "meet_link": row["meet_link"],
            "start_time": start_dt.strftime("%B %d, %Y at %I:%M %p"),
            "end_time": end_dt.strftime("%I:%M %p")
        })

    return {"meetings": meetings}