# STEP 4: FastAPI Backend & Next.js Dashboard

## What This Step Builds

Steps 1–3 built the full GHOST monitoring engine: database, scoring, classification, recovery, and the interceptor. But all output was in the terminal. Step 4 makes everything **visible in a browser** — a real-time dashboard that shows agent sessions, trajectory adherence charts, failure alerts, and recovery timelines.

---

## The FastAPI Backend

The backend is a lightweight REST API that reads from the same SQLite database that GHOST writes to. It exposes 5 endpoints:

| Endpoint | What It Returns |
|---|---|
| `GET /api/health` | Server status and version |
| `GET /api/stats` | Aggregate statistics (total sessions, success rate, failure breakdown) |
| `GET /api/sessions` | Last 100 sessions, most recent first |
| `GET /api/sessions/{id}` | Full session detail including every tool call step |
| `GET /api/sessions/{id}/trajectory` | Adherence score time series for the chart |

### Why FastAPI?

FastAPI is the fastest Python API framework, with automatic OpenAPI docs, type validation via Pydantic, and async support. Since GHOST's core is Python, keeping the backend in Python means zero serialization overhead — it reads the same SQLite file directly.

---

## The Dashboard Components

### StatsHeader (4 cards at top)
Shows aggregate health metrics at a glance:
- **Total Sessions** — how many agent runs GHOST has monitored
- **Failures Detected** — total failure events across all sessions
- **Recoveries Triggered** — how many times GHOST intervened
- **Success Rate** — percentage of sessions that completed without issues

### SessionTable (left column)
A clickable table of all monitored sessions. Each row shows:
- Session ID, task type, step count, recovery count, adherence score, status
- Color-coded adherence: green (≥0.7), amber (0.4–0.7), red (<0.4)
- Status badges: running (blue), completed (green), failed (red)
- Click a row to load its details in the right column

### AdherenceChart (right column, top)
A Recharts line chart showing the adherence score over time for the selected session:
- X axis = step number, Y axis = adherence score (0 to 1)
- Red dashed line at y=0.4 shows the drift threshold
- Red dots mark steps where failures were detected
- Amber vertical lines mark recovery interventions
- This is the single most important visualization — it shows GHOST's value

### FailureAlert (right column, middle)
Shows failure events for the selected session:
- Green banner if no failures detected
- Red alert box with failure count if failures exist
- Timeline cards showing step number, failure type, recovery strategy

### RecoveryLog (right column, bottom)
Shows recovery interventions as a vertical timeline:
- Strategy name in amber, failure type that triggered it
- Adherence score before and after recovery

---

## How the Dashboard Makes GHOST's Value Visible

Without the dashboard, GHOST's monitoring is invisible — terminal logs scroll by and disappear. The adherence chart makes the value **undeniable**:

1. **A healthy session** shows a green line staying above 0.4 → the agent stayed on track
2. **A drift event** shows the line dropping below the red threshold → GHOST detected the problem
3. **A recovery** shows the line recovering after an amber intervention marker → GHOST fixed it
4. **A failed session** shows a line that drops and never recovers → evidence that the agent needs help

This is the visualization you show in demos, papers, and on Hacker News.

---

## Files Created in This Step

| File | Purpose |
|---|---|
| `api/__init__.py` | Package marker |
| `api/main.py` | FastAPI application with CORS, startup/shutdown, router includes |
| `api/routes/__init__.py` | Package marker |
| `api/routes/sessions.py` | Session list, detail, and trajectory endpoints |
| `api/routes/stats.py` | Aggregate statistics endpoint |
| `dashboard/` | Next.js application (created via create-next-app) |
| `dashboard/app/globals.css` | Dark theme styles |
| `dashboard/app/layout.tsx` | Root layout with Inter font |
| `dashboard/app/page.tsx` | Main page with two-column layout |
| `dashboard/app/components/StatsHeader.tsx` | 4 stat cards |
| `dashboard/app/components/SessionTable.tsx` | Clickable session table |
| `dashboard/app/components/AdherenceChart.tsx` | Recharts trajectory line chart |
| `dashboard/app/components/FailureAlert.tsx` | Failure event alerts |
| `dashboard/app/components/RecoveryLog.tsx` | Recovery intervention timeline |
| `dashboard/next.config.ts` | API proxy rewrites to FastAPI |

---

## How to Start Everything

### Terminal 1 — Start FastAPI Backend
```bash
uvicorn api.main:app --reload --port 8000
```
Confirm:
- http://localhost:8000/api/health → `{"status": "ok", "version": "0.1.0"}`
- http://localhost:8000/api/stats → JSON with stats (may be zeros initially)

### Terminal 2 — Start Next.js Dashboard
```bash
cd dashboard
npm run dev
```
Open http://localhost:3000

### Terminal 3 — Generate Data
```bash
python examples/demo_simple.py
```
Then refresh the dashboard. You should see:
- A session appear in the table
- Click it → adherence chart shows a green line
- Stat cards update with real numbers

---

## Verification Checklist

- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `GET /api/stats` returns JSON with `total_sessions`
- [ ] `GET /api/sessions` returns a list (empty or with sessions)
- [ ] Dashboard loads at http://localhost:3000 with dark theme
- [ ] 4 stat cards appear at the top
- [ ] Session table renders (empty is OK before running demo)
- [ ] After running demo_simple.py, session appears in table
- [ ] Clicking session shows adherence chart with line
- [ ] Failures and recoveries appear if they occurred

---

✅ Step 4 complete. Dashboard and API working.
📖 Read STEP4_README.md to understand what was built.
➡️  Next: paste the Step 5 prompt (benchmarks + final README).
