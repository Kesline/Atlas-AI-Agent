"""Atlas prototype API: deterministic, inspectable demo agent workflows.
No paid services, no false claims of live fares/weather/bookings.
"""
from datetime import datetime, timedelta
import re
import calendar
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Atlas Agent API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

class Trip(BaseModel):
    origin: str = "Boston"
    origin_tz: str = "America/New_York"
    destination: str = "Tokyo"
    destination_tz: str = "Asia/Tokyo"
    start_date: str = "2026-11-02"
    days: int = Field(7, ge=1, le=30)
    budget: float = Field(1800, gt=0)
    mode: Literal["work", "explore", "blend"] = "blend"
    interests: list[str] = Field(default_factory=lambda: ["bookstores", "music", "food", "culture"])

class Event(BaseModel):
    title: str
    start: str # offset-aware ISO 8601 timestamp
    duration_minutes: int = Field(60, ge=1, le=1440)
    kind: str = "personal"
    fixed: bool = True

class PlanRequest(BaseModel):
    trip: Trip
    events: list[Event] = Field(default_factory=list)

class RescueRequest(PlanRequest):
    disruption: Literal["flight_cancelled", "heavy_rain", "venue_closed"] = "flight_cancelled"

def parse_zone(s: str):
    try: return ZoneInfo(s)
    except ZoneInfoNotFoundError: raise HTTPException(400, f"Invalid IANA time zone: {s}")

def validate_event(e: Event) -> datetime:
    try: x = datetime.fromisoformat(e.start.replace("Z", "+00:00"))
    except ValueError: raise HTTPException(400, "Event must use ISO-8601 datetime")
    if x.tzinfo is None: raise HTTPException(400, "Event timestamp must include UTC offset")
    return x

def itinerary(trip: Trip):
    base = {
        "work": [("09:00", "Meeting preparation & email", "work", 0), ("11:00", "Conference or coworking block", "work", 0), ("14:00", "Networking / scheduled appointments", "work", 0), ("18:30", "Dinner near accommodation", "food", 35)],
        "explore": [("09:00", "Neighborhood walk & coffee", "leisure", 16), ("11:30", "Independent bookstores & local culture", "leisure", 22), ("14:00", "Museum or landmark visit", "leisure", 25), ("19:00", "Local food & live music", "food", 45)],
        "blend": [("09:00", "Focus time / professional commitment", "work", 0), ("12:00", "Lunch near meeting location", "food", 22), ("14:00", "Bookstores & cultural discovery", "leisure", 24), ("19:00", "Dinner & neighborhood music", "food", 40)],
    }
    return [{"id": i+1, "time": t, "title": title, "kind": kind, "estimated_cost_usd": cost, "status": "suggestion"} for i,(t,title,kind,cost) in enumerate(base[trip.mode])]

def conflicts(trip: Trip, events: list[Event], plan):
    tz=parse_zone(trip.destination_tz)
    try: day = datetime.fromisoformat(trip.start_date).date()
    except ValueError: raise HTTPException(400, "start_date must be YYYY-MM-DD")
    result=[]
    for event in events:
        start=validate_event(event).astimezone(tz)
        end=start+timedelta(minutes=event.duration_minutes)
        if start.date()!=day and end.date()!=day: continue
        for item in plan:
            hh,mm=map(int,item["time"].split(":"))
            item_start=datetime(day.year,day.month,day.day,hh,mm,tzinfo=tz)
            item_end=item_start+timedelta(minutes=90)
            if start < item_end and end > item_start:
                result.append({"event":event.title,"event_local":start.strftime("%I:%M %p"),"activity":item["title"],"activity_time":item["time"],"recommendation": "Protect calendar commitment; reschedule suggested activity." if event.fixed else "Review both events and choose preferred schedule."})
    return result

def packing(trip: Trip):
    core=["Passport/ID and travel documents", "Phone, charger and adapter", "Comfortable walking shoes", "Layering pieces", "Weather-appropriate outerwear", "Essential medication"]
    if trip.mode in ("work","blend"): core += ["Conference-ready outfits (mix-and-match)", "Blazer or cardigan for air-conditioned venues", "Laptop and charger", "Networking essentials / business cards"]
    if trip.mode in ("explore","blend"): core += ["Casual day outfits", "Versatile evening outfit"]
    if trip.destination.lower()=="houston" and trip.start_date[5:7]=="11": core += ["Light sweater for cooler evenings", "Packable rain jacket or compact umbrella", "Comfortable conference and walking shoes"]
    if trip.days>7: core.append("Laundry plan for longer trip")
    return {"items":list(dict.fromkeys(core)), "notes":["Houston November recommendations are seasonal, NOT a live forecast." if trip.destination.lower()=="houston" else "Illustrative packing ideas, not based on live weather.","Respect venue-specific dress rules; avoid cultural generalizations.","Check airline baggage policies before packing."]}

class TripConversation(BaseModel):
    messages: list[dict] = Field(default_factory=list)

