"""User authentication module.

This is a *deep module* — it fully owns user creation, credential
verification, and session management.  Callers never need to know
about password hashing algorithms, database column layout, or Flask
session keys.
"""

from dataclasses import dataclass
from typing import Optional

import bcrypt
from flask import session

from db import execute_query


# ---------------------------------------------------------------------------
# Public data type — the only representation of a user that leaves this module
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class User:
    """An authenticated user.  Immutable and free of database internals."""
    id: int
    email: str


# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def _check_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def _row_to_user(row) -> Optional[User]:
    """Convert a database row to a User, or None if the row is None."""
    if row is None:
        return None
    return User(id=row["id"], email=row["email"])


def create_user(email: str, password: str) -> User:
    """Register a new user and return a ``User`` instance.

    The caller does **not** need to hash the password — this module handles it.
    """
    password_hash = _hash_password(password)
    execute_query(
        "INSERT INTO USERS (email, password_hash) VALUES (?, ?)",
        (email, password_hash),
        commit=True,
    )
    row = execute_query("SELECT * FROM USERS WHERE email = ?", (email,), fetchone=True)
    return _row_to_user(row)


def get_user_by_email(email: str) -> Optional[User]:
    """Look up a user by email.  Returns ``None`` if not found."""
    row = execute_query("SELECT * FROM USERS WHERE email = ?", (email,), fetchone=True)
    return _row_to_user(row)


def authenticate(email: str, password: str) -> Optional[User]:
    """Verify credentials and return a ``User``, or ``None`` on failure.

    This replaces the old ``login_user`` helper and the duplicated logic
    that lived in the ``/login`` route.
    """
    row = execute_query("SELECT * FROM USERS WHERE email = ?", (email,), fetchone=True)
    if row is None or not _check_password(password, row["password_hash"]):
        return None
    return _row_to_user(row)


# ---------------------------------------------------------------------------
# Session management — this module is the single owner of session["email"]
# ---------------------------------------------------------------------------

def login_session(user: User) -> None:
    """Mark the user as logged-in for the current session."""
    session["email"] = user.email


def logout_session() -> None:
    """End the current session."""
    session.pop("email", None)


def get_current_user() -> Optional[User]:
    """Return the currently logged-in ``User``, or ``None``."""
    email = session.get("email")
    if not email:
        return None
    return get_user_by_email(email)







