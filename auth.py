"""
RECON-X  ·  Authentication helpers
Admin: username=admin  password=admin123  (hard-coded)
Regular users: email + username + password stored in DB or in-memory fallback.
"""
import hashlib
from functools import wraps
from flask import session, redirect, url_for

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_ROLE     = "admin"
USER_ROLE      = "user"

# In-memory fallback: { username: {password_hash, email, role} }
_MEM_USERS: dict[str, dict] = {}


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Session helpers ────────────────────────────────────────────────────────────

def login_user(username: str, role: str):
    session["username"] = username
    session["role"]     = role
    session.permanent   = True


def logout_user():
    session.clear()


def current_user() -> dict | None:
    u = session.get("username")
    r = session.get("role")
    if u:
        return {"username": u, "role": r}
    return None


def is_admin() -> bool:
    u = current_user()
    return u is not None and u["role"] == ADMIN_ROLE


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


# ── Auth logic ─────────────────────────────────────────────────────────────────

def attempt_login(username: str, password: str, db_available: bool, db_get_user=None):
    """Returns (ok, role, error)"""
    username = username.strip().lower()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return True, ADMIN_ROLE, None

    hashed = _hash(password)

    if db_available and db_get_user:
        user = db_get_user(username)
        if user and user["password_hash"] == hashed:
            return True, USER_ROLE, None
        return False, None, "Invalid username or password."

    mem = _MEM_USERS.get(username)
    if mem and mem["password_hash"] == hashed:
        return True, USER_ROLE, None

    return False, None, "Invalid username or password."


def attempt_register(username: str, password: str, email: str = "",
                     db_available: bool = False,
                     db_create_user=None, db_user_exists=None):
    """Returns (ok, error). Email is stored but not verified."""
    username = username.strip().lower()
    email    = email.strip().lower()

    if not username or not password:
        return False, "Username and password are required."
    if not email or "@" not in email:
        return False, "A valid email address is required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    if username == ADMIN_USERNAME:
        return False, "That username is reserved."

    hashed = _hash(password)

    if db_available and db_create_user and db_user_exists:
        if db_user_exists(username):
            return False, "Username already taken."
        db_create_user(username, hashed, email)
        return True, None

    # Memory fallback
    if username in _MEM_USERS:
        return False, "Username already taken."
    _MEM_USERS[username] = {"password_hash": hashed, "email": email, "role": USER_ROLE}
    return True, None
