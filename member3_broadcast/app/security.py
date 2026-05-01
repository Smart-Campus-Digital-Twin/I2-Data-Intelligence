from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt


class TokenError(Exception):
    pass


def create_test_token(subject: str, secret: str, algorithm: str = "HS256", expires_in_minutes: int = 60) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def validate_socket_token(token: str | None, secret: str, algorithm: str) -> dict[str, object]:
    if not token:
        raise TokenError("Missing token")

    try:
        decoded = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    subject = decoded.get("sub")
    if not subject:
        raise TokenError("Token subject missing")
    return decoded
