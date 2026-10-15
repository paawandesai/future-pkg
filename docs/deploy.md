# AWS deployment (demo)

One CDK stack, `FuturePkgDemo`, in us-east-1 (`infra/`). Deployed only from the protected `main`
branch by the manual GitLab job `deploy:production`; `deploy:secret` then puts the API key.

| Piece | What | Guardrail it carries |
|---|---|---|
| Cognito user pool `future-pkg-coaches` | Invite-only (no self sign-up), email sign-in, 12+ char passwords | Real auth; `custom:coach_id` is admin-set and not writable by the app client, so a coach can't re-scope their token |
| Lambda `Api` + function URL | The FastAPI app unchanged, via the AWS Lambda Web Adapter layer, streaming responses (SSE) | `AUTH_MODE=cognito` (mock is refused on Lambda); access log is method, route template, status, ms |
| CloudFront + private S3 bucket | SPA from S3 (origin access control), `/api/*` to the function URL, no caching for the API | `X-Robots-Tag: noindex` and security headers on every response, `robots.txt` disallows all; demo banner is in the UI |
| DynamoDB `Plans` | Draft and confirmed plans | `expires_at` TTL one day after drafting |
| DynamoDB `AccessRequests` | "Request a demo account" submissions and hourly rate counters | TTL 7 days (requests) and 2 hours (counters); client addresses are stored only as salted hashes; at most 3 requests per client per hour and 50 pending in total |
| Cognito group `admin` | Who may approve requests and invite or turn off reviewers | Granted only by AWS (the stack adds `DEMO_ADMIN_EMAIL`); the API role can create, enable and disable users but can't grant admin |
| Lambda `Purge` + EventBridge rule | Daily | Deletes every plan drafted more than 12 hours ago |
| Secrets Manager `future-pkg/anthropic-api-key` | Created with a random value; `deploy:secret` puts the real key | The key is never in the template, outputs, function config or logs; the function gets the secret's name |
| CloudWatch log groups | Two weeks' retention | No bodies, prompts, member text or query strings are logged |

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
uv run --no-project --with boto3==1.43.105 python scripts/put_secret.py
uv run --no-project --with boto3==1.43.105 python scripts/demo_users.py invite someone@example.com
uv run --no-project --with boto3==1.43.105 python scripts/demo_users.py disable-all   # after grading
# or, signed in as an admin: Admin → "Turn off all reviewer accounts"
```

Tear down: `scripts/cdk.sh destroy FuturePkgDemo` removes everything, including the data.
