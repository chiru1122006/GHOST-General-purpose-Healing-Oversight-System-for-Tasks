# STEP 5: Benchmarks, Tests, and Launch Documentation

This step adds a comprehensive testing and evaluation framework to GHOST, including simulated agents, τ-bench integration, automated unit tests, and a viral-ready README.md.

---

## 1. What is τ-bench & Why It's the Right Benchmark for GHOST

**τ-bench (Tau-bench)** is a standardized benchmark designed by researchers to evaluate LLM agents on long-horizon, real-world tasks (such as customer support in airline and retail domains). 

### Why it is perfect for GHOST:
1. **Realistic Tool Actions**: Agents must query databases, inspect user profiles, make updates, and check complex guidelines (policies).
2. **Multi-Step Complexity**: Solvable tasks require multiple tools (often 5 to 15 steps), making them highly susceptible to trajectory drift and repetition loops over time.
3. **Strict Evaluation**: Tasks have exact pass/fail criteria (e.g., specific database rows must be updated and corresponding email confirmation messages sent).
4. **Natural Failure Inducement**: Standard LLM agents running baseline ReAct loops drift on τ-bench tasks because context limits degrade instruction attention. GHOST intercepts this drift at the exact step it happens and triggers prompt-level healing.

---

## 2. How to Interpret the Benchmark Results Table

When running `python benchmarks/run_tau_bench.py`, the system outputs a comparison table:

```
╔══════════════════════════════════════════════════════════════╗
║               GHOST BENCHMARK RESULTS                       ║
╠══════════════════════════╦══════════════╦═════════╦═════════╣
║ Metric                   ║ Baseline     ║ GHOST   ║ Delta   ║
╠══════════════════════════╬══════════════╬═════════╬═════════╣
║ Task Success Rate        ║ XX.X%        ║ XX.X%   ║ +XX.X%  ║
║ Avg Steps per Task       ║ XX.X         ║ XX.X    ║ -X.X    ║
║ Failure Rate             ║ XX.X%        ║ XX.X%   ║ -XX.X%  ║
║ Recovery Success Rate    ║ —            ║ XX.X%   ║ —       ║
║ Total Drift Detections   ║ —            ║ XXX     ║ —       ║
╚══════════════════════════╩══════════════╩═════════╩═════════╝
```

### Key Metrics Explained:
* **Task Success Rate**: The percentage of tasks where the agent correctly solved the user's request (e.g., cancelled the order within policy, gave correct refund reasons). GHOST should show a massive success delta (+15% to +35%).
* **Avg Steps per Task**: The average steps taken. Healthy runs resolve tasks faster. When baseline agents get stuck in repetitions, they consume maximum steps. GHOST's recovery cuts loops early, resulting in *fewer* average steps (a negative Delta).
* **Failure Rate**: The inverse of Success Rate. GHOST reduces this significantly.
* **Recovery Success Rate**: The percentage of GHOST runs where a failure was detected and GHOST successfully steered the agent back to completion.
* **Total Drift Detections**: The total count of times GHOST intervened across the benchmark run.

---

## 3. What the Pytest Tests Cover & How to Run Them

We implement unit tests in the `tests/` directory to ensure core stability across versions.

### Test Coverage:
1. **`test_trajectory.py`**:
   - Identical Sequences: Assures a perfect or near-perfect score (>0.8) for exact trajectory matches.
   - Disjoint Sequences: Assures off-topic trajectories score below the drift threshold (<0.4).
   - Repetition Loops: Checks that repeating the same tool 3+ times in the last 5 steps short-circuits the score to <0.2.
   - Neutral Default: Verifies new/unknown task categories fallback safely to a neutral `0.7` score.
2. **`test_classifier.py`**:
   - Heuristics: Validates the fallback classifier correctly flags repetition loops and tool hallucinations without needing API calls.
   - API Call Parsing: Verifies JSON cleanup logic (removing markdown code blocks like ```json) functions properly.
   - API Integration: Verifies that API classification queries return structured failures when given tool history.
3. **`test_recovery.py`**:
   - Failure mapping: Assures all 5 MAST failure types have non-trivial prompt recovery injections.
   - Placeholder filling: Checks that the `{objective}` variable is successfully formatted and capitalized in the recovery prompts.
4. **`test_interceptor.py`**:
   - Initialization: Checks default handlers, uuid generation, and memory lookups.
   - Lifecycle tracking: Assures tool start, tool end, errors, and agent finish events correctly update state tables.

### Run command:
```bash
pytest tests/ -v
```

---

## 4. How to Write a Great GitHub README.md (Star Magnets)

To make engineers star a repository, the README must deliver immediate value and scientific credibility:
1. **The Hook**: A clear, bold value proposition showing the "why" in the first 2 seconds.
2. **Visual Proof**: A high-quality demo (GIF or SVG animation) showing the project in action.
3. **Scientific Credibility**: Citing real academic concepts (MAST taxonomy, Berkeley agent drift papers) makes it feel like state-of-the-art research rather than a side-project.
4. **Frictionless Onboarding**: Getting it running locally in less than 4 commands.
5. **Clear Architecture**: An ASCII diagram or flowchart explaining how the data flows so developers can conceptualize it quickly.

---

## 5. Sequence for Maximum Launch Visibility

Follow this precise sequence to launch GHOST and get traction:

1. **Record a 90-Second Demo**: Use a clean terminal capture or browser recording showing the dashboard real-time chart responding to a repetition recovery.
2. **Hacker News Post**: Title: `Show HN: GHOST — Open-Source AI Agent Trajectory Drift Detection & Self-Healing`. Focus on the ONNX-based local scoring and the SQLite/ChromaDB memory architecture.
3. **X/Twitter Post**: Share the 90-second demo video, link to the repo, and tag major agent developers. Embed the benchmark comparison table.
4. **Subreddits**:
   - `r/MachineLearning`: Focus on the MAST taxonomy mapping and empirical results.
   - `r/LocalLLaMA`: Highlight that the heuristic fallbacks make it fully runnable locally with ONNX.
5. **Academic Outreach**: Email the benchmark results to researchers working on agent evals, asking for feedback on the recovery engine approach.
