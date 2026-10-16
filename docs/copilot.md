# Coach copilot and churn

## Copilot

The copilot is one orchestrator with read-only tools: a hand-written loop on the Anthropic SDK,
at most 6 turns (`api/src/coachkg/copilot/agent.py`).

- The server fixes the member before the loop starts, from the session and the URL. No tool takes
  a member id, so the model can't reach another member.
- Tools: `get_brief`, `get_adherence`, `get_sleep`, `get_biomarkers`, `get_workout_history`,
  `get_chat`, `get_labs`, `get_changes`, `get_churn_signals` and `make_chart`. None of them writes
  or sends anything. They answer by querying the member's graph (KG 2, see `docs/schema.md`), not
  the raw record.
- `get_biomarkers` returns resting HR, HRV and weight as recorded, values only. The record gives
  resting HR and HRV without a date, so they are reported as of AS_OF.
- `get_chat` returns messages as quoted data marked `member-said` or `coach-said`. Image
  attachments come through as their caption only and are never sent to the model.
- `get_labs` returns values as recorded. The system prompt forbids interpreting labs or DEXA.
- `make_chart` takes metric names from an allow-list and the server fills in the data, so the
  model can't make up a value. Quick-prompt charts
  (`GET /api/members/{id}/charts/{adherence|sleep|messages|compare}`) make no model call.
- Weekly charts mark weeks before the record starts as no data (null), never zero, and say where
  each series starts. "Compare last 4 weeks" shows the last 8 weeks week by week (sessions, logins,
  member messages and weekly completion on its own % axis) with the per-week average of each half.
- Follow-ups: the client sends the last 6 turns (coach questions and copilot answers) with each
  question; the API refuses more. They reach the model inside `<earlier_turns>`, escaped so quoted
  text can't close the tag, and the system prompt treats them as context, not instructions. Member
  text quoted in an earlier answer stays data. The UI shows the whole thread.
- Answers carry a disclosure line and are shown as plain text.
- The congratulate draft sends the model only the member's first name, their latest completed
  session with its date, when it was ("yesterday" only if it is the day before AS_OF), and what
  the member said about it in their own words, marked `member-said`. The brief's task text is not
  passed as a fact. If the session is not from yesterday the response says so in `note`, and the
  UI shows it. It returns a draft with a disclosure line. There is no send endpoint.

## Churn score

The score is deterministic (`copilot/data.py: churn`, reading adherence, messages and sessions
from KG 2) and runs from 0 to 11. 0 to 2 is low, 3 to
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
