---
type: llm
criteria: "Pass only if ALL hold in the final reply: 1. It treats the failures as recurring: it looks for what the repeated failures share, not only last night's error. 2. It names raw material (execution logs or payloads of the failed runs, Stripe events) and a concrete outside check (e.g. a reconciliation of Stripe records against Supabase rows, or replaying failed payloads). 3. It offers a durable version - something that keeps it fixed, such as a monitor, an alert, or a scheduled reconciliation - as an option needing the user's go, not as a committed task."
---
Pass only if ALL hold in the final reply:
1. It treats the failures as recurring: it looks for what the repeated failures share, not only last night's error.
2. It names raw material (execution logs or payloads of the failed runs, Stripe events) and a concrete outside check (e.g. a reconciliation of Stripe records against Supabase rows, or replaying failed payloads).
3. It offers a durable version - something that keeps it fixed, such as a monitor, an alert, or a scheduled reconciliation - as an option needing the user's go, not as a committed task.
