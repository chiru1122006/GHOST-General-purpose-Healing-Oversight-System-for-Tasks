# STEP 2: The Brain — Trajectory Scoring & Failure Classification

## What This Step Builds

Step 1 gave GHOST a memory (SQLite + ChromaDB). Step 2 gives it a **brain** — the ability to look at what an AI agent is doing *right now* and answer two questions:

1. **"Is this agent on track?"** → Trajectory adherence scoring
2. **"If not, what went wrong?"** → Failure classification

After completing Step 2, GHOST can score any agent's tool-call sequence in real time and classify failures into a structured taxonomy. No agent wrapping happens yet — that's Step 3.

---

## Trajectory Adherence Scoring — What It Means

Imagine you're watching a junior developer work on a task. You've seen senior developers complete the same task before, and you know the typical steps: open the file, read the code, write a fix, run the tests, commit.

If the junior developer follows roughly the same steps, you'd say they're "on track." If they start browsing Reddit, deleting random files, and running the same failing test over and over, you'd say they've "drifted."

**Trajectory adherence scoring is exactly this, but for AI agents.** GHOST compares the agent's current sequence of tool calls against previously successful sequences for the same task type. The score is a number between 0.0 (completely off-track) and 1.0 (perfectly aligned with past successes).

A score of 0.7 means "mostly on track." A score of 0.15 means "this agent is lost." A score of 0.05 means "this agent is stuck in a loop."

---

## Why Jaccard Similarity (and How It Works)

We use **Jaccard similarity** because it answers a simple, robust question: "How much overlap is there between the tools this agent is using and the tools that worked before?" It computes the size of the intersection divided by the size of the union of two sets. For example, if a successful trajectory used tools `{search, read, extract, summarize}` and the current agent has used `{search, read, cook, drive}`, the intersection is `{search, read}` (size 2) and the union is `{search, read, extract, summarize, cook, drive}` (size 6), giving a Jaccard score of 2/6 ≈ 0.33. This is low, meaning the agent is using mostly wrong tools. Jaccard is ideal here because it's order-independent (doesn't care about tool sequence), handles sets of different sizes gracefully, and is computationally trivial — no GPU, no API call, no latency. We complement it with embedding-based cosine similarity (weight 0.4) to capture sequential/semantic patterns that Jaccard misses, but Jaccard (weight 0.6) is the backbone because it's fast, interpretable, and never hallucinates.

---

## The MAST Failure Taxonomy

**MAST (Multi-Agent System Taxonomy)** is a classification system for AI agent failure modes, drawing from research on agent reliability at Berkeley and Stanford (2025). The taxonomy identifies recurring patterns in how language-model agents fail during tool-use tasks — patterns that are consistent across different agent architectures, LLM providers, and task domains.

GHOST implements 5 failure types from MAST (plus a `no_failure` category):

### 1. `step_repetition_loop`
**What it is:** The agent calls the same tool with the same (or nearly identical) input multiple times in a row, without making progress.

**Example in practice:**
```
Step 4: search_flights("NYC to LAX, June 15")  → 3 results
Step 5: search_flights("NYC to LAX, June 15")  → 3 results  
Step 6: search_flights("NYC to LAX, June 15")  → 3 results  ← stuck
```
The agent found results but doesn't know what to do next, so it keeps searching.

---

### 2. `goal_drift`
**What it is:** The agent starts working on the right task but gradually shifts to something unrelated, losing sight of the original objective.

**Example in practice:**
```
Objective: "Book a flight from NYC to LAX"
Step 1: search_flights("NYC to LAX")         ← on track
Step 2: read_page("LAX airport info")         ← still relevant
Step 3: search_web("things to do in LA")      ← drifting
Step 4: search_web("best restaurants LA")     ← lost the plot
Step 5: book_restaurant("Nobu Malibu")        ← completely off-task
```

---

### 3. `tool_hallucination`
**What it is:** The agent tries to call a tool that doesn't exist, or passes structurally invalid input to a real tool, causing repeated errors.

**Example in practice:**
```
Step 3: send_email(to="user@test.com", body="...")   → ERROR: Tool 'send_email' not found
Step 4: email_user(to="user@test.com", body="...")   → ERROR: Tool 'email_user' not found
Step 5: dispatch_email(to="user@test.com")           → ERROR: Tool 'dispatch_email' not found
```
The agent "hallucinates" tool names that sound plausible but aren't in its toolkit.

---

### 4. `in_context_locking`
**What it is:** The agent fixates on one piece of information or one approach and cannot consider alternatives, even when the current approach isn't working.

**Example in practice:**
```
Objective: "Find the CEO's email address"
Step 1: search_web("CEO email acme corp")         → no results
Step 2: search_web("CEO email address acme corp")  → no results
Step 3: search_web("acme corp CEO contact email")  → no results
Step 4: search_web("acme corporation CEO email")   → no results
```
The agent is locked into web searching when it should try the company directory tool.

---

### 5. `resource_exhaustion`
**What it is:** The agent takes an excessive number of steps without producing any output, burning through API calls, tokens, and time without converging on a result.

**Example in practice:**
```
Steps 1–15: Various search, read, analyze operations
No write_file, send_response, or any output-producing tool called
Agent has consumed 45,000 tokens and $0.12 in API costs
Still "gathering information"
```

---

## Files Created in This Step

| File | Purpose |
|------|---------|
| `STEP2_README.md` | This file — explains the scoring and classification systems. |
| `core/trajectory.py` | **Trajectory adherence scorer.** Compares current tool sequences against past successes using Jaccard + embedding similarity. |
| `core/classifier.py` | **Failure classifier.** Uses NVIDIA NIM (Llama 3.1 70B) to classify failures into the MAST taxonomy, with a pure-Python heuristic fallback. |
| `test_step2.py` | Verification script — tests scoring, heuristic classification, and optionally live NIM API. |

---

## How to Verify Step 2 Worked

### Run the verification script

```bash
python test_step2.py
```

Expected output:

```
============================================================
  GHOST Step 2 — Scoring & Classification Verification
============================================================

[1/3] Testing trajectory adherence scoring...
  [GHOST Trajectory] Loaded embedding model
  Score (similar to success): 0.82
  Score (random tools):       0.11
  Score (repetition loop):    0.05
  ✓ Similar sequence scores higher than random
  ✓ Repetition loop detected (score < 0.2)

[2/3] Testing heuristic classifier...
  Failure type: step_repetition_loop
  Confidence:   0.85
  Reasoning:    Same tool repeated 3+ times in last 5 steps
  ✓ Correctly classified repetition loop

[3/3] Testing live NIM API classifier...
  ⏭ Skipping — no NVIDIA_API_KEY in .env
  (Set NVIDIA_API_KEY in .env to test live classification)

============================================================
  ✅ Step 2 complete. Scoring and classification working.
  📖 Read STEP2_README.md to understand what was built.
  ➡️  Next: paste the Step 3 prompt.
============================================================
```

### (Optional) Test with a real API key

Set `NVIDIA_API_KEY` in your `.env` file and run `test_step2.py` again. The live API test will call NVIDIA NIM's Llama 3.1 70B model to classify the failure.

---

## What Comes Next

- **Step 3:** The `GhostWrapper` — the agent wrapper that intercepts every tool call, runs the scorer and classifier in real time, and triggers recovery strategies.
