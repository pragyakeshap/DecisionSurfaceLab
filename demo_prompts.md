# Demo prompts

Primary prompt:

> Why is order 123 delayed, and what should we do next?

Follow-up:

> What evidence did you use?

What to point out in the terminal:

## Tool-sprawl agent

- Main model sees 9 low-level tool schemas.
- Gemini may make multiple model turns as it orchestrates the workflow.
- Prompt/context token counts can grow as tool results are added to conversation context.
- Every sequential backend call adds latency.
- A retry adds additional waiting.

## Bounded agent

- Main model sees 1 domain capability.
- Backend sequencing is application-owned.
- Calculations and policy checks run in deterministic Python.
- One narrow Gemini call interprets the unstructured carrier note.
- Only compact structured evidence returns to the main model.
