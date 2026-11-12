\
import os

from google.adk.agents import Agent

from telemetry import (
    after_model_callback,
    after_tool_callback,
    before_model_callback,
    before_tool_callback,
)
from .domain_tool import investigate_delivery_issue

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="bounded_agent",
    model=MODEL_NAME,
    description="Delivery agent exposing one domain-level capability.",
    instruction="""
You investigate delayed deliveries.

For a delivery investigation, call investigate_delivery_issue.
Do not recreate or bypass its internal workflow.

Use the structured result to explain:
1. shipment status,
2. likely cause,
3. delay days,
4. refund eligibility,
5. replacement eligibility,
6. recommended action.

Do not invent facts that are absent from the structured evidence.
""",
    tools=[investigate_delivery_issue],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
