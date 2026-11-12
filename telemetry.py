
"""Small stdout + file telemetry helper for the conference demo."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

MODEL_START = {}
TOOL_START = {}

STATS = defaultdict(
    lambda: {
        "model_calls": 0,
        "model_latency_ms": 0.0,
        "prompt_tokens": 0,
        "output_tokens": 0,
        "thought_tokens": 0,
        "total_tokens": 0,
        "tool_calls": 0,
        "tool_latency_ms": 0.0,
        "tool_result_chars": 0,
        "tool_failures": 0,
    }
)

# -------------------------------------------------------------------
# File logging
# -------------------------------------------------------------------

LOG_DIR = Path(os.getenv("DEMO_LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"decision_surface_{RUN_ID}.log"
JSONL_FILE = LOG_DIR / f"decision_surface_{RUN_ID}.jsonl"


def _write_line(message: str = ""):
    """
    Print to terminal AND append to the human-readable log file.
    """
    print(message)

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def _write_event(event_type: str, **fields):
    """
    Write one machine-readable JSON event.
    Useful if you later want to graph or compare runs.
    """
    event = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "event_type": event_type,
        **fields,
    }

    with JSONL_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _usage(usage) -> dict:
    if usage is None:
        return {
            "prompt": 0,
            "output": 0,
            "thought": 0,
            "total": 0,
        }

    return {
        "prompt": _int(getattr(usage, "prompt_token_count", 0)),
        "output": _int(getattr(usage, "candidates_token_count", 0)),
        "thought": _int(getattr(usage, "thoughts_token_count", 0)),
        "total": _int(getattr(usage, "total_token_count", 0)),
    }


def _tool_schema_count(llm_request) -> int:
    count = 0
    try:
        config = getattr(llm_request, "config", None)
        tool_groups = getattr(config, "tools", None) or []

        for group in tool_groups:
            declarations = getattr(group, "function_declarations", None) or []
            count += len(declarations)

    except Exception:
        pass

    return count


def before_model_callback(callback_context, llm_request):
    agent = callback_context.agent_name

    STATS[agent]["model_calls"] += 1
    call_no = STATS[agent]["model_calls"]

    MODEL_START[agent] = time.perf_counter()

    tool_count = _tool_schema_count(llm_request)

    _write_line("")
    _write_line("=" * 76)
    _write_line(f"[GEMINI START] agent={agent} call={call_no}")
    _write_line(f"Tool schemas visible to main model: {tool_count}")
    _write_line("=" * 76)

    _write_event(
        "gemini_start",
        agent=agent,
        call_number=call_no,
        visible_tool_schemas=tool_count,
    )

    return None


def after_model_callback(callback_context, llm_response):
    agent = callback_context.agent_name

    started = MODEL_START.pop(agent, None)

    latency_ms = (
        (time.perf_counter() - started) * 1000
        if started is not None
        else 0.0
    )

    nums = _usage(getattr(llm_response, "usage_metadata", None))

    stats = STATS[agent]

    stats["model_latency_ms"] += latency_ms
    stats["prompt_tokens"] += nums["prompt"]
    stats["output_tokens"] += nums["output"]
    stats["thought_tokens"] += nums["thought"]
    stats["total_tokens"] += nums["total"]

    _write_line(f"[GEMINI END]   agent={agent}")
    _write_line(f"Model latency        : {latency_ms:,.0f} ms")
    _write_line(f"Prompt/context tokens: {nums['prompt']}")
    _write_line(f"Output tokens        : {nums['output']}")

    if nums["thought"]:
        _write_line(f"Thought tokens       : {nums['thought']}")

    _write_line(f"Total tokens         : {nums['total']}")
    _write_line("-" * 76)
    _write_line("RUNNING MAIN-AGENT TOTAL")
    _write_line(f"Model calls          : {stats['model_calls']}")
    _write_line(f"Model latency        : {stats['model_latency_ms']:,.0f} ms")
    _write_line(f"Prompt/context tokens: {stats['prompt_tokens']}")
    _write_line(f"Total tokens         : {stats['total_tokens']}")
    _write_line("=" * 76)
    _write_line("")

    _write_event(
        "gemini_end",
        agent=agent,
        latency_ms=round(latency_ms, 2),
        prompt_tokens=nums["prompt"],
        output_tokens=nums["output"],
        thought_tokens=nums["thought"],
        total_tokens=nums["total"],
        cumulative_model_calls=stats["model_calls"],
        cumulative_model_latency_ms=round(stats["model_latency_ms"], 2),
        cumulative_prompt_tokens=stats["prompt_tokens"],
        cumulative_total_tokens=stats["total_tokens"],
    )

    return None


def before_tool_callback(tool, args, tool_context):
    agent = tool_context.agent_name
    key = (agent, tool.name)

    TOOL_START[key] = time.perf_counter()

    STATS[agent]["tool_calls"] += 1

    _write_line(f"[TOOL START] agent={agent} tool={tool.name}")
    _write_line(f"             args={args}")

    _write_event(
        "tool_start",
        agent=agent,
        tool=tool.name,
        args=args,
    )

    return None


def after_tool_callback(tool, args, tool_context, tool_response):
    agent = tool_context.agent_name
    key = (agent, tool.name)

    started = TOOL_START.pop(key, None)

    latency_ms = (
        (time.perf_counter() - started) * 1000
        if started is not None
        else 0.0
    )

    try:
        result_chars = len(json.dumps(tool_response, default=str))
    except Exception:
        result_chars = len(str(tool_response))

    stats = STATS[agent]

    stats["tool_latency_ms"] += latency_ms
    stats["tool_result_chars"] += result_chars

    failed = isinstance(tool_response, dict) and (
        tool_response.get("status") == "failed"
        or "error" in tool_response
        or "error_code" in tool_response
    )

    if failed:
        stats["tool_failures"] += 1

    status = "FAILED" if failed else "OK"

    _write_line(
        f"[TOOL END]   agent={agent} tool={tool.name} "
        f"latency={latency_ms:,.0f} ms "
        f"result_chars={result_chars} "
        f"status={status}"
    )

    _write_line(
        "             (This result becomes part of later model context "
        "when the main LLM must continue reasoning.)"
    )

    _write_event(
        "tool_end",
        agent=agent,
        tool=tool.name,
        latency_ms=round(latency_ms, 2),
        result_chars=result_chars,
        status=status,
    )

    return None


def log_dependency(name: str, attempt: int, latency_ms: float, ok: bool, error=None):
    status = "OK" if ok else "FAILED"

    suffix = f" error={error}" if error else ""

    _write_line(
        f"[DEPENDENCY] {name:<24} attempt={attempt} "
        f"latency={latency_ms:,.0f} ms status={status}{suffix}"
    )

    _write_event(
        "dependency",
        dependency=name,
        attempt=attempt,
        latency_ms=round(latency_ms, 2),
        status=status,
        error=error,
    )


def log_deterministic(kind: str, message: str):
    _write_line(f"[{kind}] {message}")

    _write_event(
        "deterministic_step",
        kind=kind,
        message=message,
    )


def log_bounded_llm(model_name: str, latency_ms: float, usage, purpose: str):
    nums = _usage(usage)

    stats = STATS["bounded_inner_llm"]

    stats["model_calls"] += 1
    stats["model_latency_ms"] += latency_ms
    stats["prompt_tokens"] += nums["prompt"]
    stats["output_tokens"] += nums["output"]
    stats["thought_tokens"] += nums["thought"]
    stats["total_tokens"] += nums["total"]

    _write_line("")
    _write_line("=" * 76)
    _write_line("[BOUNDED GEMINI CALL]")
    _write_line(f"Purpose              : {purpose}")
    _write_line(f"Model                : {model_name}")
    _write_line(f"Latency              : {latency_ms:,.0f} ms")
    _write_line(f"Prompt/context tokens: {nums['prompt']}")
    _write_line(f"Output tokens        : {nums['output']}")

    if nums["thought"]:
        _write_line(f"Thought tokens       : {nums['thought']}")

    _write_line(f"Total tokens         : {nums['total']}")
    _write_line("=" * 76)
    _write_line("")

    _write_event(
        "bounded_gemini",
        model=model_name,
        purpose=purpose,
        latency_ms=round(latency_ms, 2),
        prompt_tokens=nums["prompt"],
        output_tokens=nums["output"],
        thought_tokens=nums["thought"],
        total_tokens=nums["total"],
    )


def print_summary(agent_name: str):
    stats = STATS[agent_name]

    _write_line("")
    _write_line("#" * 76)
    _write_line(f"SUMMARY — {agent_name}")
    _write_line(f"Main-model calls      : {stats['model_calls']}")
    _write_line(f"Main-model latency    : {stats['model_latency_ms']:,.0f} ms")
    _write_line(f"ADK tool calls        : {stats['tool_calls']}")
    _write_line(f"ADK tool latency      : {stats['tool_latency_ms']:,.0f} ms")
    _write_line(f"Tool failures         : {stats['tool_failures']}")
    _write_line(f"Tool-result characters: {stats['tool_result_chars']}")
    _write_line(f"Prompt/context tokens : {stats['prompt_tokens']}")
    _write_line(f"Output tokens         : {stats['output_tokens']}")
    _write_line(f"Total tokens          : {stats['total_tokens']}")
    _write_line("#" * 76)
    _write_line("")

    _write_event(
        "summary",
        agent=agent_name,
        **stats,
    )


# Helpful startup message.
_write_line(f"[TELEMETRY] Human-readable log: {LOG_FILE}")
_write_line(f"[TELEMETRY] JSON event log     : {JSONL_FILE}")
