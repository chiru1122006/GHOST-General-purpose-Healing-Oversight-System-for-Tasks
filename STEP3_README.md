# STEP 3: Recovery Engine & Interceptor — Making GHOST Work

## What This Step Builds

Steps 1–2 gave GHOST a memory (database), eyes (trajectory scoring), and a brain (failure classification). Step 3 gives it **hands** — the ability to actually intervene when an agent goes wrong, and the **nervous system** that connects everything together.

After completing Step 3, you can wrap *any* LangChain agent with a single decorator or callback handler and GHOST will automatically monitor, detect, classify, and recover from failures in real time.

---

## What "Recovery" Means

When GHOST detects that an agent has drifted off-track, it doesn't stop the agent or restart it. Instead, it **injects corrective text into the agent's next prompt** — like a copilot whispering instructions into a pilot's ear.

The injected text is firm and specific. It tells the agent exactly what it did wrong and exactly what to do next. This is far more effective than vague suggestions because LLMs respond well to direct, authoritative instructions embedded in their context window.

Recovery is *not*:
- Restarting the agent from scratch
- Removing the agent's access to tools
- Asking the user to intervene

Recovery *is*:
- Injecting a corrective system message before the agent's next action
- Banning specific tools that caused loops
- Re-stating the original objective in ALL CAPS
- Forcing the agent to enumerate alternatives

---

## The 5 Recovery Strategies

### 1. `context_reset` → for `step_repetition_loop`

**What it does:** Bans the tool the agent has been repeating and forces it to pick an unused tool.

**Why it works:** LLMs get "stuck" because the same context keeps producing the same next-token prediction. By explicitly banning the repeated tool and demanding a different one, we break the prediction loop. The firm language ("If you call the same tool again, your task will FAIL") activates the model's instruction-following behavior.

**Example injection:** *"STOP. You have called search_web 3 times in a row. Do NOT call search_web again. Choose a tool you have NOT used yet..."*

---

### 2. `objective_reinjection` → for `goal_drift`

**What it does:** Re-injects the original objective in ALL CAPS and requires the agent to explicitly connect its next action to the goal.

**Why it works:** Goal drift happens because the objective fades from the model's attention window as new context accumulates. Restating it in ALL CAPS with high salience forces it back into focus. Requiring the agent to articulate *how* its next step serves the goal creates a logical checkpoint.

**Example injection:** *"CRITICAL: Your original objective is: BOOK A FLIGHT FROM NYC TO LAX. Your recent actions do NOT serve this objective. Before your next action, state which part of the objective it addresses..."*

---

### 3. `output_validation` → for `tool_hallucination`

**What it does:** Tells the agent to verify the tool name exists before calling it, check argument formats, and read error messages carefully.

**Why it works:** Tool hallucination happens because the model "imagines" tool names that sound right but aren't in its toolkit. By making it cross-reference against the actual tool list and read error outputs, we force a self-correction loop.

**Example injection:** *"BEFORE calling any tool, verify it exists in your available tools: [search_web, read_page, ...]. Check all required arguments are present..."*

---

### 4. `forced_exploration` → for `in_context_locking`

**What it does:** Forces the agent to enumerate at least 3 alternative approaches, listing the current (failing) approach last, and then pick from the alternatives.

**Why it works:** In-context locking happens because the model's attention is dominated by one approach. By requiring it to generate alternatives *before* choosing, we widen the search space. Listing the current approach last exploits recency bias — the model is more likely to pick recently mentioned alternatives.

**Example injection:** *"You are stuck in a single approach. List 3 DIFFERENT ways to achieve your goal. Your current approach must be listed LAST. Choose one of the first two..."*

---

### 5. `efficiency_mode` → for `resource_exhaustion`

**What it does:** Informs the agent it has used too many steps and demands that each remaining action directly advances toward completion.

**Why it works:** Resource exhaustion happens when the model is in an "exploration" mode without a convergence signal. By imposing a hard constraint ("your next 3 actions must each directly produce output"), we shift it into a completion-oriented mindset.

**Example injection:** *"WARNING: You have used too many steps. Your next 3 actions must each DIRECTLY advance toward completing the task. Skip ALL exploratory steps. Be decisive..."*

---

## What the Interceptor Does

