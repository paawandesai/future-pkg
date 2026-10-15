#!/usr/bin/env bash
# Guardrail check on the staged diff, complementing gitleaks.
# Step 1 (the guardrail grep): find added lines mentioning key/secret/token/password/Bearer/sk-.
# Step 2: of those, block lines that also carry a literal value that looks like a credential
# (a long opaque string after = or :, a Bearer token, or an sk- key). Mentions of variable
# names and placeholders pass. Matched text is never printed, only file names.
set -euo pipefail
pattern='api[_-]?key|secret|token|passw|Bearer |sk-'
# A literal must be 20+ opaque characters including a digit (so file paths and words pass).
value='[=:]\s*["'"'"']?(?=[A-Za-z0-9_/+.=-]*[0-9])[A-Za-z0-9_/+.=-]{20,}|Bearer [A-Za-z0-9._-]{12,}|sk-[A-Za-z0-9_-]{16,}'
status=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if git diff --cached -U0 --no-color -- "$f" | grep -E '^\+[^+]' | grep -iE "$pattern" \
     | grep -vE '\$\{?[A-Za-z_]+\}?' | grep -qP "$value"; then
    echo "check-staged-secrets: possible credential in staged changes to $f" >&2
    status=1
  fi
done < <(git diff --cached --name-only --diff-filter=ACM)
exit $status
