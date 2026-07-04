# STEP 1: Foundation — Database, Memory, and Project Skeleton

## What is GHOST?

**GHOST (General-purpose Healing & Oversight System for Tasks)** is an open-source middleware layer that wraps any LangChain or LangGraph AI agent to make it failure-aware, self-correcting, and fully observable in real time. It sits between your agent and its tools, intercepting every action to detect failures, trigger recovery strategies, and log full execution trajectories. Think of it as a flight recorder + autopilot for AI agents — it watches everything, remembers past failures, and intervenes when things go wrong.

---

## What Step 1 Builds

Step 1 creates the **foundation** that every other step depends on. No agent wrapping happens here — instead, we set up the data layer (SQLite + ChromaDB) and the project skeleton so that Steps 2–6 have a clean, typed, tested base to build on.

After completing Step 1, you should have:
- A working SQLite database with all required tables
- A working ChromaDB vector store for failure memory
- A complete project folder structure ready for future steps
- A passing verification script that proves everything works

---

## Files Created in This Step

| File | Purpose |
|------|---------|
| `STEP1_README.md` | This file. Explains what Step 1 does and how to verify it. |
| `ghost/core/.gitkeep` | Placeholder for core logic (agent wrapper, drift detector — Steps 2–3). |
| `ghost/db/.gitkeep` | Placeholder for database utilities. |
| `ghost/api/.gitkeep` | Placeholder for FastAPI server (Step 5). |
| `ghost/api/routes/.gitkeep` | Placeholder for API route modules. |
| `ghost/benchmarks/.gitkeep` | Placeholder for τ-bench integration (Step 6). |
| `ghost/benchmarks/results/.gitkeep` | Placeholder for benchmark result JSON files. |
| `ghost/examples/.gitkeep` | Placeholder for example agent scripts. |
| `ghost/tests/.gitkeep` | Placeholder for test suite. |
| `ghost/dashboard/.gitkeep` | Placeholder for Next.js dashboard (Step 4). |
| `.env.example` | Template for environment variables. Copy to `.env` and fill in your keys. |
| `.gitignore` | Keeps secrets, caches, and build artifacts out of version control. |
| `requirements.txt` | Python dependencies pinned to minimum working versions. |
| `db/__init__.py` | Makes `db/` a Python package so we can import `db.schema`. |
| `db/schema.py` | **The SQLite database layer.** Creates all tables on import. |
| `core/__init__.py` | Makes `core/` a Python package (empty for now). |
| `core/memory.py` | **The ChromaDB failure memory layer.** Stores and retrieves past failures. |
| `test_step1.py` | Verification script — run this to confirm Step 1 is fully working. |

---

## Database Tables — What They Store and Why

### `sessions`
One row per agent execution session. When you wrap an agent with GHOST and run it on a task, a session is created. This table tracks:
- **What** the agent was trying to do (`task_type`, `objective`)
- **How** it went (`status`, `success`, `final_adherence`)
- **How much** work it did (`total_steps`, `recovery_count`)
- **When** it ran (`started_at`, `ended_at`)

**Why it exists:** You need a top-level record of every agent run to build dashboards, compute success rates, and identify which task types fail most often.

### `trajectory_logs`
One row per tool call the agent makes. This is the granular, step-by-step flight recorder. Each row captures:
- **What tool** was called and with what input/output (`tool_name`, `tool_input`, `tool_output`)
- **Whether it failed** and how (`failure_detected`, `failure_type`, `tool_error`)
- **Whether GHOST intervened** (`recovery_triggered`, `recovery_strategy`)
- **How well the agent was tracking** its goal at that moment (`adherence_score`)

**Why it exists:** This is the core data that powers drift detection, failure analysis, and the recovery engine. Without step-level logs, GHOST can't detect when an agent is going off-track.

### `successful_trajectories`
One row per successfully completed task. Stores the full tool sequence (as a JSON array) that led to success.

**Why it exists:** When a new task of the same type comes in, GHOST can look up "what worked before" and use it as a reference trajectory. This is how the system learns from past successes.

---

## How to Verify Step 1 Worked

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the verification script

```bash
python test_step1.py
```

You should see output like:

```
============================================================
  GHOST Step 1 — Foundation Verification
============================================================

[1/6] Checking folder structure...
  ✓ ghost/core/ exists
  ✓ ghost/db/ exists
  ✓ ghost/api/ exists
  ✓ ghost/api/routes/ exists
  ✓ ghost/benchmarks/ exists
  ✓ ghost/benchmarks/results/ exists
  ✓ ghost/examples/ exists
  ✓ ghost/tests/ exists
  ✓ ghost/dashboard/ exists

[2/6] Checking required files...
  ✓ .env.example exists
  ✓ .gitignore exists
  ✓ requirements.txt exists
  ✓ db/__init__.py exists
  ✓ db/schema.py exists
  ✓ core/__init__.py exists
  ✓ core/memory.py exists

[3/6] Initializing database...
  ✓ Database created at db/ghost.db
  ✓ Table 'sessions' exists
  ✓ Table 'trajectory_logs' exists
  ✓ Table 'successful_trajectories' exists

[4/6] Testing database operations...
  ✓ Insert into sessions works
  ✓ Insert into trajectory_logs works
  ✓ Insert into successful_trajectories works

[5/6] Testing ChromaDB memory...
  ✓ FailureMemory initialized
  ✓ store_failure() works
  ✓ get_warnings_for_task() returns results
  ✓ get_failure_stats() returns stats

[6/6] Cleanup...
  ✓ Test database removed
  ✓ Test ChromaDB directory removed

============================================================
  ✅ ALL CHECKS PASSED — Step 1 foundation is solid.
============================================================
```

### 3. (Optional) Inspect the database manually

```bash
python -c "import db.schema; print('Database initialized successfully')"
```

---

## What Comes Next

- **Step 2:** Agent wrapper — the `GhostWrapper` class that intercepts LangChain agent tool calls
- **Step 3:** Drift detection — real-time adherence scoring using embeddings
- **Step 4:** Next.js dashboard — live visualization of agent sessions
- **Step 5:** FastAPI server — REST API for the dashboard and external integrations
- **Step 6:** τ-bench integration — benchmarking against standardized agent evaluation
