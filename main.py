from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta, time
from services.google_calendar import get_busy_slots, create_event
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, WORK_START_HOUR, WORK_END_HOUR
import httpx
from config import MAKE_WEBHOOK_URL

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
def book_meeting(client_name: str, client_email: str, start: str, end: str):
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    try:
        meet_link, event_id = create_event(client_name, client_email, start_dt, end_dt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    #Store in Supabase
    supabase.table("meetings").insert({
        "client_name": client_name,
        "client_email": client_email,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "google_event_id": event_id,
        "meet_link": meet_link,
        "status": "upcoming"
    }).execute()

    try:
        httpx.post(MAKE_WEBHOOK_URL, json={
            "client_name": client_name,
            "client_email": client_email,
            "meet_link": meet_link,
            "start_time": start_dt.strftime("%B %d, %Y at %I:%M %p"),
            "end_time": end_dt.strftime("%I:%M %p")
        }, timeout=10)
    except Exception:
        pass  # Don't fail the booking if webhook fails
    
    return {"meet_link": meet_link}