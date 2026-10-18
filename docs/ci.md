# CI and local hooks

Goal: catch problems before a push, keep pipelines short, and stay inside a small shared runner
(4 vCPU / 8 GB host, 2 vCPU / 2 GB per job, 2 concurrent jobs for this project).

## Local gates (Husky)

| Hook | Runs | Measured |
|---|---|---|
| pre-commit | gitleaks on staged changes, credential-literal check, lint-staged (prettier + eslint for `web/`, ruff format + check for `api/`) on staged files only | 3.5–3.9 s |
| pre-push | web typecheck, vitest on files changed since `origin/main`, mypy, pytest (`-n 2`) | 6.9 s |

Husky was chosen because the repo has a root `package.json` (polyglot repo with Node present).
`pnpm install` installs the hooks; CI sets `HUSKY=0`. gitleaks must be on the developer's PATH.
A deliberate lint error blocks the commit (checked: eslint `no-unused-vars` stopped it).

## Pipeline

- One pipeline per push: merge request pipelines win over branch pipelines; new commits cancel
  running interruptible pipelines (verified: a second push cancelled the first).
- Jobs skip when their area did not change (`rules: changes` with `compare_to: refs/heads/main`).
- Jobs start as soon as their inputs are ready (`needs: []`; `web:build` waits only on `web:typecheck`).
- 15 minute default timeout, `GIT_DEPTH=20` (except `gitleaks`, which fetches the whole history),
  workers capped at 2, Node heap capped at 1536 MB.
- `kg:live` checks every SNOMED, Uberon and Wikidata identifier against its source on every
  pipeline, and the deploy jobs wait for it. If NCI EVS, EBI OLS or Wikidata is down, the
  pipeline fails until it is back (one automatic retry).
- Each job prints `peak_memory_mb` from its cgroup as its last script line.

### Dependencies: cache plus re-sync instead of an install job

Measured locally: `api/.venv` is 167 MB and a warm `uv sync --frozen` takes 0.1 s (cold 7.6 s);
`node_modules` is 239 MB and a warm `pnpm install --frozen-lockfile --offline` takes 1.9 s (cold 3.7 s).
Passing 400 MB of installed dependencies as artifacts would cost more than re-syncing from a
lockfile-keyed cache, so each job re-syncs. The cache is written by `py:test` and `web:test` and
only read elsewhere.

### No prebuilt CI image (yet)

Tool setup per job is under 3 s (`corepack enable` + pnpm download; the uv image already has
uv and Python), so a `Dockerfile.ci` would not pay for itself. Revisit when the deploy jobs need
AWS CLI + CDK + Docker together. Privileged docker-in-docker on the runner is unverified.

## Measurements (MR pipeline, 2026-10-15)

| Job | Duration | Peak RAM |
|---|---|---|
| gitleaks | 5 s | 38 MB |
| py:lint | 10 s | 229 MB |
| py:typecheck | 17 s | 477 MB |
| py:test | 17 s | 332 MB |
| py:licenses | 11 s | 230 MB |
| web:lint | 23 s | 611 MB |
| web:typecheck | 17 s | 625 MB |
| web:test | 20 s | 621 MB |
| web:build | 18 s | 627 MB |
| web:licenses | 15 s | 633 MB |

Pipeline wall time 70–116 s with 2 job slots; about 153 job-seconds per push touching both
areas. Queue time (140–400 s) came from the runner being busy, not from this pipeline.

## Recommended project settings (not changed)

- Container registry cleanup policy: keep the last 5 tags, remove tags older than 14 days.
- A weekly schedule for `eval:live`, which already has a schedule rule.
- OIDC for the deploy jobs instead of the static keys of the `future-pkg-deployer` IAM user: an
  IAM role that trusts the GitLab instance's OIDC provider, scoped to protected `main`. It needs
  the AWS account owner to create the provider and role, so it is an owner step.
