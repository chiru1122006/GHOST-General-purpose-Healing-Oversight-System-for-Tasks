#!/usr/bin/env python3
"""
GHOST Demo — Simplest possible working example.

This script demonstrates both ways to use GHOST with an AI agent:
  1. Using the @ghost_monitor decorator (3 lines of code)
  2. Using the GHOSTCallbackHandler directly (more control)

This demo uses a custom version-agnostic SimpleAgentExecutor to execute
ReAct agent loops, ensuring compatibility with all LangChain package versions.

Prerequisites:
  - NVIDIA_API_KEY_1/NVIDIA_API_KEY1 or NVIDIA_API_KEY_2/NVIDIA_API_KEY2 must be set in .env
  - pip install -r requirements.txt

Run with:
    python examples/demo_simple.py
"""

from __future__ import annotations

import os
import re
import sys

# Add project root to path so imports work when running from examples/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.tools import Tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core import GHOSTCallbackHandler, ghost_monitor
from benchmarks.llm_retry import build_nvidia_clients, invoke_with_fallback

# ─────────────────────────────────────────────
# Check for API key
# ─────────────────────────────────────────────

llm_clients = build_nvidia_clients(model="openai/gpt-oss-120b")
if not llm_clients:
    print("❌ NVIDIA_API_KEY_1/NVIDIA_API_KEY1 or NVIDIA_API_KEY_2/NVIDIA_API_KEY2 not set in .env")
    print("   Copy .env.example to .env and add your NVIDIA NIM API keys.")
    sys.exit(1)

# ─────────────────────────────────────────────
# Mock tools (simple functions that return fake data)
# ─────────────────────────────────────────────


def _search_web(query: str) -> str:
    """Search the web for information."""
    return (
        f"Search results for '{query}': "
        "1. Recent advances in AI agents (2026) — arxiv.org "
        "2. LangChain agent patterns — blog.langchain.dev "
        "3. Self-correcting AI systems — openai.com/research"
    )


def _read_page(url: str) -> str:
    """Read and extract content from a web page."""
    return (
        f"Content from {url}: This article discusses how modern AI agents "
        "use tool-calling patterns to accomplish complex tasks. Key findings "
        "include improved reliability through self-correction mechanisms and "
        "trajectory monitoring. The research shows a 40% reduction in failure "
        "rates when agents are equipped with failure-aware middleware."
    )


def _extract_info(text: str) -> str:
    """Extract key information from text."""
    return (
        "Extracted key points: "
        "1. AI agents improved reliability by 40% with monitoring middleware. "
        "2. Self-correction reduces repetitive failures. "
        "3. Trajectory scoring enables real-time drift detection."
    )


def _summarize(text: str) -> str:
    """Summarize the given text."""
    return (
        "Summary: AI agent research in 2026 shows significant advances in "
        "reliability through failure-aware middleware systems. Key breakthroughs "
        "include trajectory monitoring, MAST-based failure classification, and "
        "automated recovery strategies that reduce failure rates by 40%."
    )


