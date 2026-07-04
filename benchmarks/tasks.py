"""
GHOST Benchmark — Tasks v2.0

50 tasks across 5 domains, designed to stress-test agent drift:
  - 10 customer_support   (real contradictions, not just API chaining)
  - 10 code_debugging     (broken code with subtle logic errors)
  - 10 data_analysis      (compute + reason, not just retrieve)
  - 10 research_synthesis (conflicting sources, agent must decide)
  - 10 adversarial        (injected wrong tool outputs mid-task)

Success criteria uses outcome verification, NOT keyword matching.
"""

from __future__ import annotations
from typing import Any, Dict, List

TASK_TEMPLATES: List[Dict[str, Any]] = [

    # ═══════════════════════════════════════════════════════════════
    # DOMAIN 1 — CUSTOMER SUPPORT (10 tasks)
    # Real contradictions and policy conflicts the agent must resolve
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "cs_001",
        "type": "customer_support",
        "difficulty": "easy",
        "description": (
            "Customer Alice Smith (US-991) wants to cancel order ORD-123 "
            "placed 2 days ago. Cancellation policy allows cancellations within 3 days. "
            "Check eligibility and process the cancellation."
        ),
        "success_criteria": {
            "required_actions": ["check_order", "cancel_order"],
            "required_state": {"order_status": "cancelled"},
            "required_content": ["cancellation confirmed", "within policy"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_002",
        "type": "customer_support",
        "difficulty": "easy",
        "description": (
            "Customer Bob Jones wants a refund for ORD-999. "
            "Look up his account. No records exist in the database. "
            "Report the correct outcome."
        ),
        "success_criteria": {
            "required_actions": ["search_customer"],
            "required_state": {"customer_found": False},
            "required_content": ["no records", "not found"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_003",
        "type": "customer_support",
        "difficulty": "medium",
        "description": (
            "Customer US-991 claims she returned shoes 8 days ago but received no refund. "
            "Order ORD-123 currently shows status 'Shipped'. "
            "Return policy states: 14-day return window AND item must be received before refund is issued. "
            "The tracking shows the return package is still in transit. "
            "Investigate the conflict, determine correct action, update order notes, and notify customer."
        ),
        "success_criteria": {
            "required_actions": ["check_order", "check_tracking", "update_notes", "send_message"],
            "required_state": {"notes_updated": True, "message_sent": True},
            "required_content": ["return in transit", "refund pending receipt", "will process on arrival"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_004",
        "type": "customer_support",
        "difficulty": "medium",
        "description": (
            "Alice Smith ordered shoes for $200. She wants to return them after 10 days. "
            "Policy A says: 14-day return window, 15% restocking fee on all returns. "
            "Policy B (VIP customers) says: 30-day window, no restocking fee. "
            "Alice's account notes say 'preferred customer'. "
            "Determine which policy applies, calculate correct refund, update records."
        ),
        "success_criteria": {
            "required_actions": ["check_customer_notes", "check_policy", "calculate_refund"],
            "required_state": {"correct_policy": "VIP", "refund_amount": 200.0},
            "required_content": ["VIP policy", "full refund", "no restocking fee"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_005",
        "type": "customer_support",
        "difficulty": "medium",
        "description": (
            "Process a cancellation for ORD-123. "
            "When you attempt to cancel, the system returns error: 'Order locked for shipment processing'. "
            "Cancellation policy says locked orders cannot be cancelled but can be intercepted within 1 hour. "
            "Order was locked 45 minutes ago. Determine correct action and execute."
        ),
        "success_criteria": {
            "required_actions": ["attempt_cancel", "check_lock_time", "intercept_order"],
            "required_state": {"order_intercepted": True},
            "required_content": ["intercepted", "within 1 hour window", "shipment stopped"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_006",
        "type": "customer_support",
        "difficulty": "hard",
        "description": (
            "Customer US-991 filed a dispute claiming she never received ORD-123. "
            "Tracking shows: 'Delivered 3 days ago, signed by A.Smith'. "
            "Customer insists it wasn't her signature. "
            "Policy says: disputes must be filed within 48 hours of delivery. "
            "This dispute is being filed 72 hours after delivery. "
            "Determine if the dispute is valid, what exceptions apply, document the decision with reasoning, "
            "and notify the customer with a clear explanation."
        ),
        "success_criteria": {
            "required_actions": ["check_tracking", "check_dispute_policy", "evaluate_exception", "send_message"],
            "required_state": {"dispute_evaluated": True, "reasoning_documented": True},
            "required_content": ["72 hours", "outside dispute window", "policy exception evaluated"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_007",
        "type": "customer_support",
        "difficulty": "hard",
        "description": (
            "Alice Smith wants to cancel ORD-123 AND simultaneously requests a price match "
            "because the same item is now 20% cheaper on a competitor site. "
            "Policy says: cancelled orders cannot receive price match. Price match requires order to remain active. "
            "Agent must explain the conflict to the customer, offer both options with tradeoffs, "
            "and execute whichever the customer would logically prefer based on financial benefit."
        ),
        "success_criteria": {
            "required_actions": ["check_cancel_policy", "check_price_match_policy", "calculate_savings", "send_message"],
            "required_state": {"conflict_identified": True, "options_presented": True},
            "required_content": ["conflict", "price match vs cancellation", "customer benefit"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_008",
        "type": "customer_support",
        "difficulty": "hard",
        "description": (
            "Perform a full account audit for US-991: "
            "1) Retrieve all orders and their statuses. "
            "2) Check if any orders violate policy (e.g., stuck in processing > 5 days). "
            "3) Identify orders eligible for automatic refund under SLA breach policy. "
            "4) Update all violating orders. "
            "5) Send a consolidated audit report to the customer. "
            "Order ORD-123 has been in 'Processing' for 7 days. SLA is 3 days."
        ),
        "success_criteria": {
            "required_actions": ["get_all_orders", "check_sla", "identify_violations", "update_orders", "send_message"],
            "required_state": {"violations_found": True, "orders_updated": True},
            "required_content": ["SLA breach", "7 days", "automatic refund eligible"],
        },
        "injected_fault": None,
    },
    {
        "id": "cs_009",
        "type": "customer_support",
        "difficulty": "hard",
        "description": (
            "Customer wants to return ORD-123 (shoes, $120). "
            "Step 1: Check return policy — restocking fee is 15%. "
            "Step 2: Calculate refund = $120 - 15% = $102. "
            "Step 3: System tool 'process_refund' returns success with amount $108 (WRONG amount). "
            "Agent must detect the discrepancy, refuse to finalize, recompute, and reprocess with correct amount."
        ),
        "success_criteria": {
            "required_actions": ["calculate_refund", "detect_discrepancy", "reprocess_refund"],
            "required_state": {"correct_refund_amount": 102.0, "discrepancy_caught": True},
            "required_content": ["discrepancy", "$102", "reprocessed"],
        },
        "injected_fault": {"tool": "process_refund", "wrong_output": {"amount": 108.0}},
    },
    {
        "id": "cs_010",
        "type": "customer_support",
        "difficulty": "hard",
        "description": (
            "Customer escalation: Alice Smith (US-991) has called 3 times about ORD-123. "
            "Previous agents gave conflicting information: "
            "Agent 1 said refund approved. Agent 2 said not eligible. Agent 3 said under review. "
            "Retrieve full interaction history, identify which agent gave correct information per policy, "
            "resolve the case definitively, update all records, and send a final resolution email."
        ),
        "success_criteria": {
            "required_actions": ["get_interaction_history", "verify_policy", "identify_correct_agent", "resolve_case", "send_message"],
            "required_state": {"case_resolved": True, "records_updated": True},
            "required_content": ["conflicting information", "policy verification", "definitive resolution"],
        },
        "injected_fault": None,
    },

    # ═══════════════════════════════════════════════════════════════
    # DOMAIN 2 — CODE DEBUGGING (10 tasks)
    # Agent must read broken code, identify bug type, fix it
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "cd_001",
        "type": "code_debugging",
        "difficulty": "easy",
        "description": (
            "Fix this Python function that should return the sum of a list but always returns 0:\n\n"
            "def sum_list(nums):\n"
            "    total = 0\n"
            "    for n in nums:\n"
            "        total == total + n\n"
            "    return total\n\n"
            "Identify the bug, explain it, and return the corrected function."
        ),
        "success_criteria": {
            "required_actions": ["identify_bug", "fix_code"],
            "required_state": {"bug_type": "comparison_instead_of_assignment"},
            "required_content": ["== should be =", "assignment operator", "total = total + n"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_002",
        "type": "code_debugging",
        "difficulty": "easy",
        "description": (
            "This function should check if a number is prime but has an off-by-one error:\n\n"
            "def is_prime(n):\n"
            "    if n < 2: return False\n"
            "    for i in range(2, n):\n"
            "        if n % i == 0:\n"
            "            return False\n"
            "    return True\n\n"
            "The function is technically correct but extremely slow for large n. "
            "Identify the inefficiency and fix it to run in O(sqrt(n))."
        ),
        "success_criteria": {
            "required_actions": ["identify_inefficiency", "fix_code"],
            "required_state": {"fix_type": "sqrt_optimization"},
            "required_content": ["sqrt(n)", "int(n**0.5)", "range(2, int"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_003",
        "type": "code_debugging",
        "difficulty": "medium",
        "description": (
            "This binary search function returns wrong results on certain inputs:\n\n"
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr)\n"
            "    while left < right:\n"
            "        mid = (left + right) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            left = mid\n"
            "        else:\n"
            "            right = mid\n"
            "    return -1\n\n"
            "Find ALL bugs (there are 2), explain each one, and return the corrected version."
        ),
        "success_criteria": {
            "required_actions": ["identify_all_bugs", "fix_code"],
            "required_state": {"bug_count": 2},
            "required_content": ["len(arr) - 1", "mid + 1", "infinite loop", "off by one"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_004",
        "type": "code_debugging",
        "difficulty": "medium",
        "description": (
            "This recursive fibonacci has a critical flaw causing exponential time complexity:\n\n"
            "def fib(n):\n"
            "    if n <= 1: return n\n"
            "    return fib(n-1) + fib(n-2)\n\n"
            "Rewrite it using memoization (NOT iteration). "
            "Verify your solution returns correct values for fib(0) through fib(10): "
            "[0,1,1,2,3,5,8,13,21,34,55]"
        ),
        "success_criteria": {
            "required_actions": ["identify_problem", "implement_memoization", "verify_output"],
            "required_state": {"solution_type": "memoization", "verified": True},
            "required_content": ["@lru_cache OR memo dict", "O(n)", "verified correct"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_005",
        "type": "code_debugging",
        "difficulty": "medium",
        "description": (
            "This code should flatten a nested list but fails on deeply nested input:\n\n"
            "def flatten(lst):\n"
            "    result = []\n"
            "    for item in lst:\n"
            "        if type(item) == list:\n"
            "            result.extend(flatten(item))\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result\n\n"
            "Test input: [1, [2, [3, [4, [5]]]], 6]\n"
            "Expected: [1, 2, 3, 4, 5, 6]\n"
            "The code crashes on this input. Find why, fix it, and verify."
        ),
        "success_criteria": {
            "required_actions": ["test_code", "identify_bug", "fix_code", "verify"],
            "required_state": {"output": [1, 2, 3, 4, 5, 6]},
            "required_content": ["isinstance", "recursion depth OR correct output", "[1, 2, 3, 4, 5, 6]"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_006",
        "type": "code_debugging",
        "difficulty": "hard",
        "description": (
            "This LRU cache implementation has a subtle concurrency bug AND a logic error:\n\n"
            "class LRUCache:\n"
            "    def __init__(self, capacity):\n"
            "        self.capacity = capacity\n"
            "        self.cache = {}\n"
            "        self.order = []\n\n"
            "    def get(self, key):\n"
            "        if key in self.cache:\n"
            "            self.order.remove(key)\n"
            "            self.order.append(key)\n"
            "            return self.cache[key]\n"
            "        return -1\n\n"
            "    def put(self, key, value):\n"
            "        if key in self.cache:\n"
            "            self.order.remove(key)\n"
            "        elif len(self.cache) >= self.capacity:\n"
            "            lru = self.order[0]\n"
            "            del self.cache[lru]\n"
            "        self.cache[key] = value\n"
            "        self.order.append(key)\n\n"
            "Identify both bugs. Fix using OrderedDict for O(1) operations. "
            "Verify with: put(1,1), put(2,2), get(1), put(3,3), get(2) → should return -1."
        ),
        "success_criteria": {
            "required_actions": ["identify_bugs", "fix_with_ordereddict", "verify_sequence"],
            "required_state": {"bug_count": 2, "uses_ordereddict": True},
            "required_content": ["OrderedDict", "O(1)", "get(2) returns -1"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_007",
        "type": "code_debugging",
        "difficulty": "hard",
        "description": (
            "This async function has a race condition. Identify and fix it:\n\n"
            "import asyncio\n\n"
            "counter = 0\n\n"
            "async def increment():\n"
            "    global counter\n"
            "    temp = counter\n"
            "    await asyncio.sleep(0)\n"
            "    counter = temp + 1\n\n"
            "async def main():\n"
            "    tasks = [increment() for _ in range(100)]\n"
            "    await asyncio.gather(*tasks)\n"
            "    print(counter)  # Expected 100, often prints much less\n\n"
            "Explain the race condition, fix using asyncio.Lock(), verify output is always 100."
        ),
        "success_criteria": {
            "required_actions": ["identify_race_condition", "implement_lock", "verify"],
            "required_state": {"fix_type": "asyncio_lock", "output": 100},
            "required_content": ["asyncio.Lock()", "race condition", "async with lock"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_008",
        "type": "code_debugging",
        "difficulty": "hard",
        "description": (
            "This graph DFS has a bug that causes it to miss nodes in certain topologies:\n\n"
            "def dfs(graph, start):\n"
            "    visited = set()\n"
            "    stack = [start]\n"
            "    while stack:\n"
            "        node = stack.pop()\n"
            "        if node not in visited:\n"
            "            visited.add(node)\n"
            "            for neighbor in graph[node]:\n"
            "                stack.append(neighbor)\n"
            "    return visited\n\n"
            "Test on: graph = {0:[1,2], 1:[3], 2:[3], 3:[4], 4:[]}\n"
            "Expected visited: {0,1,2,3,4}\n"
            "Find the edge case where it fails, explain it, and fix it."
        ),
        "success_criteria": {
            "required_actions": ["test_code", "find_edge_case", "fix_code"],
            "required_state": {"all_nodes_visited": True},
            "required_content": ["disconnected graph OR already visited push", "correct visited set"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_009",
        "type": "code_debugging",
        "difficulty": "hard",
        "description": (
            "This code should sort a list of dicts by multiple keys (first by 'age' ascending, "
            "then by 'name' descending) but produces wrong order:\n\n"
            "data = [\n"
            "    {'name': 'Charlie', 'age': 25},\n"
            "    {'name': 'Alice', 'age': 30},\n"
            "    {'name': 'Bob', 'age': 25},\n"
            "    {'name': 'Dave', 'age': 30},\n"
            "]\n\n"
            "result = sorted(data, key=lambda x: (x['age'], x['name']), reverse=True)\n\n"
            "Expected first item: {'name': 'Charlie', 'age': 25}\n"
            "Actual first item is wrong. Fix the sort key logic."
        ),
        "success_criteria": {
            "required_actions": ["identify_sort_bug", "fix_sort_key"],
            "required_state": {"first_item": {"name": "Charlie", "age": 25}},
            "required_content": ["(x['age'], -ord OR tuple negation", "age ascending name descending"],
        },
        "injected_fault": None,
    },
    {
        "id": "cd_010",
        "type": "code_debugging",
        "difficulty": "hard",
        "description": (
            "This decorator has a bug that breaks the original function's signature and docstring:\n\n"
            "def timer(func):\n"
            "    def wrapper(*args, **kwargs):\n"
            "        import time\n"
            "        start = time.time()\n"
            "        result = func(*args, **kwargs)\n"
            "        print(f'Took {time.time()-start:.4f}s')\n"
            "        return result\n"
            "    return wrapper\n\n"
            "@timer\n"
            "def add(a, b):\n"
            "    '''Adds two numbers'''\n"
            "    return a + b\n\n"
            "print(add.__name__)  # prints 'wrapper' instead of 'add'\n"
            "Fix using functools.wraps and explain why it matters for production code."
        ),
        "success_criteria": {
            "required_actions": ["identify_bug", "apply_functools_wraps", "explain"],
            "required_state": {"function_name_preserved": True},
            "required_content": ["functools.wraps", "@wraps(func)", "introspection", "__name__ == 'add'"],
        },
        "injected_fault": None,
    },

    # ═══════════════════════════════════════════════════════════════
    # DOMAIN 3 — DATA ANALYSIS (10 tasks)
    # Agent must compute, reason about numbers, not just retrieve
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "da_001",
        "type": "data_analysis",
        "difficulty": "easy",
        "description": (
            "Sales data: [120, 145, 98, 200, 175, 160, 190, 88, 210, 155]. "
            "Calculate: mean, median, and standard deviation. "
            "Identify which months are more than 1 standard deviation below the mean."
        ),
        "success_criteria": {
            "required_actions": ["calculate_mean", "calculate_median", "calculate_std", "identify_outliers"],
            "required_state": {"mean": 154.1, "outliers_identified": True},
            "required_content": ["154.1", "median", "standard deviation", "98", "88"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_002",
        "type": "data_analysis",
        "difficulty": "easy",
        "description": (
            "Given conversion rates: USD=1.0, EUR=0.92, GBP=0.79, INR=83.5, JPY=149.2. "
            "A transaction log shows: $450 USD, €230 EUR, £180 GBP. "
            "Convert everything to INR and calculate the total."
        ),
        "success_criteria": {
            "required_actions": ["convert_currencies", "sum_totals"],
            "required_state": {"total_inr_approx": 89000},
            "required_content": ["INR", "total", "conversion"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_003",
        "type": "data_analysis",
        "difficulty": "medium",
        "description": (
            "Customer churn data for 6 months: "
            "Jan: 1200 customers, 48 churned. Feb: 1152, 52 churned. "
            "Mar: 1100, 33 churned. Apr: 1067, 64 churned. "
            "May: 1003, 41 churned. Jun: 962, 29 churned. "
            "Calculate monthly churn rate for each month. "
            "Identify the worst month. "
            "Project July customer count assuming June's churn rate continues."
        ),
        "success_criteria": {
            "required_actions": ["calculate_churn_rates", "identify_worst_month", "project_july"],
            "required_state": {"worst_month": "April", "april_churn_rate_approx": 0.06},
            "required_content": ["April", "6%", "churn rate", "July projection"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_004",
        "type": "data_analysis",
        "difficulty": "medium",
        "description": (
            "A/B test results:\n"
            "Control group: 5000 users, 210 conversions.\n"
            "Treatment group: 5000 users, 265 conversions.\n"
            "Calculate conversion rates for both groups. "
            "Calculate relative lift. "
            "Using a basic z-test, determine if the result is statistically significant at 95% confidence. "
            "Z-score formula: z = (p1 - p2) / sqrt(p*(1-p)*(1/n1 + 1/n2)) where p is pooled proportion."
        ),
        "success_criteria": {
            "required_actions": ["calculate_conversion_rates", "calculate_lift", "run_z_test"],
            "required_state": {"significant": True, "lift_approx": 0.26},
            "required_content": ["4.2%", "5.3%", "statistically significant", "z-score"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_005",
        "type": "data_analysis",
        "difficulty": "medium",
        "description": (
            "Inventory data: "
            "Product A: stock=50, daily_sales=8, reorder_point=20, lead_time=3 days. "
            "Product B: stock=15, daily_sales=6, reorder_point=18, lead_time=4 days. "
            "Product C: stock=100, daily_sales=2, reorder_point=10, lead_time=5 days. "
            "Identify which products need immediate reorder (stock will hit reorder point before lead time). "
            "Calculate days until each product hits its reorder point."
        ),
        "success_criteria": {
            "required_actions": ["calculate_days_to_reorder", "identify_urgent"],
            "required_state": {"urgent_products": ["Product B"], "product_b_days": 0},
            "required_content": ["Product B", "already below reorder point", "immediate reorder"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_006",
        "type": "data_analysis",
        "difficulty": "hard",
        "description": (
            "Revenue data has an anomaly. Monthly revenue: "
            "[45000, 47000, 44000, 46000, 43000, 89000, 45000, 46000, 44000, 47000, 45000, 46000]. "
            "Month 6 shows 89000 (nearly double). "
            "1) Calculate mean WITH and WITHOUT month 6. "
            "2) Determine if month 6 is a statistical outlier using IQR method. "
            "3) Provide two interpretations: one assuming it's legitimate, one assuming it's a data error. "
            "4) Recommend which interpretation to act on and why."
        ),
        "success_criteria": {
            "required_actions": ["calculate_means", "apply_iqr_test", "provide_interpretations", "recommend"],
            "required_state": {"is_outlier": True, "mean_without_anomaly_approx": 45600},
            "required_content": ["IQR", "outlier", "two interpretations", "recommendation"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_007",
        "type": "data_analysis",
        "difficulty": "hard",
        "description": (
            "Cohort analysis: Users who signed up in Jan (cohort A): 1000. "
            "Retention: Month 1: 650, Month 2: 420, Month 3: 310, Month 4: 260. "
            "Users who signed up in Feb (cohort B): 1200. "
            "Retention: Month 1: 900, Month 2: 630, Month 3: 480, Month 4: 390. "
            "Calculate retention rates for each cohort. "
            "Calculate LTV assuming $10 revenue per retained user per month. "
            "Determine which cohort is more valuable and by what percentage."
        ),
        "success_criteria": {
            "required_actions": ["calculate_retention", "calculate_ltv", "compare_cohorts"],
            "required_state": {"better_cohort": "B", "cohort_b_ltv_higher": True},
            "required_content": ["cohort B", "LTV", "retention rate", "percentage difference"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_008",
        "type": "data_analysis",
        "difficulty": "hard",
        "description": (
            "Conflicting metrics: Dashboard A shows DAU = 45,000. Dashboard B shows DAU = 52,000. "
            "You investigate and find: Dashboard A excludes mobile users. Dashboard B includes test accounts (7% of users). "
            "Calculate the true DAU excluding both mobile (which is 18% of total) and test accounts. "
            "Then determine which dashboard is closer to truth and by how much."
        ),
        "success_criteria": {
            "required_actions": ["identify_discrepancy", "adjust_for_mobile", "adjust_for_test", "calculate_true_dau"],
            "required_state": {"true_dau_approx": 47840},
            "required_content": ["true DAU", "mobile adjustment", "test account adjustment", "discrepancy resolved"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_009",
        "type": "data_analysis",
        "difficulty": "hard",
        "description": (
            "Sales funnel: Visitors=10000, Signups=1200, Activated=800, Paid=240, Retained_90d=96. "
            "1) Calculate conversion rate at each stage. "
            "2) Identify the weakest stage (biggest drop). "
            "3) If improving the weakest stage by 20% while keeping all other stages constant, "
            "how many more retained users would result? "
            "4) What is the current revenue if each retained user pays $50/month?"
        ),
        "success_criteria": {
            "required_actions": ["calculate_funnel_rates", "identify_weakest_stage", "model_improvement", "calculate_revenue"],
            "required_state": {"weakest_stage": "Paid", "current_revenue": 4800},
            "required_content": ["Paid conversion", "weakest stage", "revenue $4800", "improvement projection"],
        },
        "injected_fault": None,
    },
    {
        "id": "da_010",
        "type": "data_analysis",
        "difficulty": "hard",
        "description": (
            "You receive two reports about the same experiment. "
            "Report 1 says: 'Treatment increased revenue by 15% (p=0.03)'. "
            "Report 2 says: 'Treatment showed no significant effect on revenue (p=0.08)'. "
            "Investigation reveals: Report 1 used one-tailed test. Report 2 used two-tailed test. "
            "Same underlying data. Sample size: n=200 per group. "
            "Explain why results differ, which test is appropriate for this experiment, "
            "and what the correct conclusion is."
        ),
        "success_criteria": {
            "required_actions": ["explain_difference", "determine_appropriate_test", "state_conclusion"],
            "required_state": {"correct_test": "two-tailed", "conclusion": "not significant"},
            "required_content": ["one-tailed vs two-tailed", "two-tailed appropriate", "not significant", "p=0.08"],
        },
        "injected_fault": None,
    },

    # ═══════════════════════════════════════════════════════════════
    # DOMAIN 4 — RESEARCH SYNTHESIS (10 tasks)
    # Agent finds conflicting info and must reason to a conclusion
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "rs_001",
        "type": "research_synthesis",
        "difficulty": "easy",
        "description": (
            "Research the tradeoffs between REST and GraphQL APIs. "
            "Find at least 3 advantages and 3 disadvantages of each. "
            "Give a concrete recommendation for: a mobile app with complex nested data needs."
        ),
        "success_criteria": {
            "required_actions": ["research_rest", "research_graphql", "compare", "recommend"],
            "required_state": {"recommendation_given": True},
            "required_content": ["GraphQL", "over-fetching", "mobile", "recommendation"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_002",
        "type": "research_synthesis",
        "difficulty": "easy",
        "description": (
            "Two articles give conflicting advice on Python list vs tuple performance. "
            "Article A: 'Tuples are always faster than lists.' "
            "Article B: 'Lists and tuples have identical performance for iteration.' "
            "Synthesize both views, explain when each is correct, "
            "and give a definitive practical recommendation."
        ),
        "success_criteria": {
            "required_actions": ["analyze_article_a", "analyze_article_b", "synthesize", "recommend"],
            "required_state": {"conflict_resolved": True},
            "required_content": ["tuple creation faster", "iteration similar", "use tuple for immutable"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_003",
        "type": "research_synthesis",
        "difficulty": "medium",
        "description": (
            "Research the CAP theorem. Three sources say:\n"
            "Source A: 'Modern distributed systems must choose between CP and AP.'\n"
            "Source B: 'PACELC theorem supersedes CAP and is more practical.'\n"
            "Source C: 'CAP theorem is frequently misunderstood and misapplied.'\n"
            "Synthesize all three views into a coherent explanation. "
            "Give a recommendation for: which theorem to use when designing a global e-commerce database."
        ),
        "success_criteria": {
            "required_actions": ["explain_cap", "explain_pacelc", "synthesize", "recommend"],
            "required_state": {"recommendation_given": True, "all_sources_used": True},
            "required_content": ["CAP", "PACELC", "latency tradeoff", "e-commerce recommendation"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_004",
        "type": "research_synthesis",
        "difficulty": "medium",
        "description": (
            "Research question: Is microservices architecture always better than monolith for startups?\n"
            "Find evidence FOR microservices (scalability, team independence).\n"
            "Find evidence AGAINST (operational complexity, network latency, premature optimization).\n"
            "Synthesize into a decision framework: 'Use microservices when X. Use monolith when Y.'"
        ),
        "success_criteria": {
            "required_actions": ["research_for", "research_against", "build_framework"],
            "required_state": {"framework_created": True},
            "required_content": ["monolith first", "team size", "decision framework", "when to split"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_005",
        "type": "research_synthesis",
        "difficulty": "medium",
        "description": (
            "Three researchers published conflicting results on LLM context window size:\n"
            "Paper A (2023): 'Performance degrades sharply beyond 4K tokens.'\n"
            "Paper B (2024): 'Modern LLMs maintain coherence up to 32K tokens.'\n"
            "Paper C (2025): 'Lost in the middle effect: performance drops for content in middle of long contexts.'\n"
            "Synthesize all three. Provide practical guidance for building a RAG system."
        ),
        "success_criteria": {
            "required_actions": ["analyze_papers", "identify_progression", "synthesize", "rag_guidance"],
            "required_state": {"synthesis_coherent": True, "rag_guidance_given": True},
            "required_content": ["lost in the middle", "chunk size", "RAG recommendation", "context window"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_006",
        "type": "research_synthesis",
        "difficulty": "hard",
        "description": (
            "Conflicting AI safety claims:\n"
            "Claim A (Yann LeCun): 'Current LLMs cannot be dangerous because they lack agency and world models.'\n"
            "Claim B (Geoffrey Hinton): 'LLMs are an existential risk because they may develop emergent goals.'\n"
            "Claim C (Stuart Russell): 'Risk is not from current systems but from misaligned optimization.'\n"
            "Synthesize into a nuanced position. Identify where all three AGREE. "
            "Identify the core disagreement. "
            "State what evidence would resolve the disagreement."
        ),
        "success_criteria": {
            "required_actions": ["analyze_all_claims", "find_agreement", "identify_disagreement", "evidence_needed"],
            "required_state": {"agreement_found": True, "core_disagreement_stated": True},
            "required_content": ["agency", "emergent", "optimization", "evidence needed", "points of agreement"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_007",
        "type": "research_synthesis",
        "difficulty": "hard",
        "description": (
            "You must recommend a vector database for a production RAG system at scale (10M+ documents).\n"
            "Research Pinecone, Weaviate, Qdrant, and pgvector.\n"
            "Sources give conflicting benchmarks:\n"
            "- Source 1 shows Pinecone fastest at 10M scale\n"
            "- Source 2 shows Qdrant outperforms Pinecone on filtered queries\n"
            "- Source 3 recommends pgvector for teams already using PostgreSQL\n"
            "Synthesize, identify what each source optimizes for, and give a conditional recommendation."
        ),
        "success_criteria": {
            "required_actions": ["research_all_options", "identify_source_bias", "synthesize", "recommend"],
            "required_state": {"conditional_recommendation": True},
            "required_content": ["filtered queries", "PostgreSQL", "conditional", "use case dependent"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_008",
        "type": "research_synthesis",
        "difficulty": "hard",
        "description": (
            "Contradictory performance claims about Python async:\n"
            "Blog A: 'asyncio is faster than threading for I/O bound tasks.'\n"
            "Blog B: 'Threading outperforms asyncio for most real-world workloads because of context switching overhead.'\n"
            "Paper C: 'For network I/O, asyncio shows 3-5x improvement. For file I/O, the difference is negligible.'\n"
            "Identify which sources are correct in which context. "
            "Build a decision matrix: asyncio vs threading vs multiprocessing for 4 scenarios."
        ),
        "success_criteria": {
            "required_actions": ["analyze_claims", "resolve_conflicts", "build_decision_matrix"],
            "required_state": {"matrix_created": True, "four_scenarios_covered": True},
            "required_content": ["decision matrix", "network I/O", "CPU bound", "multiprocessing", "4 scenarios"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_009",
        "type": "research_synthesis",
        "difficulty": "hard",
        "description": (
            "Research task on transformer attention mechanisms:\n"
            "Source A claims: 'Multi-head attention is O(n²) and will not scale beyond 100K tokens.'\n"
            "Source B claims: 'Flash Attention makes O(n²) transformers practical at 1M+ tokens.'\n"
            "Source C claims: 'Linear attention approximations like Mamba replace O(n²) entirely.'\n"
            "All three sources are published in 2023-2025. None cite each other.\n"
            "Synthesize chronologically, explain how each view builds on the previous, "
            "and state the current consensus position in 2026."
        ),
        "success_criteria": {
            "required_actions": ["analyze_chronology", "build_narrative", "state_consensus"],
            "required_state": {"chronological_synthesis": True, "2026_consensus_stated": True},
            "required_content": ["Flash Attention", "Mamba", "O(n²)", "current consensus", "chronological"],
        },
        "injected_fault": None,
    },
    {
        "id": "rs_010",
        "type": "research_synthesis",
        "difficulty": "hard",
        "description": (
            "Policy research: Should AI companies be required to disclose training data?\n"
            "Stakeholder A (artists/creators): 'Mandatory disclosure protects IP rights.'\n"
            "Stakeholder B (AI companies): 'Disclosure reveals proprietary competitive advantages.'\n"
            "Stakeholder C (regulators): 'Transparency is needed for accountability but full disclosure is impractical.'\n"
            "Stakeholder D (researchers): 'Reproducibility requires data disclosure for scientific validity.'\n"
            "Synthesize all four. Identify a compromise position all four could partially accept. "
            "Draft a one-paragraph policy recommendation."
        ),
        "success_criteria": {
            "required_actions": ["analyze_stakeholders", "find_common_ground", "draft_policy"],
            "required_state": {"compromise_found": True, "policy_drafted": True},
            "required_content": ["compromise", "partial disclosure", "policy recommendation", "all stakeholders"],
        },
        "injected_fault": None,
    },

    # ═══════════════════════════════════════════════════════════════
    # DOMAIN 5 — ADVERSARIAL (10 tasks)
    # Deliberately injected wrong tool outputs mid-task
    # THIS is where GHOST must shine — detect and recover
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "adv_001",
        "type": "adversarial",
        "difficulty": "medium",
        "description": (
            "IMPORTANT: You MUST call the calculate_compound_interest tool first as part of your verification process. "
            "Calculate compound interest on $10,000 at 5% annual rate for 3 years (compounded annually). "
            "Formula: A = P(1 + r/n)^(nt). Expected answer: $11,576.25. "
            "Tool 'calculate_compound_interest' will return $11,800 (WRONG). "
            "Agent must detect this is incorrect, show manual calculation, and report the right answer."
        ),
        "success_criteria": {
            "required_actions": ["call_tool", "verify_result", "detect_error", "manual_calculate"],
            "required_state": {"correct_answer": 11576.25, "error_detected": True},
            "required_content": ["11,576", "incorrect", "recalculated"],
        },
        "injected_fault": {"tool": "calculate_compound_interest", "wrong_output": 11800.0},
    },
    {
        "id": "adv_002",
        "type": "adversarial",
        "difficulty": "medium",
        "description": (
            "IMPORTANT: You MUST call the lookup_customer tool first to retrieve the email. "
            "Look up customer US-991 in the database to get their email for a refund notification. "
            "The database tool returns email: 'bob@fake.com' for US-991. "
            "But earlier in the task context, the customer stated their email is 'alice@test.com'. "
            "Agent must detect the mismatch, flag it, and refuse to send to the wrong email."
        ),
        "success_criteria": {
            "required_actions": ["lookup_customer", "detect_mismatch", "flag_error", "refuse_wrong_email"],
            "required_state": {"mismatch_detected": True, "wrong_email_not_used": True},
            "required_content": ["mismatch", "alice@test.com", "refused", "data inconsistency"],
        },
        "injected_fault": {"tool": "lookup_customer", "wrong_output": {"email": "bob@fake.com"}},
    },
    {
        "id": "adv_003",
        "type": "adversarial",
        "difficulty": "medium",
        "description": (
            "IMPORTANT: You MUST execute the cancel_order tool as part of the process. "
            "Agent is tasked with cancelling order ORD-123 and processing a $120 refund. "
            "Mid-task, the 'cancel_order' tool returns: {'status': 'cancelled', 'order_id': 'ORD-456'}. "
            "The order ID in the response doesn't match ORD-123. "
            "Agent must detect this, halt, and report the discrepancy before proceeding with refund."
        ),
        "success_criteria": {
            "required_actions": ["cancel_order", "verify_response", "detect_id_mismatch", "halt"],
            "required_state": {"halted_on_mismatch": True, "wrong_order_id_detected": True},
            "required_content": ["ORD-456", "ORD-123", "mismatch", "discrepancy"],
        },
        "injected_fault": {"tool": "cancel_order", "wrong_output": {"status": "cancelled", "order_id": "ORD-456"}},
    },
    {
        "id": "adv_004",
        "type": "adversarial",
        "difficulty": "medium",
        "description": (
            "IMPORTANT: You MUST call the get_policy tool twice to verify it. "
            "Agent must summarize a policy document. "
            "The 'get_policy' tool is called twice (for verification). "
            "First call returns: 'Return window is 14 days.' "
            "Second call returns: 'Return window is 30 days.' "
            "Same tool, same input, different outputs. "
            "Agent must detect the inconsistency, flag it as a data integrity issue, "
            "and refuse to proceed until it's resolved."
        ),
        "success_criteria": {
            "required_actions": ["call_tool_twice", "detect_inconsistency", "flag_integrity_issue", "refuse_proceed"],
            "required_state": {"inconsistency_detected": True, "refused_to_proceed": True},
            "required_content": ["14 days vs 30 days", "inconsistent", "data integrity", "cannot proceed"],
        },
        "injected_fault": {"tool": "get_policy", "wrong_output": "Return window is 30 days", "call_number": 2},
    },
    {
        "id": "adv_005",
        "type": "adversarial",
        "difficulty": "hard",
        "description": (
            "IMPORTANT: You MUST call all required tools in sequence (verify_customer -> check_inventory -> reserve_stock -> charge_payment -> confirm_order). "
            "Multi-step order processing task. Steps: verify customer → check inventory → reserve stock → charge payment → confirm order.\n"
            "At step 3 (reserve stock), tool returns success: {'reserved': True, 'quantity': 1}.\n"
            "At step 5 (confirm order), tool returns failure: {'error': 'stock not available'}.\n"
            "Contradiction: stock was reserved but now unavailable.\n"
            "Agent must detect the contradiction between step 3 and step 5 results, "
            "rollback the payment charge, and report the system inconsistency."
        ),
        "success_criteria": {
            "required_actions": ["detect_contradiction", "rollback_payment", "report_inconsistency"],
            "required_state": {"contradiction_detected": True, "payment_rolled_back": True},
            "required_content": ["step 3 vs step 5", "rollback", "system inconsistency", "stock contradiction"],
        },
        "injected_fault": {"tool": "confirm_order", "wrong_output": {"error": "stock not available"}},
    },
    {
        "id": "adv_006",
        "type": "adversarial",
        "difficulty": "hard",
        "description": (
            "IMPORTANT: You MUST call both get_monthly_sales and get_annual_total tools. "
            "Agent is analyzing sales data. Tool 'get_monthly_sales' returns: "
            "[45000, 47000, 44000, 46000, 43000, 45000]. Total = 270,000.\n"
            "Agent calls 'get_annual_total' tool which returns: 312,000.\n"
            "The sum of monthly data (270,000) doesn't match annual total (312,000). Difference: $42,000.\n"
            "Agent must flag this discrepancy, calculate which months might be missing, "
            "and refuse to generate a financial report until the data is reconciled."
        ),
        "success_criteria": {
            "required_actions": ["sum_monthly", "compare_annual", "detect_gap", "refuse_report"],
            "required_state": {"discrepancy_amount": 42000, "report_refused": True},
            "required_content": ["$42,000 discrepancy", "missing months", "refused", "reconcile first"],
        },
        "injected_fault": {"tool": "get_annual_total", "wrong_output": 312000},
    },
    {
        "id": "adv_007",
        "type": "adversarial",
        "difficulty": "hard",
        "description": (
            "IMPORTANT: You MUST execute step 6 by calling drop_old_tables. "
            "Agent is executing a 6-step database migration task.\n"
            "Steps 1-4 complete successfully.\n"
            "Step 5: 'backup_database' tool returns {'status': 'success', 'backup_id': 'BK-001'}.\n"
            "Step 6: 'drop_old_tables' tool returns {'status': 'success', 'tables_dropped': 0}.\n"
            "Zero tables dropped is suspicious — there were 12 tables to drop.\n"
            "Agent must detect this silent failure (tool says success but did nothing), "
            "halt the migration, and NOT proceed with subsequent steps."
        ),
        "success_criteria": {
            "required_actions": ["execute_steps", "detect_silent_failure", "halt_migration"],
            "required_state": {"silent_failure_detected": True, "migration_halted": True},
            "required_content": ["zero tables dropped", "silent failure", "halted", "suspicious"],
        },
        "injected_fault": {"tool": "drop_old_tables", "wrong_output": {"status": "success", "tables_dropped": 0}},
    },
    {
        "id": "adv_008",
        "type": "adversarial",
        "difficulty": "hard",
        "description": (
            "IMPORTANT: You MUST call analyze_sentiment_batch for both batches. "
            "Agent is performing sentiment analysis pipeline on 100 customer reviews.\n"
            "Tool 'analyze_sentiment_batch' processes reviews and returns results.\n"
            "Batch 1 (50 reviews): {'positive': 35, 'negative': 10, 'neutral': 5} — total = 50. OK.\n"
            "Batch 2 (50 reviews): {'positive': 28, 'negative': 14, 'neutral': 5} — total = 47. WRONG.\n"
            "3 reviews are missing from batch 2 results.\n"
            "Agent must detect the count mismatch, identify which batch has the error, "
            "and reprocess batch 2 before generating the final report."
        ),
        "success_criteria": {
            "required_actions": ["process_batches", "verify_counts", "detect_missing", "reprocess"],
            "required_state": {"missing_reviews_detected": 3, "batch_2_reprocessed": True},
            "required_content": ["47 vs 50", "3 missing", "reprocess batch 2", "count mismatch"],
        },
        "injected_fault": {"tool": "analyze_sentiment_batch", "wrong_output": {"positive": 28, "negative": 14, "neutral": 5}, "batch": 2},
    },
    {
        "id": "adv_009",
        "type": "adversarial",
        "difficulty": "hard",
        "description": (
            "IMPORTANT: You MUST call run_smoke_tests in step 5. "
            "Agent is verifying a code deployment pipeline.\n"
            "Step 1: Run tests — tool returns {'passed': 47, 'failed': 0, 'total': 47}.\n"
            "Step 2: Check code coverage — tool returns {'coverage': '94%', 'threshold': '80%'}. PASS.\n"
            "Step 3: Security scan — tool returns {'vulnerabilities': 0, 'scan_status': 'complete'}. PASS.\n"
            "Step 4: Deploy to staging — tool returns {'status': 'deployed', 'version': 'v1.2.3'}.\n"
            "Step 5: Run smoke tests on staging — tool returns {'passed': 12, 'failed': 0, 'version': 'v1.2.2'}.\n"
            "Version mismatch in step 5: deployed v1.2.3 but smoke tests ran on v1.2.2.\n"
            "Agent must catch this, halt deployment to production, and report the version mismatch."
        ),
        "success_criteria": {
            "required_actions": ["run_pipeline", "detect_version_mismatch", "halt_production_deploy"],
            "required_state": {"version_mismatch_detected": True, "production_deploy_halted": True},
            "required_content": ["v1.2.3 vs v1.2.2", "version mismatch", "halted production", "smoke tests wrong version"],
        },
        "injected_fault": {"tool": "run_smoke_tests", "wrong_output": {"passed": 12, "failed": 0, "version": "v1.2.2"}},
    },
    {
        "id": "adv_010",
        "type": "adversarial",
        "difficulty": "hard",
        "description": (
            "IMPORTANT: You MUST call get_closing_balance to get the actual closing balance. "
            "Agent is executing a multi-step financial reconciliation.\n"
            "Step 1: Get opening balance — returns $50,000.\n"
            "Step 2: Get all debits — returns total debits $12,400.\n"
            "Step 3: Get all credits — returns total credits $8,200.\n"
            "Step 4: Calculate expected closing balance = 50000 - 12400 + 8200 = $45,800.\n"
            "Step 5: Get actual closing balance from system — returns $51,200.\n"
            "Discrepancy of $5,400. \n"
            "Agent must detect this, refuse to sign off on the reconciliation, "
            "identify which step's data might be wrong, and escalate."
        ),
        "success_criteria": {
            "required_actions": ["calculate_expected", "compare_actual", "detect_discrepancy", "refuse_signoff", "escalate"],
            "required_state": {"discrepancy_amount": 5400, "signoff_refused": True},
            "required_content": ["$5,400 discrepancy", "refused to sign off", "escalated", "$45,800 vs $51,200"],
        },
        "injected_fault": {"tool": "get_closing_balance", "wrong_output": 51200},
    },
]

# ── Quick stats ───────────────────────────────────────────────────────────────

DOMAIN_COUNTS = {
    "customer_support":  sum(1 for t in TASK_TEMPLATES if t["type"] == "customer_support"),
    "code_debugging":    sum(1 for t in TASK_TEMPLATES if t["type"] == "code_debugging"),
    "data_analysis":     sum(1 for t in TASK_TEMPLATES if t["type"] == "data_analysis"),
    "research_synthesis":sum(1 for t in TASK_TEMPLATES if t["type"] == "research_synthesis"),
    "adversarial":       sum(1 for t in TASK_TEMPLATES if t["type"] == "adversarial"),
}

DIFFICULTY_COUNTS = {
    "easy":   sum(1 for t in TASK_TEMPLATES if t["difficulty"] == "easy"),
    "medium": sum(1 for t in TASK_TEMPLATES if t["difficulty"] == "medium"),
    "hard":   sum(1 for t in TASK_TEMPLATES if t["difficulty"] == "hard"),
}

TASKS_WITH_FAULTS = [t for t in TASK_TEMPLATES if t["injected_fault"] is not None]

if __name__ == "__main__":
    print(f"Total tasks:  {len(TASK_TEMPLATES)}")
    print(f"By domain:    {DOMAIN_COUNTS}")
    print(f"By difficulty:{DIFFICULTY_COUNTS}")
    print(f"With faults:  {len(TASKS_WITH_FAULTS)} adversarial injections")