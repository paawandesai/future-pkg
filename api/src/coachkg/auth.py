"""Who is calling.

mock: local runs only; refused when running on AWS Lambda, so a deployed stack can't fall back to it.
cognito: a Cognito ID token (Authorization: Bearer) verified against the pool's keys; the coach id
comes from the admin-set `custom:coach_id` claim, which the app client cannot write. Admin routes
also need membership of the pool's `admin` group (`cognito:groups`), which only AWS can grant.
Anything else, or any failure, is a 401 (403 for a signed-in non-admin on an admin route).
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Header, HTTPException

from coachkg.config import load_settings

DEMO_COACH = "coach_01HXSAM"


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Sign in required", headers={"WWW-Authenticate": "Bearer"})


@lru_cache(maxsize=1)
def _jwks(issuer: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600, timeout=5)


def signing_key(token: str, issuer: str) -> Any:
    return _jwks(issuer).get_signing_key_from_jwt(token).key


def cognito_claims(authorization: str | None) -> dict[str, Any]:
    pool_id = os.environ.get("COGNITO_USER_POOL_ID", "")
    client_id = os.environ.get("COGNITO_CLIENT_ID", "")
    if not pool_id or not client_id:
        raise _unauthorized()
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized()
    region = pool_id.split("_", 1)[0]
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    try:
        claims = jwt.decode(
            token,
            signing_key(token, issuer),
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
            options={"require": ["exp", "iat", "iss", "aud", "token_use"]},
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError):
        raise _unauthorized() from None
    coach = claims.get("custom:coach_id")
    if claims.get("token_use") != "id" or not isinstance(coach, str) or not coach:
        raise _unauthorized()
    if not user_enabled(pool_id, str(claims.get("cognito:username") or "")):
        raise _unauthorized()
    return dict(claims)


# A disabled account stops working within ENABLED_TTL_S, not when its one-hour token expires.
ENABLED_TTL_S = 60.0
_enabled: dict[str, tuple[float, bool]] = {}
_enabled_lock = threading.Lock()


def _cognito_enabled(pool_id: str, username: str) -> bool:
    import boto3  # type: ignore[import-not-found]  # provided by the Lambda runtime

    region = pool_id.split("_", 1)[0]
    user = boto3.client("cognito-idp", region_name=region).admin_get_user(
        UserPoolId=pool_id, Username=username
    )
    return bool(user.get("Enabled"))


def user_enabled(pool_id: str, username: str, lookup: Any = None) -> bool:
    """Is the account still enabled? Checked against Cognito on Lambda (cached per user), and
    fails closed: an unknown user or a failed lookup is a 401. Local runs have no pool to ask."""
    if lookup is None:
        if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return True
        lookup = _cognito_enabled
    if not username:
        return False
    now = time.monotonic()
    with _enabled_lock:
        hit = _enabled.get(username)
        if hit and now - hit[0] < ENABLED_TTL_S:
            return hit[1]
    try:
        ok = bool(lookup(pool_id, username))
    except Exception:
        return False
    with _enabled_lock:
        _enabled[username] = (now, ok)
    return ok


def _mock_allowed() -> bool:
    return not os.environ.get("AWS_LAMBDA_FUNCTION_NAME")


def current_coach(authorization: Annotated[str | None, Header()] = None) -> str:
    mode = load_settings().auth_mode
    if mode == "mock" and _mock_allowed():
        return os.environ.get("DEMO_COACH_ID", DEMO_COACH)
    if mode == "cognito":
        return str(cognito_claims(authorization)["custom:coach_id"])
    raise _unauthorized()


def current_caller(authorization: Annotated[str | None, Header()] = None) -> str:
    """Who is spending model calls: the signed-in user (the token's `sub`), not the coach id, which
    every demo reviewer shares. Used only as a rate-limit key, hashed before it is stored."""
    mode = load_settings().auth_mode
    if mode == "mock" and _mock_allowed():
        return "local"
    if mode == "cognito":
        return str(cognito_claims(authorization).get("sub") or "")
    raise _unauthorized()


@dataclass(frozen=True)
class Admin:
    email: str


def current_admin(authorization: Annotated[str | None, Header()] = None) -> Admin:
    """Admin routes. Locally (mock) the demo coach is the admin; deployed, the `admin` group decides."""
    mode = load_settings().auth_mode
    if mode == "mock" and _mock_allowed():
        return Admin(email="local-admin@example.com")
    if mode != "cognito":
        raise _unauthorized()
    claims = cognito_claims(authorization)
    groups = claims.get("cognito:groups") or []
    if "admin" not in groups:
        raise HTTPException(status_code=403, detail="Admins only")
    return Admin(email=str(claims.get("email", "")))
