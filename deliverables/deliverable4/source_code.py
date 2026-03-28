"""
=============================================================================
Deliverable 4 — Pipes & Security: Source Code
=============================================================================
This file consolidates all source modules required for Deliverable 4:
  • shell/pipe_handler.py  — subprocess pipeline chaining with fd management
  • shell/security.py      — SHA-256+salt hashing, HMAC login, RBAC
  • main.py additions      — login on startup, pipe dispatch, security commands,
                              file permission enforcement

Features implemented:
  - Unix-style command pipelines: cmd1 | cmd2 | cmd3
  - Secure login (3 attempts, SHA-256+salt, timing-safe hmac.compare_digest)
  - Role-based access control (admin vs. user roles)
  - File permission enforcement (r/w/x per path, per role)
  - Security shell commands: whoami, passwd, useradd, chmod

Data files (not included here — auto-created on first run):
  data/users.json      — hashed+salted user credentials
  data/permissions.json — per-path, per-role permission strings
=============================================================================
"""

# =============================================================================
# FILE: shell/pipe_handler.py
# =============================================================================
"""
pipe_handler.py — Execute a pipeline of external commands.

Each command segment is spawned as a subprocess; stdout of each process
is connected to stdin of the next via subprocess.PIPE.  The final
process inherits the terminal's stdout so its output appears directly.

Usage (from main.py):
    from shell.pipe_handler import run_pipeline
    run_pipeline(commands, background=False)
"""

import subprocess


def run_pipeline(commands: list, background: bool = False) -> None:
    """Run *commands* as a Unix-style pipeline.

    Args:
        commands:   List of token-lists, e.g. [["ls"], ["grep", "txt"]]
        background: If True, don't wait for the last process to finish.
    """
    if not commands:
        return

    procs: list = []
    prev_proc = None

    for i, cmd_tokens in enumerate(commands):
        is_last = (i == len(commands) - 1)

        stdin_src = prev_proc.stdout if prev_proc is not None else None
        # Last proc writes directly to the terminal; others pipe to next
        stdout_dst = None if is_last else subprocess.PIPE

        try:
            proc = subprocess.Popen(
                cmd_tokens,
                stdin=stdin_src,
                stdout=stdout_dst,
                stderr=None,   # inherit terminal stderr
            )
        except FileNotFoundError:
            print(f"shell: {cmd_tokens[0]}: command not found")
            _kill_all(procs)
            if prev_proc and prev_proc.stdout:
                prev_proc.stdout.close()
            return
        except PermissionError:
            print(f"shell: {cmd_tokens[0]}: permission denied")
            _kill_all(procs)
            return

        # Let the child own the read end of the pipe; close it in the parent
        if prev_proc is not None and prev_proc.stdout is not None:
            prev_proc.stdout.close()

        procs.append(proc)
        prev_proc = proc

    if background:
        print(f"[pipeline] started {len(procs)} process(es) in background")
        return

    # Wait for all processes
    for proc in procs:
        proc.wait()


def _kill_all(procs: list) -> None:
    for p in procs:
        try:
            p.kill()
            p.wait()
        except Exception:
            pass


# =============================================================================
# FILE: shell/security.py
# =============================================================================
"""
security.py — Authentication, role-based access control, and file
              permission enforcement for the custom shell.

Password storage:
    Passwords are NEVER stored in plaintext.
    Each user entry holds a SHA-256 hash of (salt + password), plus the salt.
    Verification uses hmac.compare_digest for timing-safe comparison.

Roles:
    admin — unrestricted access to all commands and files.
    user  — read-only on files unless explicitly granted write in permissions.json.

Session state:
    _current_user / _current_role are module-level singletons set after login.
"""

import os
import sys
import json
import hashlib
import hmac
import secrets

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_USERS_FILE = os.path.join(_DATA_DIR, "users.json")
_PERMS_FILE = os.path.join(_DATA_DIR, "permissions.json")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_current_user = None
_current_role = None


def get_current_user():
    return _current_user