def _write_output(content: str) -> str:
    """Write output to a file."""
    output_path = "examples/output.txt"
    os.makedirs("examples", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Output written to {output_path}"


tools = [
    Tool(name="search_web", func=_search_web, description="Search the web for information on a topic"),
    Tool(name="read_page", func=_read_page, description="Read and extract content from a web page URL"),
    Tool(name="extract_info", func=_extract_info, description="Extract key information and data points from text"),
    Tool(name="summarize", func=_summarize, description="Summarize text into a concise paragraph"),
    Tool(name="write_output", func=_write_output, description="Write final output content to a file"),
]

# ─────────────────────────────────────────────
# Custom Version-Agnostic Agent Executor
# ─────────────────────────────────────────────


class SimpleAgentExecutor:
    """
    A lightweight, robust ReAct agent executor.
    
    This executes a ReAct decision loop using the provided LLM and tools,
    firing GHOST callback handler hooks at every step. This makes GHOST monitoring
    independent of specific LangChain package configurations.
    """

    def __init__(self, llm_clients: list[ChatOpenAI], tools: list[Tool], max_iterations: int = 8):
        self.llm_clients = llm_clients
        self.tools = {t.name: t for t in tools}
        self.max_iterations = max_iterations

    def invoke(self, inputs: dict, config: dict = None) -> dict:
        callbacks = config.get("callbacks", []) if config else []
        query = inputs.get("input", "")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        scratchpad = []

        print(f"\n[Agent] Solving task: '{query}'")

        for iteration in range(self.max_iterations):
            # Check for pending GHOST recovery injection
            ghost_injection = ""
            for cb in callbacks:
                if hasattr(cb, "pending_injection") and cb.pending_injection:
                    ghost_injection = f"\n\n{cb.pending_injection}\n"
                    cb.pending_injection = None  # Consume the injection

            system_prompt = (
                f"You are a ReAct AI agent. You have access to the following tools:\n"
                f"{tools_desc}\n\n"
                f"MANDATORY RULES:\n"
                f"1. Respond in exactly ONE of these two formats:\n"
                f"Action: <tool_name>\n"
                f"Action Input: <tool_input>\n"
                f"OR:\n"
                f"Final Answer: <your final answer summary>\n\n"
                f"2. BUDGET & COMPLETION RULES:\n"
                f"- Gather information by calling 'search_web', 'read_page', and/or 'extract_info' in your first 2-3 steps.\n"
                f"- Once you have gathered sufficient information, you MUST call the 'summarize' tool next.\n"
                f"- You are NOT allowed to output 'Final Answer:' until you have called the 'summarize' tool.\n"
                f"- Immediately after calling 'summarize', you MUST stop calling tools and output your final answer as: 'Final Answer: <the summary result from the tool>'."
            )

            user_prompt = (
                f"Objective: {query}\n"
                f"{ghost_injection}\n"
                f"Previous history of actions and tool outputs:\n" + "\n".join(scratchpad) + "\n\n"
                f"Next step (thought and action or final answer):"
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Call LLM compatibly
            response = invoke_with_fallback(self.llm_clients, messages)

            # Print the agent's thought process/raw response
            print(f"\n[Agent Raw Response]:\n{response}\n")

            # Parse action or final answer (case-insensitive)
            action_match = re.search(r"Action:\s*(\w+)", response, re.IGNORECASE)
            input_match = re.search(r"Action\s*Input:\s*(.+)", response, re.IGNORECASE)
            final_match = re.search(r"Final\s*Answer:\s*(.+)", response, re.IGNORECASE | re.DOTALL)

            if final_match:
                final_answer = final_match.group(1).strip()
                for cb in callbacks:
                    if hasattr(cb, "on_agent_finish"):
                        cb.on_agent_finish(final_answer)
                return {"output": final_answer}

            if action_match and input_match:
                tool_name = action_match.group(1).strip()
                tool_input = input_match.group(1).strip()

                tool = self.tools.get(tool_name)

                # Trigger start callback
                for cb in callbacks:
                    if hasattr(cb, "on_tool_start"):
                        cb.on_tool_start({"name": tool_name}, tool_input)

                if not tool:
                    # Tool hallucination
                    error_msg = f"Tool '{tool_name}' not found."
                    for cb in callbacks:
                        if hasattr(cb, "on_tool_error"):
                            cb.on_tool_error(ValueError(error_msg))
                    scratchpad.append(f"Action: {tool_name}\nObservation: ERROR: {error_msg}")
                    continue

                try:
                    # Run tool
                    output = tool.func(tool_input)
                    # Trigger end callback
                    for cb in callbacks:
                        if hasattr(cb, "on_tool_end"):
                            cb.on_tool_end(output)
                    scratchpad.append(f"Action: {tool_name}\nObservation: {output}")

                    # Auto-finalize when a terminal tool (summarize, write_output) is executed
                    if tool_name in ["summarize", "write_output"]:
                        final_answer = f"Generated Summary:\n{output}"
                        for cb in callbacks:
                            if hasattr(cb, "on_agent_finish"):
                                cb.on_agent_finish(final_answer)
                        return {"output": final_answer}
                except Exception as e:
                    # Trigger error callback
                    for cb in callbacks:
                        if hasattr(cb, "on_tool_error"):
                            cb.on_tool_error(e)
                    scratchpad.append(f"Action: {tool_name}\nObservation: ERROR: {e}")
            else:
                error_msg = "Could not parse Action/Action Input or Final Answer from LLM response."
                scratchpad.append(f"Observation: ERROR: {error_msg}")
                for cb in callbacks:
                    if hasattr(cb, "on_tool_error"):
                        cb.on_tool_error(ValueError(error_msg))

        final_answer = "Max iterations reached without final answer."
        for cb in callbacks:
            if hasattr(cb, "on_agent_finish"):
                cb.on_agent_finish(final_answer)
        return {"output": final_answer}


# Initialize our executor
agent_executor = SimpleAgentExecutor(llm_clients, tools, max_iterations=8)

# ─────────────────────────────────────────────
# PATTERN 1: Using the @ghost_monitor decorator
# ─────────────────────────────────────────────


@ghost_monitor(
    task_type="web_research",
    objective="Research 2026 AI agent breakthroughs and write a summary",
)
def run_with_decorator(query: str, **kwargs) -> dict:
    """Run the agent with GHOST monitoring via decorator."""
    return agent_executor.invoke({"input": query}, **kwargs)


# ─────────────────────────────────────────────
# PATTERN 2: Using the handler directly
# ─────────────────────────────────────────────


def run_with_handler(query: str) -> dict:
    """Run the agent with GHOST monitoring via direct handler."""
    handler = GHOSTCallbackHandler(
        task_type="web_research",
        objective="Research 2026 AI agent breakthroughs and write a summary",
    )
    result = agent_executor.invoke(
        {"input": query},
        config={"callbacks": [handler]},
    )
    print("\n📋 Session Summary:")
    summary = handler.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    return result


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  GHOST Demo — AI Agent Monitoring")
    print("=" * 60)
    print()
    print("Running Pattern 1: @ghost_monitor decorator")
    print("-" * 60)

    try:
        result = run_with_decorator(
            "Research the latest 2026 AI agent breakthroughs and summarize the key findings"
        )
        print(f"\n📝 Agent output:\n{result.get('output', 'No output')}")
    except Exception as e:
        print(f"\n❌ Agent error: {e}")
        print("   This is expected if NVIDIA NIM is rate-limited or unavailable.")
        print("   The important thing is that GHOST monitoring was active.")

    print()
    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)
