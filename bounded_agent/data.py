ORDERS = {
    "123": {
        "order_id": "123",
        "customer_id": "C-9001",
        "order_date": "2026-10-29",
        "promised_delivery_date": "2026-11-01",
        "shipment_id": "SHP-123",
        "order_total": 149.99,
    }
}

SHIPMENTS = {
    "SHP-123": {
        "shipment_id": "SHP-123",
        "order_id": "123",
        "status": "STALLED",
        "last_scan": "Austin Regional Facility",
        "last_scan_date": "2026-11-01",
        "carrier": "DemoExpress",
    }
}

CARRIER_EVENTS = {
    "SHP-123": [
        {
            "timestamp": "2026-11-01T08:40:00",
            "location": "Austin Regional Facility",
            "note": (
                "Package has not moved from the regional facility. "
                "Carrier operations are disrupted due to severe weather "
                "and a backlog is affecting outbound shipments."
            ),
        }
    ]
}

ACTIVE_INCIDENTS = [
    {
        "incident_id": "INC-77",
        "type": "WEATHER",
        "region": "Central Texas",
        "status": "ACTIVE",
        "summary": "Severe weather is delaying outbound carrier operations.",
    }
]

REFUND_POLICY = {
    "policy_id": "REFUND-2026-01",
    "minimum_delay_days": 10,
    "notes": "Refunds are allowed after 10 full days beyond the promised date.",
}

REPLACEMENT_POLICY = {
    "policy_id": "REPLACE-2026-02",
    "minimum_delay_days": 5,
    "notes": "Replacement may be offered after 5 full days with no movement.",
}
