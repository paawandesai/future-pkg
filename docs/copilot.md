# Coach copilot and churn

## Copilot

The copilot is one orchestrator with read-only tools: a hand-written loop on the Anthropic SDK,
at most 6 turns (`api/src/coachkg/copilot/agent.py`).

- The server fixes the member before the loop starts, from the session and the URL. No tool takes
  a member id, so the model can't reach another member.
- Tools: `get_brief`, `get_adherence`, `get_sleep`, `get_workout_history`, `get_chat`, `get_labs`,
  `get_changes`, `get_churn_signals` and `make_chart`. None of them writes or sends anything.
- `get_chat` returns messages as quoted data marked `member-said` or `coach-said`. Image
  attachments come through as their caption only and are never sent to the model.
- `get_labs` returns values as recorded. The system prompt forbids interpreting labs or DEXA.
- `make_chart` takes metric names from an allow-list and the server fills in the data, so the
  model can't make up a value. Quick-prompt charts
  (`GET /api/members/{id}/charts/{adherence|sleep|messages|compare}`) make no model call.
- Answers carry a disclosure line and are shown as plain text.
- The congratulate draft sends the model only the member's first name, their latest completed
  session and the brief's celebrate task. It returns a draft with a disclosure line. There is no
  send endpoint.

## Churn score

The score is deterministic (`copilot/data.py: churn`) and runs from 0 to 11. 0 to 2 is low, 3 to
6 is elevated, and 7 or more is high.

| Feature | Points |
|---|---|
| Weekly completion: the last 2 weeks against the 2 before | 3 for a drop of 40 points or more; 2 for 20 or more; 1 for 10 or more |
| App logins: the last 14 days against the rate in the 28 days before | 3 at half the prior rate or less; 2 at 75% or less; 1 below 90% |
| Member messages, measured the same way as logins | Same as logins. If there are no earlier messages, it scores 0 and says so |
| Planned sessions missed in the last 14 days | 1 each, up to 2 |

Biomarkers, sleep, labs and DEXA are never inputs.

Login events are generated (`fixtures/generated-login-events.json`, from
`scripts/generate_fixtures.py`). The score lists them as generated data wherever it uses them.

The provided `coach_brief` churn text is shown next to our score, unchanged. For Jordan, both
say "elevated".
