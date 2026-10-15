#!/usr/bin/env bash
# Package the API for AWS Lambda (python3.12 on Amazon Linux 2023, glibc 2.34, x86_64) into infra/build/lambda.
# Runtime dependencies come from api/uv.lock as manylinux wheels; boto3 is provided by the Lambda
# runtime. data/ is fetched at build time (scripts/fetch_data.py) and is never committed.
set -euo pipefail
cd "$(dirname "$0")/.."
out=infra/build/lambda
rm -rf "$out" && mkdir -p "$out"
[ -f data/exercises.json ] || python3 scripts/fetch_data.py data
(cd api && uv export --frozen --no-dev --no-hashes --no-emit-project -q -o ../infra/build/requirements.txt)
uv pip install -q --target "$out" -r infra/build/requirements.txt \
  --python-platform x86_64-manylinux_2_34 --python-version 3.12 --only-binary :all:
cp -r api/src/coachkg "$out/"
cp -r kg fixtures data "$out/"
find "$out" -name __pycache__ -prune -exec rm -rf {} +
cat > "$out/run.sh" <<'RUN'
#!/bin/bash
# Started by the Lambda Web Adapter; uvicorn's own access log is off (main.py logs ids/status/timing).
export PYTHONPATH="/var/task:/var/runtime:${PYTHONPATH:-}"
exec /var/lang/bin/python -m uvicorn coachkg.main:app --host 127.0.0.1 --port "${PORT:-8080}" \
  --no-access-log --log-level warning
RUN
chmod 755 "$out/run.sh"
echo "lambda package: $(du -sh "$out" | cut -f1)"
