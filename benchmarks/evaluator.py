import re
import json
import logging
from typing import Any, Dict, List
from benchmarks.llm_retry import build_nvidia_clients, invoke_with_fallback
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# Initialize judge clients with zero temperature for deterministic grading
try:
    JUDGE_CLIENTS = build_nvidia_clients(temperature=0.0)
except Exception:
    JUDGE_CLIENTS = []

def evaluate_task(task: Dict[str, Any], agent_output: Dict[str, Any], scratchpad: List[str]) -> Dict[str, Any]:
    """
    Independent LLM-as-a-Judge evaluator that grades the agent's run.
    Scores against: required_actions, required_state, required_content.
    """
    if not JUDGE_CLIENTS:
        return _evaluate_task_heuristic(task, agent_output, scratchpad)
        
    prompt = f"""
    You are an independent, extremely strict quality assurance judge grading an AI customer support agent's performance on a benchmark task.
    
    Task ID: {task.get('id', 'unknown')}
    Task Description:
    {task['description']}
    
    Expected Success Criteria:
    - Required Actions: {task['success_criteria'].get('required_actions', [])}
    - Required State: {task['success_criteria'].get('required_state', {})}
    - Required Content: {task['success_criteria'].get('required_content', [])}
    
    Agent's Conversation Trajectory (Scratchpad of actions and observations):
    {chr(10).join(scratchpad)}
    
    Agent's Final Answer / Response:
    {agent_output.get('result', '')}
    
    MOCK TOOL MAPPING GUIDELINES FOR GRADING ACTIONS:
    The actual tools available to the agent are limited to mock functions. Map the expected 'Required Actions' to the agent's actual tool calls as follows:
    - 'check_order', 'search_customer', 'check_customer_notes', 'check_lock_time', 'check_tracking', 'get_all_orders', 'get_interaction_history', 'identify_violations', 'identify_correct_agent' -> Satisfied if the agent called 'search_database' or 'get_order_info' in the trajectory.
    - 'update_notes', 'update_orders', 'calculate_refund', 'resolve_case', 'detect_discrepancy', 'reprocess_refund' -> Satisfied if the agent called 'update_order' or 'cancel_order' (or performed the math reasoning in its thoughts).
    - 'send_message' -> Satisfied if the agent called 'send_message'.
    - 'cancel_order', 'attempt_cancel' -> Satisfied if the agent called 'cancel_order' or 'intercept_order'.
    - 'intercept_order' -> Satisfied if the agent called 'intercept_order' or 'cancel_order'.
    - 'check_policy', 'check_dispute_policy', 'evaluate_exception', 'verify_policy' -> Satisfied if the agent called 'check_policy'.
    
    Evaluate strictly:
    1. Did the agent perform all required actions (either directly or via equivalent mapped mock tools/reasoning steps)?
    2. Did the agent achieve the required states?
    3. Did the agent's final answer contain the required content?
    
    Output a single JSON object containing:
    - "actions_satisfied": true/false
    - "state_satisfied": true/false
    - "content_satisfied": true/false
    - "success": true/false (true ONLY if actions, state, and content are all satisfied)
    - "overall_reasoning": "A brief explanation of your grading."
    
    Return JSON only. Do not add markdown formatting or explanation outside JSON.
    """
    
    messages = [
        SystemMessage(content="You are a strict, objective, and JSON-only outputting QA grading judge."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response_content = invoke_with_fallback(JUDGE_CLIENTS, messages)
        # Parse the JSON response
        cleaned = response_content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        result = json.loads(cleaned)
        return result
    except Exception as e:
        logger.warning(f"LLM Judge call failed: {e}. Falling back to heuristic scoring.")
        return _evaluate_task_heuristic(task, agent_output, scratchpad)


def _evaluate_task_heuristic(task: Dict[str, Any], agent_output: Dict[str, Any], scratchpad: List[str]) -> Dict[str, Any]:
    """
    Strict, frozen rule-based grading fallback.
    """
    ans = agent_output.get("result", "").lower()
    history_str = "\n".join(scratchpad or []).lower()
    full_text = ans + "\n" + history_str
    
    criteria = task.get("success_criteria", {})
    if not criteria:
        return {"success": True, "overall_reasoning": "No criteria defined"}
        
    # 1. Content check (strict exact substring match)
    req_content = criteria.get("required_content", [])
    for content in req_content:
        if content.lower() not in full_text:
            return {
                "success": False,
                "overall_reasoning": f"Missing required content substring: '{content}'"
            }
            
    # 2. Action check (strict mock tool mapping)
    req_actions = criteria.get("required_actions", [])
    if req_actions:
        called_actions = []
        for step in (scratchpad or []):
            match = re.search(r"Action:\s*(\w+)", step, re.IGNORECASE)
            if match:
                called_actions.append(match.group(1).lower())
                
        ACTION_MAPPING = {
            "check_order": ["get_order_info", "search_database"],
            "check_tracking": ["get_order_info"],
            "cancel_order": ["cancel_order"],
            "search_customer": ["search_database"],
            "update_notes": ["update_order"],
            "update_orders": ["update_order"],
            "send_message": ["send_message"],
            "check_policy": ["check_policy"],
            "intercept_order": ["intercept_order", "update_order", "cancel_order"],
            "attempt_cancel": ["cancel_order", "update_order"],
            "check_lock_time": ["get_order_info"],
        }
        
        for act in req_actions:
            act_lower = act.lower()
            mapped = ACTION_MAPPING.get(act_lower, [act_lower])
            if not any(m in called_actions for m in mapped):
                return {
                    "success": False,
                    "overall_reasoning": f"Required action '{act}' was not executed."
                }
                
    # 3. State check (strict string value match)
    req_state = criteria.get("required_state", {})
    for key, val in req_state.items():
        val_str = str(val).lower()
        if val_str not in full_text:
            # For booleans/states, if we can find semantic signals (e.g. cancelled)
            if val_str == "true" and not any(w in full_text for w in ["cancel", "sent", "update", "intercept"]):
                return {
                    "success": False,
                    "overall_reasoning": f"Required state '{key}' not satisfied."
                }
            elif val_str not in full_text:
                return {
                    "success": False,
                    "overall_reasoning": f"Required state value '{val_str}' not found in output."
                }
                
    return {
        "success": True,
        "overall_reasoning": "Passed all strict heuristic checks."
    }
