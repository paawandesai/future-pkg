.PHONY: data install up dev test

# Fetch the assessment inputs at a pinned commit (never committed).
data:
	python3 scripts/fetch_data.py data

# One command, Docker: http://localhost:5173
up: data
	docker compose up --build

# Dependencies from the lockfiles (no Docker path).
install:
	pnpm install --frozen-lockfile
	cd api && uv sync --frozen

# One command, no Docker (needs uv and pnpm): API on :8000, web on :5173.
dev: data install
	(cd api && set -a && { [ -f ../.env ] && . ../.env || true; } && set +a && \
	  uv run uvicorn coachkg.main:app --port 8000 --no-access-log) & \
	pnpm --filter web exec vite; kill %1 2>/dev/null || true

# All offline suites; works on a fresh clone.
test: data install
	cd api && uv run --frozen pytest -n 2
	pnpm --filter web exec vitest run
	pnpm --filter infra test
