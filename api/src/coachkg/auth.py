"""Who is calling.

mock: local runs only; refused when running on AWS Lambda, so a deployed stack can't fall back to it.
cognito: a Cognito ID token (Authorization: Bearer) verified against the pool's keys; the coach id
comes from the admin-set `custom:coach_id` claim, which the app client cannot write.
Anything else, or any failure, is a 401.
"""

from __future__ import annotations

import os
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


def cognito_coach(authorization: str | None) -> str:
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
    return coach


def current_coach(authorization: Annotated[str | None, Header()] = None) -> str:
    mode = load_settings().auth_mode
    if mode == "mock":
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            raise _unauthorized()
        return os.environ.get("DEMO_COACH_ID", DEMO_COACH)
    if mode == "cognito":
        return cognito_coach(authorization)
    raise _unauthorized()