def get_current_role():
    return _current_role


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str, salt: str = None):
    """Return (hash_hex, salt_hex).  Generates a fresh salt when not provided."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return digest, salt


def _verify_password(stored_hash: str, salt: str, password: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(stored_hash, candidate)


# ---------------------------------------------------------------------------
# Users persistence
# ---------------------------------------------------------------------------

def _bootstrap_users() -> None:
    """Create data/users.json with default accounts if it does not exist."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    if os.path.exists(_USERS_FILE):
        return
    users = {}
    for username, password, role in [
        ("admin", "admin123", "admin"),
        ("alice",  "alice123",  "user"),
    ]:
        h, s = hash_password(password)
        users[username] = {"hash": h, "salt": s, "role": role}
    with open(_USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_users() -> dict:
    with open(_USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users: dict) -> None:
    with open(_USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# ---------------------------------------------------------------------------
# Permissions persistence
# ---------------------------------------------------------------------------

def _bootstrap_permissions() -> None:
    """Create data/permissions.json with sample entries if missing."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    if os.path.exists(_PERMS_FILE):
        return
    perms = {
        "system/config.txt": {"admin": "rwx", "user": "---"},
        "system/log.txt":    {"admin": "rwx", "user": "r--"},
        "myfile.txt":        {"admin": "rwx", "user": "rwx"},
    }
    with open(_PERMS_FILE, "w") as f:
        json.dump(perms, f, indent=2)


def load_permissions() -> dict:
    with open(_PERMS_FILE, "r") as f:
        return json.load(f)


def save_permissions(perms: dict) -> None:
    with open(_PERMS_FILE, "w") as f:
        json.dump(perms, f, indent=2)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login() -> None:
    """Show a login prompt; allow up to 3 attempts.  Sets session on success."""
    global _current_user, _current_role

    _bootstrap_users()
    _bootstrap_permissions()

    users = load_users()
    max_attempts = 3

    print("=" * 44)
    print("   MyShell 1.0  —  Login Required")
    print("=" * 44)

    for attempt in range(1, max_attempts + 1):
        try:
            username = input("Username: ").strip()
            password = input("Password: ").strip()
        except EOFError:
            print("\nLogin cancelled.")
            sys.exit(1)

        if username in users:
            u = users[username]
            if _verify_password(u["hash"], u["salt"], password):
                _current_user = username
                _current_role = u["role"]
                print(f"\nWelcome, {username}!  (role: {_current_role})\n")
                return

        remaining = max_attempts - attempt
        if remaining > 0:
            print(f"  Invalid credentials. {remaining} attempt(s) remaining.\n")

    print("Too many failed login attempts. Exiting.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Permission check
# ---------------------------------------------------------------------------

def check_permission(path: str, op: str) -> bool:
    """Return True if the current user has *op* permission on *path*.

    op: 'r' (read), 'w' (write/delete/create), 'x' (execute)

    Admins always pass.  Standard users default to read-only for unknown paths.
    """
    if _current_role == "admin":
        return True

    perms = load_permissions()

    # Try the path as-is, then normalised
    entry = perms.get(path) or perms.get(os.path.normpath(path))
    if entry is None:
        # Unknown path: users may read but not write
        return op == "r"

    allowed_str = entry.get("user", "r--")
    return op in allowed_str


# ---------------------------------------------------------------------------
# Security commands
# ---------------------------------------------------------------------------

def cmd_whoami(_args: list) -> None:
    print(f"{_current_user}  (role: {_current_role})")


def cmd_passwd(_args: list) -> None:
    """Change the current user's password."""
    users = load_users()
    try:
        old = input("Current password: ").strip()
    except EOFError:
        return

    u = users[_current_user]
    if not _verify_password(u["hash"], u["salt"], old):
        print("shell: passwd: incorrect current password")
        return

    try:
        new1 = input("New password: ").strip()
        new2 = input("Confirm new password: ").strip()
    except EOFError:
        return

    if not new1:
        print("shell: passwd: password cannot be empty")
        return
    if new1 != new2:
        print("shell: passwd: passwords do not match")
        return

    h, s = hash_password(new1)
    users[_current_user]["hash"] = h
    users[_current_user]["salt"] = s
    save_users(users)
    print("Password updated successfully.")


def cmd_useradd(args: list) -> None:
    """useradd <username> — admin only."""
    if _current_role != "admin":
        print("shell: useradd: permission denied (admin only)")
        return
    if not args:
        print("shell: useradd: usage: useradd <username>")
        return

    username = args[0]
    users = load_users()
    if username in users:
        print(f"shell: useradd: user '{username}' already exists")
        return

    try:
        pwd1 = input(f"Password for '{username}': ").strip()
        pwd2 = input("Confirm password: ").strip()
    except EOFError:
        return

    if not pwd1:
        print("shell: useradd: password cannot be empty")
        return
    if pwd1 != pwd2:
        print("shell: useradd: passwords do not match")
        return

    h, s = hash_password(pwd1)
    users[username] = {"hash": h, "salt": s, "role": "user"}
    save_users(users)
    print(f"User '{username}' created with role 'user'.")


def cmd_chmod(args: list) -> None:
    """chmod <path> <perms> — admin only.

    perms: any combination of r, w, x  (e.g. rw)  or --- to deny all.
    """
    if _current_role != "admin":
        print("shell: chmod: permission denied (admin only)")
        return
    if len(args) < 2:
        print("shell: chmod: usage: chmod <path> <perms>   e.g. chmod myfile.txt rw")
        return

    path, perms_str = args[0], args[1]
    valid = set("rwx-")
    if not all(c in valid for c in perms_str):
        print(f"shell: chmod: invalid permission string '{perms_str}'. Use r/w/x or ---")
        return

    data = load_permissions()
    if path not in data:
        data[path] = {"admin": "rwx", "user": perms_str}
    else:
        data[path]["user"] = perms_str
    save_permissions(data)
    print(f"Permissions for '{path}': user={perms_str}")


# =============================================================================
# FILE: main.py  (Deliverable 4 — login, pipe dispatch, security integration)
# =============================================================================
"""
Relevant sections of main.py for Deliverable 4:
  - login() called on startup
  - pipe commands dispatched to run_pipeline()
  - security (whoami/passwd/useradd/chmod) commands
  - file-permission checks applied to cat/ls/rm/touch/mkdir/rmdir

The REPL portion shown below is simplified to highlight D4 additions.
The full main.py also includes D2 (scheduler) and D3 (memory/sync) handlers.
"""

import sys as _sys


def repl_d4_demo(get_current_user_fn, check_permission_fn) -> None:
    """
    Illustrates how Deliverable 4 additions integrate into the REPL loop.
    In the full project this is part of the main repl() function in main.py.
    """
    # On startup:  security.login()  — called before entering the REPL
    # This sets _current_user and _current_role for the session.

    # Inside the REPL loop, after parsing the command line:
    #
    # if is_pipe:
    #     run_pipeline(tokens, background)   # pipe dispatch  (D4)
    #     continue
    #
    # Security commands
    # if cmd == "whoami":  security.cmd_whoami(args); continue
    # if cmd == "passwd":  security.cmd_passwd(args); continue
    # if cmd == "useradd": security.cmd_useradd(args); continue
    # if cmd == "chmod":   security.cmd_chmod(args); continue
    #
    # File-permission enforcement
    # _READ_CMDS  = {"cat", "ls"}
    # _WRITE_CMDS = {"rm", "touch", "mkdir", "rmdir"}
    # if cmd in _READ_CMDS:
    #     if not security.check_permission(args[0] if args else ".", "r"):
    #         print(f"shell: {cmd}: Permission denied"); continue
    # if cmd in _WRITE_CMDS:
    #     if not security.check_permission(args[0] if args else ".", "w"):
    #         print(f"shell: {cmd}: Permission denied"); continue
    pass


def main() -> None:
    try:
        login()          # Authenticate user before REPL starts
        # repl()         # Full REPL (includes D1-D4 command dispatch)
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        _sys.exit(code)


if __name__ == "__main__":
    print("This file contains library code for Deliverable 4.")
    print("Run 'python main.py' from the project root to start the full shell.")
    print()
    print("Demonstrating security module bootstrap and permission check...")
    # Bootstrap will create data/users.json and data/permissions.json
    _bootstrap_users()
    _bootstrap_permissions()
    print("data/users.json and data/permissions.json created (if not already present).")
    print()
    print("Permission check examples (as 'user' role):")
    # Temporarily set role for demo
    _current_role = "user"
    print(f"  cat system/config.txt -> r allowed: {check_permission('system/config.txt', 'r')}")
    print(f"  rm  system/config.txt -> w allowed: {check_permission('system/config.txt', 'w')}")
    print(f"  cat myfile.txt        -> r allowed: {check_permission('myfile.txt', 'r')}")