The interceptor (`GHOSTCallbackHandler`) is a LangChain callback handler that hooks into the agent's execution lifecycle. Every time the agent calls a tool, the interceptor:

```
┌─────────────────────────────────────────────────────┐
│  Agent calls a tool                                 │
│         ↓                                           │
│  on_tool_start() → Record tool name + input         │
│         ↓                                           │
│  Tool executes...                                   │
│         ↓                                           │
│  on_tool_end() → Record output                      │
│         ↓                                           │
│  _check_trajectory()                                │
│    ├─ Compute adherence score (Jaccard + embedding)  │
│    ├─ Log step to SQLite                            │
│    ├─ If score < threshold:                         │
│    │    ├─ _handle_drift()                          │
│    │    │    ├─ Classify failure (NIM API + fallback)│
│    │    │    ├─ Get recovery strategy                │
│    │    │    ├─ Store failure in ChromaDB memory     │
│    │    │    ├─ Log to SQLite                        │
│    │    │    └─ Return injection text                │
│    │    └─ Inject corrective prompt                  │
│    └─ Print colored adherence score                 │
│         ↓                                           │
│  on_agent_finish() → Save session + trajectory      │
└─────────────────────────────────────────────────────┘
```

---

## The `@ghost_monitor` Decorator

The decorator is the simplest way to use GHOST. It wraps any function that calls a LangChain agent and automatically injects the callback handler:

```python
from core import ghost_monitor

@ghost_monitor(
    task_type="web_research",
    objective="Research AI breakthroughs in 2026"
)
def run_agent(query):
    return agent_executor.invoke({"input": query})

# That's it. GHOST is now monitoring.
result = run_agent("What are the latest AI breakthroughs?")
```

You can also use the handler directly for more control:

```python
from core import GHOSTCallbackHandler

handler = GHOSTCallbackHandler(
    task_type="web_research",
    objective="Research AI breakthroughs in 2026"
)
result = agent_executor.invoke(
    {"input": "What are the latest AI breakthroughs?"},
    config={"callbacks": [handler]}
)
print(handler.get_summary())
```

---

## Files Created in This Step

| File | Purpose |
|------|---------|
| `STEP3_README.md` | This file — explains recovery, the interceptor, and the decorator. |
| `core/recovery.py` | `RecoveryEngine` — maps failure types to recovery strategies with injection text. |
| `core/interceptor.py` | `GHOSTCallbackHandler` + `@ghost_monitor` — the main integration point. |
| `core/__init__.py` | Updated — exports all public classes and the decorator. |
| `examples/demo_simple.py` | Minimal working demo with mock tools and both usage patterns. |
| `test_step3.py` | Verification script — tests recovery engine, handler init, and simulated tool calls. |

---

## How to Verify Step 3 Worked

### Run the verification script

```bash
python test_step3.py
```

Expected output:

```
============================================================
  GHOST Step 3 — Recovery Engine & Interceptor Verification
============================================================

[1/3] Testing recovery engine...
  ✓ step_repetition_loop → context_reset
  ✓ goal_drift → objective_reinjection
  ✓ tool_hallucination → output_validation
  ✓ in_context_locking → forced_exploration
  ✓ resource_exhaustion → efficiency_mode

[2/3] Testing handler initialization...
  ✓ Handler initializes correctly

[3/3] Testing simulated tool calls...
  ✓ Handler tracked 3 steps
  INFO: Adherence history: [...]

============================================================
  ✅ Step 3 complete. Recovery engine and interceptor working.
  📖 Read STEP3_README.md to understand what was built.
  ➡️  Next: paste the Step 4 prompt.
  💡 Optional now: python examples/demo_simple.py (needs NVIDIA_API_KEY)
============================================================
```

### (Optional) Run the live demo

```bash
python examples/demo_simple.py
```

This requires `NVIDIA_API_KEY` in `.env` and will run a real LLM agent with GHOST monitoring. You'll see colorful real-time output showing adherence scores, drift detection, and recovery injections.

---

## What Comes Next

- **Step 4:** Next.js dashboard — live visualization of agent sessions, trajectories, and failure patterns
- **Step 5:** FastAPI server — REST API powering the dashboard
- **Step 6:** τ-bench integration — benchmarking GHOST against standardized agent evaluation
