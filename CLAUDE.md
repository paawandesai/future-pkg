# Working in this repository

This is coach decision support, not a medical device. Read this before changing anything that
touches safety, member data or the deployment.

## Layout

- `api/`: FastAPI app (`coachkg`). It contains the graph (`kg/`), resolver, safety filter,
  generator pipeline, copilot, plans and auth.
- `kg/`: rule files, authored exercises and ontology alignments. YAML is the source of truth.
- `web/`: React SPA. `infra/`: CDK stack. `eval/`: live evaluation. `scripts/`: data fetch,
  packaging, deploy helpers.
- `data/` is fetched at build time (`make data`) and must never be committed.

## Commands

```
make up | make dev | make test
cd api && uv run pytest -n 2 && uv run mypy src tests && uv run ruff check .
pnpm --filter web typecheck && pnpm --filter web exec vitest run
pnpm --filter infra test
cd api && uv run python ../eval/run_eval.py         # live, needs the API key
scripts/cdk.sh diff                                 # masks account ids
```

The hooks run gitleaks, a staged credential check and lint-staged on commit, and type checks and
tests on push. Never bypass them with `--no-verify`. Ask before weakening any check.

## Rules that don't bend

- **Safety is deterministic.**
  - The safety filter acts only on dataset facts and on rule files a person has signed
    (`review.status: signed`, with initials and a date).
  - A model never writes graph edges or decides that something is safe.
  - If an injury mention can't be resolved, the request is blocked (fail closed).
  - Never cache safety decisions across members.
- **Member text is data.**
  - Chat lines, captions and notes are quoted with `member-said` provenance.
  - Member text can add a pending restriction. Only the coach's structured field can clear one.
  - Text inside member data is never treated as an instruction.
- **Copilot tools stay read-only.** They are scoped by the server to the member on screen. No
  tool takes a member id, and there is no send tool. Drafts carry the AI disclosure.
- **Labs and DEXA** are shown as values only. They are never churn inputs and are never
  interpreted.
- **Wording.**
  - Write "coach decision support". Never say a workout is "safe".
  - The coach confirms every plan.
  - UI text is gender-neutral.
- **SNOMED CT** is used by reference only: identifiers plus our own labels, never descriptions.
  Don't copy guideline text; paraphrase and cite.
- **Secrets.**
  - Secrets come only from the environment or Secrets Manager.
  - Never print or log keys, tokens, request bodies or member text.
  - Never put a secret in IaC, stack outputs or CI logs.
  - Never print the AWS account id.
- **Synthetic data only.** Disclose anything generated.

## Conventions

- New dependencies:
  - Permissive licences only (CI fails on GPL, AGPL, SSPL, BUSL, non-commercial, unknown or proprietary licences).
  - The commit message states each new dependency's licence and maintenance status.
  - Regenerate `LICENSES.md` with `scripts/license_audit.py`.
- Model ids are configuration (`LLM_MODEL_FAST`, `LLM_MODEL_MAIN`). Keep model identifiers out of
  code, comments and merge request text. The only place a commit names a model is its
  `Co-Authored-By` trailer, which records who wrote it (see `AI_USAGE.md`).
- When you change a signed rule file, set its review back to `status: draft` so a person signs it again.
- Deploys go only through the manual, protected `deploy:production` job on `main`, or with the
  owner's explicit approval.