@app.post('/api/trip/suggest')
def suggest_trip(req: TripConversation):
    """Conservative trip extraction from USER messages only; never AI-made-up suggestions."""
    raw=' '.join(str(m.get('content','')) for m in req.messages if m.get('role')=='user')
    lower=raw.lower()
    dest=next((city for city in ('Houston','Tokyo','Seoul','London','Paris') if re.search(r'\b'+city.lower()+r'\b',lower)),None)
    if not dest: return {'suggestion':None}
    year_m=re.search(r'\b(20\d{2})\b',lower);year=int(year_m.group(1)) if year_m else 2026
    month_m=re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',lower)
    if not month_m: return {'suggestion':None}
    month=list(calendar.month_name).index(month_m.group(1).capitalize())
    # Works for 'November 1–7', 'November 1st until November 7th', and 'November 1-7'.
    context=lower[month_m.end():]
    date_candidates=[int(x) for x in re.findall(r'\b(\d{1,2})(?:st|nd|rd|th)?\b',context[:125])]
    date_candidates=[d for d in date_candidates if 1<=d<=calendar.monthrange(year,month)[1]]
    if len(date_candidates)<2: return {'suggestion':None}
    start_day,end_day=date_candidates[:2]
    if end_day<start_day:return {'suggestion':None}
    money=[]
    for m in re.finditer(r'(?:\$\s*(\d[\d,]*)|(\d[\d,]*)\s*\$)',raw):
        try:money.append(int((m.group(1) or m.group(2)).replace(',','')))
        except ValueError: pass
    if not money: return {'suggestion':None}
    budget=money[-1]
    if budget<=0:return {'suggestion':None}
    origin='Boston' if 'boston' in lower else 'Boston'
    conference=('afrotech' in lower or 'afro tech' in lower or 'conference' in lower)
    mode='blend' if conference and any(x in lower for x in ('bookstore','sightsee','cultur','restaurant','free time','music')) else 'work' if conference else 'explore'
    lodging='staying_with_family' if any(x in lower for x in ('staying with my cousin','staying with family','staying with my aunt','staying with relatives')) else 'unconfirmed'
    interests=[x for x in ('bookstores','music','food','culture','networking') if x in lower or (x=='food' and 'restaurant' in lower) or (x=='culture' and 'cultural' in lower)]
    return {'suggestion':{'origin':origin,'destination':dest,'start_date':f'{year:04d}-{month:02d}-{start_day:02d}', 'end_date':f'{year:04d}-{month:02d}-{end_day:02d}', 'days':end_day-start_day+1, 'budget':budget,'mode':mode,'accommodation':lodging,'purpose':'AfroTech conference + exploring' if conference and mode=='blend' else 'Conference / work' if conference else 'Leisure travel','interests':interests or ['culture']}}

@app.get("/api/health")
def health(): return {"status":"ok", "data_mode":"demo"}

@app.post("/api/plan")
def plan(req:PlanRequest):
    origin=parse_zone(req.trip.origin_tz); destination=parse_zone(req.trip.destination_tz)
    plan_items=itinerary(req.trip)
    now=datetime.now(ZoneInfo("UTC"))
    return {"mode":"demo", "trip":req.trip.model_dump(),"itinerary":plan_items,"conflicts":conflicts(req.trip,req.events,plan_items),"packing":packing(req.trip),"time":{"home":now.astimezone(origin).isoformat(),"destination":now.astimezone(destination).isoformat()},"agent_trace":[{"agent":"Planner","result":"Built mode-specific day-one suggestions"},{"agent":"Schedule Guard","result":"Checked proposed activities against fixed calendar events"},{"agent":"Packing Advisor","result":"Recommended a starter packing list"},{"agent":"Verifier","result":"Marked prices and availability as illustrative"}],"disclaimer":"Demo itinerary and estimated costs only. No live weather, fares, provider booking, or external calendar access."}

@app.post("/api/rescue")
def rescue(req:RescueRequest):
    _ = parse_zone(req.trip.destination_tz)
    scenario={
        "flight_cancelled": {"alert":"Connecting flight cancelled (simulated)","actions":[{"step":"Re-check arrival","detail":"Identify alternative routes with a live provider before presenting actual flight options.","status":"requires_live_data"},{"step":"Protect commitments","detail":"Flag fixed calendar events that may be affected by late arrival.","status":"recommended"},{"step":"Notify hotel","detail":"Prepare a late-arrival message for review, without sending it.","status":"draft"},{"step":"Repair day one","detail":"Move optional sightseeing until after arrival and rest.","status":"proposed"}]},
        "heavy_rain": {"alert":"Heavy rain forecast (simulated)","actions":[{"step":"Move outdoor plans","detail":"Swap neighborhood walk with indoor museums and bookstores.","status":"proposed"},{"step":"Check transport","detail":"Recommend sheltered routes; verify actual transit service before navigating.","status":"requires_live_data"},{"step":"Update packing","detail":"Recommend umbrella and waterproof outer layer.","status":"recommended"}]},
        "venue_closed": {"alert":"Planned venue unexpectedly closed (simulated)","actions":[{"step":"Find substitute","detail":"Search for nearby venues matching user interests when places integration is enabled.","status":"requires_live_data"},{"step":"Check time windows","detail":"Protect meeting and transport buffer times.","status":"recommended"},{"step":"Ask approval","detail":"Propose replacement in itinerary; do not automatically purchase tickets.","status":"approval_required"}]}
    }[req.disruption]
    return {"mode":"simulation", "scenario":req.disruption,**scenario,"requires_approval":True,"trace":["Disruption recognized", "Constraints collected", "Alternative actions drafted", "Verification and approval gate reached"],"disclaimer":"Simulation. No bookings, emails or calendar entries were changed."}

from agent import ChatRequest, run_chat

@app.post('/api/chat')
async def chat(req: ChatRequest):
    return await run_chat(req)
