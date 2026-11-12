\
import os

from google.adk.agents import Agent

from telemetry import (
    after_model_callback,
    after_tool_callback,
    before_model_callback,
    before_tool_callback,
)
from .tools import (
    calculate_delay_days,
    check_refund_eligibility,
    check_replacement_eligibility,
    get_active_incidents,
    get_carrier_events,
    get_order,
    get_refund_policy,
    get_replacement_policy,
    get_shipment,
)

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="tool_sprawl_agent",
    model=MODEL_NAME,
    description="Delivery agent with many low-level tools exposed to Gemini.",
    instruction="""
You investigate delayed deliveries.

When asked about an order, use the available tools to determine:
1. shipment status,
2. likely delay cause,
3. delay days,
4. refund eligibility,
5. replacement eligibility,
6. recommended next action.

You are responsible for deciding which tools to call, their order, their
arguments, how to combine the results, and when you have enough evidence.

Do not invent business data. Base conclusions only on tool results.
""",
    tools=[
        get_order,
        get_shipment,
        get_carrier_events,
        get_active_incidents,
        get_refund_policy,
        get_replacement_policy,
        calculate_delay_days,
        check_refund_eligibility,
        check_replacement_eligibility,
    ],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
