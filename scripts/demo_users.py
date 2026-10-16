"""Manage the invite-only demo coach accounts in the deployed Cognito pool.

  uv run --no-project --with boto3==1.43.105 python scripts/demo_users.py invite EMAIL [COACH_ID]
  ... list | disable EMAIL | disable-all | delete EMAIL

`invite` emails a temporary password straight from Cognito (it is never printed here). COACH_ID
defaults to the demo coach that owns the fictional member Jordan. `disable-all` is the
"demo accounts disabled after grading" step. Prints emails and statuses only.
"""

import os
import sys

import boto3

POOL_NAME = "future-pkg-coaches"
DEFAULT_COACH = "coach_01HXSAM"

idp = boto3.client(
    "cognito-idp", region_name=os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
)


def pool_id() -> str:
    pools = [p for p in idp.list_user_pools(MaxResults=60)["UserPools"] if p["Name"] == POOL_NAME]
    if len(pools) != 1:
        sys.exit(f"expected one pool named {POOL_NAME}, found {len(pools)}")
    return str(pools[0]["Id"])


def users(pid: str) -> list[dict]:
    out, kw = [], {}
    while True:
        page = idp.list_users(UserPoolId=pid, **kw)
        out += page["Users"]
        if "PaginationToken" not in page:
            return out
        kw = {"PaginationToken": page["PaginationToken"]}


def main(argv: list[str]) -> None:
    if not argv:
        sys.exit(__doc__)
    cmd, args, pid = argv[0], argv[1:], pool_id()
    if cmd == "invite":
        email, coach = args[0], (args[1] if len(args) > 1 else DEFAULT_COACH)
        idp.admin_create_user(
            UserPoolId=pid,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "custom:coach_id", "Value": coach},
            ],
            DesiredDeliveryMediums=["EMAIL"],
        )
        print(f"invited {email} as {coach}; Cognito emailed the temporary password")
    elif cmd == "list":
        for u in users(pid):
            email = next((a["Value"] for a in u["Attributes"] if a["Name"] == "email"), "?")
            print(f"{email}\t{u['UserStatus']}\t{'enabled' if u['Enabled'] else 'disabled'}")
    elif cmd == "disable":
        idp.admin_disable_user(UserPoolId=pid, Username=args[0])
        print(f"disabled {args[0]}")
    elif cmd == "disable-all":
        for u in users(pid):
            idp.admin_disable_user(UserPoolId=pid, Username=u["Username"])
        print("disabled every demo account")
    elif cmd == "delete":
        idp.admin_delete_user(UserPoolId=pid, Username=args[0])
        print(f"deleted {args[0]}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
