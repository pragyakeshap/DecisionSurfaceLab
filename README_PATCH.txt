Add telemetry.py to the repo root.
Replace both agent.py files with the versions in this patch.

For latency/failure demonstration, add these env vars:
DEMO_DEPENDENCY_LATENCY_MS=250
DEMO_FAIL_CARRIER_ONCE=false

The existing tools.py and domain_tool.py also need the dependency wrappers described in the chat response.
