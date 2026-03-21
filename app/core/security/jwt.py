"""
JWT token creation and validation utilities.

This module is framework-agnostic and handles only JWT operations.
It does NOT depend on FastAPI or any web framework.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from redis.asyncio import Redis

from app.core.config import settings
from app.core.enums import TokenType
from app.core.redis import get_redis_client

# JWT Configuration
JWT_SECRET_KEY = settings.effective_jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""

    pass


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or has an invalid signature."""

    pass


# TODO: Make it a JWT Service
def create_access_token(
    payload: dict[str, Any], token_type: TokenType = TokenType.ACCESS
) -> str:
    """
    Create a JWT access token with the given payload.

    Automatically adds:
    - iat (issued at): Current UTC timestamp
    - exp (expiration): 15 minutes from now

    Args:
        payload: Dictionary containing the token payload data.
                 Common fields: {"sub": user_id, "email": user_email}

    Returns:
        str: Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "user123", "email": "user@example.com"})
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    # Create a copy to avoid mutating the original payload
    to_encode = payload.copy()

    # Add issued at timestamp
    now = datetime.now(timezone.utc)
    to_encode["iat"] = now
    to_encode["jti"] = str(uuid.uuid4())

    # Add expiration timestamp (15 minutes from now)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire

    to_encode["type"] = token_type.value
    # Encode and return the JWT token
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(payload: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with the given payload.

    Refresh tokens are long-lived tokens used to obtain new access tokens
    without re-authentication. They contain minimal user information and
    do NOT include permissions.

    Automatically adds:
    - iat (issued at): Current UTC timestamp
    - exp (expiration): 7 days from now
    - type: "refresh"

    Args:
        payload: Dictionary containing the token payload data.
                 Should include: {"sub": user_id, "email": user_email}

    Returns:
        str: Encoded JWT refresh token string

    Example:
        >>> token = create_refresh_token({"sub": "user123", "email": "user@example.com": "web"})
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    # Create a copy to avoid mutating the original payload
    to_encode = payload.copy()

    # Add issued at timestamp
    now = datetime.now(timezone.utc)
    to_encode["iat"] = now
    to_encode["jti"] = str(uuid.uuid4())

    # Add expiration timestamp (7 days from now)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode["exp"] = expire

    # Set token type to refresh
    to_encode["type"] = TokenType.REFRESH.value

    # Encode and return the JWT token
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Validates:
    - Token signature
    - Token expiration

    Args:
        token: The JWT token string to decode

    Returns:
        dict: The decoded token payload

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token signature is invalid or token is malformed

    Example:
        >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        >>> payload = decode_access_token(token)
        >>> print(payload["sub"])
        'user123'
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload

    except jwt.ExpiredSignatureError:
        # Token has expired
        raise TokenExpiredError("Token has expired")

    except jwt.InvalidTokenError:
        # Invalid signature or malformed token
        raise InvalidTokenError("Invalid token or signature")


async def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    redis: Redis = await get_redis_client()
    if ttl_seconds <= 0:
        return
    redis_key = f"blacklist:{jti}"
    await redis.setex(redis_key, ttl_seconds, "1")


async def is_jti_blacklisted(jti: str) -> bool:
    redis: Redis = await get_redis_client()
    redis_key = f"blacklist:{jti}"
    return await redis.exists(redis_key)


def issue_token(user_id: str, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "provider": "google",
    }
    return create_access_token(payload)
