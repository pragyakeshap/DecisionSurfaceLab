\
from __future__ import annotations

import os
import time
from datetime import date

from google import genai
from google.genai import types

from telemetry import (
    log_bounded_llm,
    log_dependency,
    log_deterministic,
)
from .data import (
    ACTIVE_INCIDENTS,
    CARRIER_EVENTS,
    ORDERS,
    REFUND_POLICY,
    REPLACEMENT_POLICY,
    SHIPMENTS,
)

TODAY = date(2026, 11, 7)
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
LATENCY_MS = int(os.getenv("DEMO_DEPENDENCY_LATENCY_MS", "200"))
FAIL_CARRIER_ONCE = os.getenv("DEMO_FAIL_CARRIER_ONCE", "false").lower() == "true"
_carrier_failed_once = False


def _dependency(name, work, *, retry_once=False):
    global _carrier_failed_once

    max_attempts = 2 if retry_once else 1
    last_error = None

    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        time.sleep(LATENCY_MS / 1000)

        should_fail = (
            retry_once
            and FAIL_CARRIER_ONCE
            and not _carrier_failed_once
            and attempt == 1
        )

        if should_fail:
            _carrier_failed_once = True
            latency_ms = (time.perf_counter() - started) * 1000
            last_error = "simulated carrier timeout"
            log_dependency(name, attempt, latency_ms, False, last_error)
            continue

        result = work()
        latency_ms = (time.perf_counter() - started) * 1000
        log_dependency(name, attempt, latency_ms, True)
        return result

    raise RuntimeError(last_error or f"{name} failed")


def _get_order(order_id: str) -> dict:
    return _dependency("Order API", lambda: ORDERS.get(order_id, {}))


def _get_shipment(shipment_id: str) -> dict:
    return _dependency("Shipment API", lambda: SHIPMENTS.get(shipment_id, {}))


def _get_carrier_events(shipment_id: str) -> list[dict]:
    return _dependency(
        "Carrier API",
        lambda: CARRIER_EVENTS.get(shipment_id, []),
        retry_once=True,
    )


def _get_active_incidents() -> list[dict]:
    return _dependency("Incident API", lambda: ACTIVE_INCIDENTS)


def _calculate_delay_days(promised_delivery_date: str) -> int:
    promised = date.fromisoformat(promised_delivery_date)
    delay_days = max((TODAY - promised).days, 0)
    log_deterministic(
        "CODE",
        f"delay calculation: {TODAY.isoformat()} - "
        f"{promised_delivery_date} = {delay_days} days",
    )
    return delay_days


def _check_refund_eligibility(delay_days: int) -> bool:
    eligible = delay_days >= REFUND_POLICY["minimum_delay_days"]
    log_deterministic(
        "RULE",
        f"refund: {delay_days} >= "
        f"{REFUND_POLICY['minimum_delay_days']} -> {eligible}",
    )
    return eligible


def _check_replacement_eligibility(delay_days: int) -> bool:
    eligible = delay_days >= REPLACEMENT_POLICY["minimum_delay_days"]
    log_deterministic(
        "RULE",
        f"replacement: {delay_days} >= "
        f"{REPLACEMENT_POLICY['minimum_delay_days']} -> {eligible}",
    )
    return eligible


def _interpret_carrier_note(note: str) -> str:
    """One narrow semantic task that genuinely needs interpretation."""
    client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )

    prompt = f"""
Classify this carrier note into exactly one category:
NORMAL
DELAY
LOST
DAMAGED

Return only the category name.

Carrier note:
{note}
"""

    started = time.perf_counter()
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=10,
            ),
        )
    finally:
        client.close()

    latency_ms = (time.perf_counter() - started) * 1000

    log_bounded_llm(
        MODEL_NAME,
        latency_ms,
        getattr(response, "usage_metadata", None),
        "Classify the unstructured carrier note",
    )

    classification = (response.text or "").strip().upper()
    if classification not in {"NORMAL", "DELAY", "LOST", "DAMAGED"}:
        classification = "DELAY"

    return classification


def investigate_delivery_issue(order_id: str) -> dict:
    """
    High-level business capability.

    The main agent sees only this function. Internal sequencing, retries,
    calculations, policy rules, and bounded semantic reasoning stay inside it.
    """
    started = time.perf_counter()

    try:
        order = _get_order(order_id)
        if not order:
            return {
                "status": "failed",
                "error_code": "ORDER_NOT_FOUND",
                "order_id": order_id,
            }

        shipment = _get_shipment(order["shipment_id"])
        if not shipment:
            return {
                "status": "failed",
                "error_code": "SHIPMENT_NOT_FOUND",
                "order_id": order_id,
            }

        events = _get_carrier_events(shipment["shipment_id"])
        note = events[-1]["note"] if events else ""

        delay_days = _calculate_delay_days(
            order["promised_delivery_date"]
        )
        refund_eligible = _check_refund_eligibility(delay_days)
        replacement_eligible = _check_replacement_eligibility(delay_days)

        classification = (
            _interpret_carrier_note(note) if note else "NORMAL"
        )

        incidents = _get_active_incidents()
        matching_incident = next(
            (
                incident
                for incident in incidents
                if incident["type"] == "WEATHER"
                and classification == "DELAY"
            ),
            None,
        )

        likely_cause = (
            "Severe weather and carrier backlog"
            if matching_incident
            else "No confirmed operational incident"
        )

        if replacement_eligible:
            recommended_action = "offer_replacement"
        elif refund_eligible:
            recommended_action = "offer_refund"
        else:
            recommended_action = "continue_monitoring"

        result = {
            "status": "success",
            "issue": "missing_or_stalled_delivery",
            "order_id": order_id,
            "shipment_id": shipment["shipment_id"],
            "shipment_status": shipment["status"],
            "delay_days": delay_days,
            "active_incident": (
                matching_incident["incident_id"]
                if matching_incident
                else None
            ),
            "likely_cause": likely_cause,
            "refund_eligible": refund_eligible,
            "replacement_eligible": replacement_eligible,
            "recommended_action": recommended_action,
            "evidence": {
                "last_scan": shipment["last_scan"],
                "last_scan_date": shipment["last_scan_date"],
                "carrier_note_classification": classification,
            },
        }

        total_ms = (time.perf_counter() - started) * 1000
        print(
            f"[DOMAIN TOOL] investigate_delivery_issue "
            f"total_latency={total_ms:,.0f} ms"
        )
        print(
            "[DOMAIN TOOL] Returning ONE compact structured evidence object "
            "to the main model."
        )
        return result

    except Exception as exc:
        total_ms = (time.perf_counter() - started) * 1000
        print(
            f"[DOMAIN TOOL FAILURE] investigate_delivery_issue "
            f"latency={total_ms:,.0f} ms error={exc}"
        )
        return {
            "status": "failed",
            "error_code": "INVESTIGATION_FAILED",
            "message": str(exc),
        }
