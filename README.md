# ATLAS — Your Journey, Handled

An interactive hackathon MVP for an **agentic travel companion** with Work, Explore and Blend modes, live home/destination clocks, local calendar entry and conflict detection, packing guidance, and three simulated Trip Rescue workflows.

## Quick start

Requires **Python 3.10+** and **Node.js 20+**.

**Terminal 1: backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend health check: http://127.0.0.1:8000/api/health

**Terminal 2: frontend**

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

## 3-minute judge demo
1. In Overview, choose **Tokyo**, **Blend**, and generate a day-one itinerary. Show both live clocks.
2. Open My Calendar. The sample Zoom meeting is entered in Boston time. Generate plan and show local-time collision warnings on the November 2, 2026 itinerary.
3. Open Style & Pack, generate packing suggestions, and tick items off.
4. Open Trip Rescue, select Flight Cancelled, and show the agent's staged recovery plan and approval gate.
5. Switch to Heavy Rain and show that the proposed recovery approach changes.

## What is real vs simulated?

**Real in this MVP:** local-time-zone clocks via `Intl.DateTimeFormat`, API-based mode-dependent plan assembly, IANA time zone conversion in Python, offset-aware conflict detection, editable session calendar events, an interactive packing checklist, and explicit rescue decision traces.

**Simulated / NOT connected:** flight inventory or bookings, real weather forecasts, place opening hours, tickets, actual email or calendar account syncing, hotel communication, payments, cultural guidance, user wardrobe photos. The demo labels these boundaries deliberately.

### Architecture

- `frontend/`: React + TypeScript + Vite; no API keys necessary.
- `backend/`: FastAPI; bounded, transparent agent roles represented by an orchestration pipeline.
- `POST /api/plan`: planner, schedule guard, packing advisor, verifier.
- `POST /api/rescue`: disruption-specific response preparation and human approval gate.

This is a strong *foundation*, **not yet an autonomous LLM agent**. Next milestone: connect a real tool-calling LLM orchestrator with verified tools, retrieval traces, and evaluation tests. Do not claim this demo places bookings or monitors external services.

## Roadmap

1. **Reliability:** tests for time zones, DST, cross-midnight meetings, invalid input, budgets, and rescue approval safeguards.
2. **Calendar OAuth:** Google Calendar read-only; Microsoft Graph next. Support full-detail vs busy-only views, account revocation, and explicit consent for writes.
3. **Verified data:** weather provider; places/maps with citations/attribution; flight inventory via approved provider.
4. **Agentic loop:** LangGraph or comparable orchestrator, safe structured tool outputs, bounded planning budget, audit log and explicit human approval for purchases and messages.
5. **Style & Pack:** forecast-based items, venue-specific verified dress requirements, optional private digital closet, suitcase weight limits.
6. **Evaluation:** test 20 disruptions; track accurate recovery plans, conflicts caught, unsupported claims, approvals enforced, and response latency.
7. **Security:** OAuth tokens server-side, least privilege, encryption, retention controls, abuse/rate limits.

## Names / branding

Atlas is a working project name. Search trademarks and domains before launching commercially.

## NEW: Real conversational AI with OpenRouter + SerpAPI

The **Atlas AI Chat** section provides real back-and-forth multi-turn messages. The frontend submits the last 24 messages and current trip/calendar context to the backend. The OpenRouter model may invoke bounded tools up to four iterations per turn:

- `search_travel_web` (optional SerpAPI Google search; snippets + URLs)
- `get_local_time` (real IANA local time)
- `check_calendar` (events entered locally in prototype, not Google account syncing)
- `draft_trip_plan` (existing deterministic itinerary, schedule conflicts, packing)
- `simulate_trip_rescue` (explicitly simulated flight, weather, venue disruption)

### Configure credentials (backend only)

```bash
cd backend
cp .env.example .env
# Edit .env with your own OPENROUTER_API_KEY and SERPAPI_KEY
# Select an OpenRouter model that SUPPORTS TOOL CALLING
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open the Vite frontend and select **Atlas AI Chat** in the sidebar.

**Never put keys in frontend TypeScript, VITE_* environment variables, GitHub, or screenshots.** `.env` is ignored by the repository; rotate any leaked keys. Requests are sent to the selected OpenRouter model provider, and web queries (if enabled) go to SerpAPI. No user database is included; conversation state is held in the browser session. No payments, bookings, or external changes occur. The tool loop is bounded to protect cost and latency. Model usage and SerpAPI searches may incur charges. Set provider spending limits.

### Example live-agent prompts

- “I am attending a conference in Houston November 2–6. Ask me the most important questions first.”
- “Search current information on local bookstores and cite your links.”
- “How does my 10 AM Boston Zoom meeting appear in Tokyo time? Check the calendar.”
- “Help me pack for a conference and sightseeing in Seoul; search for seasonal weather guidance.”
- “My connecting flight is cancelled. Walk me through a recovery plan, but don't book anything.”

### Troubleshooting

- **503 from `/api/chat`** — missing `OPENROUTER_API_KEY` in `backend/.env`, or backend not restarted.
- **502 from `/api/chat`** — selected model doesn't support tools, invalid key, provider unavailable, or insufficient credits; inspect backend error message. Change `OPENROUTER_MODEL` to a tool-capable model.
- **Search unavailable** — add `SERPAPI_KEY`; chat still works without it.
- **UI says API error** — start the backend at port 8000, frontend at port 5173.

### Next steps

Chat currently retains context within the open application; persisted conversations, Google/Outlook calendar OAuth, event writing, hotel/flight booking, weather forecast feeds, and streaming chat are future work, not currently connected. Before a public deployment add authenticated user accounts, server-side rate limits, per-user cost controls, data retention controls and streaming support.


## Sync an existing trip conversation

1. Go to **Atlas AI Chat** and click **Sync trip from this chat**. The app reads user messages, not AI-generated prices.
2. Inspect the proposed destination, dates, and budget. Click **Confirm & update my journey**.
3. Overview displays the confirmed trip and budget; clicking Generate refreshes the illustrative itinerary.
4. Chat messages and the confirmed trip persist in this browser's localStorage (not server-side), so do not use a private window if you want them to persist.

If your old Overview still displays $1,800, the demo budget hasn't been replaced by a confirmed $2,000 trip. Use the sync button and confirm. No real calendar integration or live price verification is included.
