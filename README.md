# DecisionSurfaceLab

A conference demo showing the same delivery-investigation task implemented in two ways:

1. **Tool Sprawl** — the main Gemini agent sees many low-level tools.
2. **Bounded Architecture** — the main Gemini agent sees one business capability.

The demo makes these differences visible in the terminal:

- Gemini/model call count
- model latency
- prompt/context token usage
- tool count visible to the main model
- tool/dependency latency
- dependency failures and retries
- compact structured evidence returned by the bounded architecture

## Scenario

Ask both agents:

> Why is order 123 delayed, and what should we do next?

Expected business facts:

- promised delivery date: 2026-11-01
- demo current date: 2026-11-07
- delay: 6 days
- shipment: STALLED
- active incident: severe weather / backlog
- refund eligible: false
- replacement eligible: true
- recommended action: offer replacement

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit GOOGLE_CLOUD_PROJECT in .env

gcloud auth application-default login
adk web
```

The terminal where `adk web` runs is part of the demo. It prints telemetry.

## Optional failure demo

Set:

```text
DEMO_FAIL_CARRIER_ONCE=true
```

Restart `adk web`.

The first Carrier API attempt will time out, the application will log the failure,
retry once, and continue successfully.

## Clean comparisons

Restart `adk web` before comparing the two agents if you want counters to start fresh.


## Telemetry log files

Every `adk web` run creates two timestamped files under `logs/`:

```text
logs/
├── decision_surface_YYYYMMDD_HHMMSS.log
└── decision_surface_YYYYMMDD_HHMMSS.jsonl
```

The `.log` file contains the same human-readable telemetry shown in the terminal.

The `.jsonl` file contains one JSON object per telemetry event and is useful
for later analysis or charting.

Example:

```json
{"event_type":"gemini_end","agent":"bounded_agent","latency_ms":812.4,"prompt_tokens":530,"total_tokens":551}
```

The `logs/` folder is excluded from Git by default.
