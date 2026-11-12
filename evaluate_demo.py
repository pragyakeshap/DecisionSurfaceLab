\
from bounded_agent.domain_tool import (
    _calculate_delay_days,
    _check_refund_eligibility,
    _check_replacement_eligibility,
)

EXPECTED = {
    "delay_days": 6,
    "refund_eligible": False,
    "replacement_eligible": True,
    "recommended_action": "offer_replacement",
}


def check(label, actual, expected):
    ok = actual == expected
    print(
        f"{label:<28} {'PASS' if ok else 'FAIL'} "
        f"actual={actual!r} expected={expected!r}"
    )
    return ok


def main():
    delay_days = _calculate_delay_days("2026-11-01")
    refund_eligible = _check_refund_eligibility(delay_days)
    replacement_eligible = _check_replacement_eligibility(delay_days)

    if replacement_eligible:
        recommended_action = "offer_replacement"
    elif refund_eligible:
        recommended_action = "offer_refund"
    else:
        recommended_action = "continue_monitoring"

    print("\nLayered deterministic evaluation")
    print("-" * 72)
    results = [
        check("Delay calculation", delay_days, EXPECTED["delay_days"]),
        check(
            "Refund policy",
            refund_eligible,
            EXPECTED["refund_eligible"],
        ),
        check(
            "Replacement policy",
            replacement_eligible,
            EXPECTED["replacement_eligible"],
        ),
        check(
            "Recommended action",
            recommended_action,
            EXPECTED["recommended_action"],
        ),
    ]
    print("-" * 72)
    print("OVERALL:", "PASS" if all(results) else "FAIL")


if __name__ == "__main__":
    main()
