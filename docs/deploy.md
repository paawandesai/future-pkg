# AWS deployment (demo)

One CDK stack, `FuturePkgDemo`, in us-east-1 (`infra/`). Deployed only from the protected `main`
branch by the manual GitLab job `deploy:production`; `deploy:secret` then puts the API key.

| Piece | What | Guardrail it carries |
|---|---|---|
| Cognito user pool `future-pkg-coaches` | Invite-only (no self sign-up), email sign-in, 12+ char passwords | Real auth; `custom:coach_id` is admin-set and not writable by the app client, so a coach can't re-scope their token |
| Lambda `Api` + function URL | The FastAPI app unchanged, via the AWS Lambda Web Adapter layer, streaming responses (SSE) | `AUTH_MODE=cognito` (mock is refused on Lambda); access log is method, route template, status, ms; rejects any request without CloudFront's `x-origin-verify` header (value generated in Secrets Manager), so the function URL can't be used directly; reserved concurrency 5 (`-c apiConcurrency=N`); a disabled account's token is refused within a minute (`AdminGetUser`, cached 60 s, fails closed); model-backed requests (drafts, copilot answers, congratulation drafts) are capped at 40 per signed-in user per hour and 600 a day for the whole demo (HTTP 429 after that) |
| CloudFront Function `ApiGate` (viewer request, `/api/*`) | Runs at the edge before Lambda | A request without a bearer token gets 401 from the edge, except `POST /api/access-requests`, so anonymous floods never invoke the function; writes the viewer's address into `X-Viewer-Ip`, overwriting any client copy, for the access form's rate limit |
| CloudFront + private S3 bucket | SPA from S3 (origin access control), `/api/*` to the function URL, no caching for the API | `X-Robots-Tag: noindex` and security headers on every response (CSP without inline styles, Permissions-Policy, Server header removed), `robots.txt` disallows all; demo banner is in the UI |
| DynamoDB `Plans` | Draft and confirmed plans | `expires_at` TTL one day after drafting |
| DynamoDB `AccessRequests` | "Request a demo account" submissions and hourly rate counters | TTL 7 days (requests) and 2 hours (counters); client addresses are stored only as salted hashes; at most 3 requests per viewer address (IPv6 per /64) per hour and 50 pending in total; an admin can reject all pending at once |
| Cognito group `admin` | Who may approve requests and invite or turn off reviewers | Granted only by the owner with the AWS CLI (below), never by the stack or the app; the API role can create, enable, disable and read users but can't grant admin |
| Lambda `Purge` + EventBridge rule | Daily | Deletes every plan drafted more than 12 hours ago, and every expired access request and rate counter |
| Secrets Manager `future-pkg/anthropic-api-key` | Created with a random value; `deploy:secret` puts the real key | The key is never in the template, outputs, function config or logs; the function gets the secret's name |
| CloudWatch log groups | Two weeks' retention for the stack's groups, including CDK's provider functions | No bodies, prompts, member text or query strings are logged. One orphaned group from an earlier version (`/aws/lambda/FuturePkgDemo-AWS679f53fac…`, the old admin-grant provider) has no expiry and holds the admin's email from 2026-10-15; the owner deletes it by hand (below) |
| AWS Budget (optional) | Monthly cost budget, email at 50% and 100% actual and 100% forecast | Created only when `-c budgetEmail=…` or `BUDGET_ALERT_EMAIL` is set; `-c monthlyBudgetUsd=N` (default 20) |

Why Lambda instead of App Runner or Fargate: App Runner no longer accepts new customers, and
Fargate needs a load balancer (about $16/month) plus the task (about $18/month), over the $25
budget. Lambda with the web adapter runs the same app with streaming for roughly $1/month at demo
traffic. Cold start is about 2 s (imports 1.7 s; building the graphs 0.05 s).

## Commands

```
scripts/package_lambda.sh            # infra/build/lambda (wheels for python3.12 on AL2023)
pnpm --filter web build              # web/dist
scripts/cdk.sh diff                  # every 12-digit number (account id) is masked in output
scripts/cdk.sh deploy FuturePkgDemo --require-approval never
uv run --project api --frozen --only-group deploy python scripts/put_secret.py
uv run --project api --frozen --only-group deploy python scripts/demo_users.py invite someone@example.com
uv run --project api --frozen --only-group deploy python scripts/demo_users.py disable-all   # after grading
# or, signed in as an admin: Admin → "Turn off all reviewer accounts"
```

First admin (owner, once per pool; the stack no longer does this, because the CDK custom resource
that did logged the email):

```
aws cognito-idp admin-add-user-to-group --user-pool-id <UserPoolId output> --group-name admin --username <email>
```

Old admin-grant log group (owner, once; the deployer user can't delete log groups):

```
aws logs delete-log-group --log-group-name /aws/lambda/FuturePkgDemo-AWS679f53fac002430cb0da5b7982bd22872-<suffix>
```

Static analysis (checkov, 2026-10-18): the failed checks we accept for the demo are no WAF (the
edge function stops anonymous calls instead), no CloudFront access logs (they would hold viewer
IP addresses), no DynamoDB point-in-time recovery (it would keep plans past the daily purge), the
default CloudFront certificate, and AWS-owned encryption keys. The only IAM wildcards are in
CDK's own providers (`cloudfront:CreateInvalidation`, `logs:PutRetentionPolicy`).

The Admin button turns off reviewer accounts and leaves admin accounts on. `disable-all` turns off
every account in the pool, admins included, so run it last.

Invites come from Cognito's default sender, which can land in spam, and the temporary password
expires after 7 days. There is no resend: `delete EMAIL`, then `invite EMAIL` again.

Tear down: `scripts/cdk.sh destroy FuturePkgDemo` removes everything, including the data.
