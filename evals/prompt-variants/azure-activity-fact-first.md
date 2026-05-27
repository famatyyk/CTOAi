# Variant: fact-first

Analyze Azure Activity Log entry.
Rules:
- Start with confirmed facts only.
- Separate inference in a distinct section.
- Do not make high-confidence claims when fields are missing.
- Always reference operationName, status, subStatus, resourceId, caller, correlationId if present.

Output sections:
- Confirmed facts
- Inference (low confidence where applicable)
- Impact
- Next investigation step
