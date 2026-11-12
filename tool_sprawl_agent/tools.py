\
from __future__ import annotations

import os
import time
from datetime import date

from telemetry import log_dependency
from .data import (
    ACTIVE_INCIDENTS,
    CARRIER_EVENTS,
    ORDERS,
    REFUND_POLICY,
    REPLACEMENT_POLICY,
    SHIPMENTS,
)

TODAY = date(2026, 11, 7)
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

    return {"error": last_error or f"{name} failed"}


def get_order(order_id: str) -> dict:
    """Return order details for an order ID."""
    return _dependency(
        "Order API",
        lambda: ORDERS.get(order_id, {"error": "order_not_found"}),
    )


def get_shipment(shipment_id: str) -> dict:
    """Return shipment details for a shipment ID."""
    return _dependency(
        "Shipment API",
        lambda: SHIPMENTS.get(shipment_id, {"error": "shipment_not_found"}),
    )


def get_carrier_events(shipment_id: str) -> dict:
    """Return recent carrier events and retry once after a simulated timeout."""
    return _dependency(
        "Carrier API",
        lambda: {
            "shipment_id": shipment_id,
            "events": CARRIER_EVENTS.get(shipment_id, []),
        },
        retry_once=True,
    )


def get_active_incidents(region: str) -> dict:
    """Return active operational incidents for a region."""
    def work():
        matches = [
            item
            for item in ACTIVE_INCIDENTS
            if region.lower() in item["region"].lower()
            or item["region"].lower() in region.lower()
        ]
        return {"region": region, "incidents": matches}

    return _dependency("Incident API", work)


def get_refund_policy() -> dict:
    """Return the delayed-delivery refund policy."""
    return _dependency("Policy API/refund", lambda: REFUND_POLICY)


def get_replacement_policy() -> dict:
    """Return the stalled-delivery replacement policy."""
    return _dependency("Policy API/replace", lambda: REPLACEMENT_POLICY)


def calculate_delay_days(promised_delivery_date: str) -> dict:
    """Calculate full days past the promised date."""
    promised = date.fromisoformat(promised_delivery_date)
    delay_days = max((TODAY - promised).days, 0)
    return {
        "promised_delivery_date": promised_delivery_date,
        "demo_current_date": TODAY.isoformat(),
        "delay_days": delay_days,
    }


def check_refund_eligibility(delay_days: int, minimum_delay_days: int) -> dict:
    """Apply the deterministic refund threshold."""
    return {
        "delay_days": delay_days,
        "minimum_delay_days": minimum_delay_days,
        "refund_eligible": delay_days >= minimum_delay_days,
    }


def check_replacement_eligibility(
    delay_days: int, minimum_delay_days: int
) -> dict:
    """Apply the deterministic replacement threshold."""
    return {
        "delay_days": delay_days,
        "minimum_delay_days": minimum_delay_days,
        "replacement_eligible": delay_days >= minimum_delay_days,
    }
