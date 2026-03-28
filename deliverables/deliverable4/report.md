# Deliverable 4 — Report

## 1. Integration Overview

Deliverable 4 brings all four OS concepts together into a single, cohesive shell. The architecture is a layered dispatcher: authentication gates entry, the REPL loop parses and routes commands, and security checks intercept file-touching operations before they reach built-ins.

### Component Map
| Component | Module | Integrated In |
|-----------|--------|--------------|
| Process Management | `shell/process_manager.py` | `main.py` dispatcher |
| Scheduling | `shell/scheduler.py` | `main.py` dispatcher (schedule / add-task / run-scheduler) |
| Memory Management | `shell/memory_manager.py` | `main.py` dispatcher (mem-*) |
| Synchronization | `shell/synchronization.py` | `main.py` dispatcher (mutex-* / sem-* / run-*) |
| Piping | `shell/pipe_handler.py` | `main.py` — replaces the D1–D3 stub |
| Security | `shell/security.py` | `main.py` — login on startup, check before every file command |

### Data Flow

```
User input
    │
    ▼
parser.parse(line)          ← shlex tokenizer, pipe/background detection
    │
    ├─ is_pipe? ──────────► pipe_handler.run_pipeline(segments)
    │
    └─ single command ────► security permission check (for file cmds)
                                │
                                ├─ security commands  (whoami / passwd / useradd / chmod)
                                ├─ scheduler commands (schedule / add-task / run-scheduler)
                                ├─ memory commands    (mem-init … mem-free)
                                ├─ sync commands      (mutex-* / sem-* / run-*)
                                ├─ job-control        (jobs / fg / bg)
                                ├─ BUILTINS           (cd / ls / cat / rm …)
                                └─ external command   ← process_manager.run_command
```

All modules share state through module-level singletons: `security._current_user/role`, `scheduler._active_scheduler`, `memory_manager._mem`. No global mutable state is passed between functions as arguments; each module manages its own lifecycle.

## 2. Piping Implementation

Piping is implemented in `shell/pipe_handler.py` using `subprocess.Popen`.

### Pipeline construction

1. `parser.parse()` splits the input line on `|` and returns a `list[list[str]]` where each sub-list is one command segment.
2. `main.py` detects `is_pipe=True` and delegates to `run_pipeline(commands)`.
3. `run_pipeline()` iterates over segments left-to-right:
   - For all but the last segment, `stdout=subprocess.PIPE` captures output as a readable stream.
   - For the last segment, `stdout=None` so output flows directly to the terminal.
   - Each process's `stdin` is set to the **previous process's `stdout` pipe** object.
   - After spawning each child, the **parent immediately closes its copy** of the read end of the pipe (`prev_proc.stdout.close()`). This is critical: without this, `sort` and similar commands that wait for EOF will hang forever because the parent still holds an open file descriptor.
4. After spawning all processes, the parent calls `proc.wait()` on each, collecting exit codes and preventing zombies.

### Error handling

- `FileNotFoundError` → "command not found" message; all already-started processes are killed.
- `PermissionError` → "permission denied" message; same cleanup.
- Background pipelines (`cmd1 | cmd2 &`) skip the wait loop and print a status message.

### File descriptor discipline

The key invariant is: **every file descriptor is owned by exactly one process at a time**. The parent transfers ownership of each pipe's read end to the next child by passing `stdin=prev_proc.stdout`, then immediately closes its own copy. This avoids both fd leaks and the classic "pipeline hangs at EOF" bug.

## 3. Security Mechanisms

### User Authentication

The login flow (`security.login()`) is called once from `main()` before the REPL starts:

1. Prompts for username and password (up to 3 attempts).
2. Looks up the username in `data/users.json`.
3. Calls `_verify_password(stored_hash, salt, entered_password)`:
   - Recomputes `SHA-256(salt + entered_password)`.
   - Compares with `hmac.compare_digest()` — a **timing-safe** comparison that prevents timing-based side-channel attacks (an attacker cannot learn whether the hash prefix matched by measuring response time).
4. On success, sets `_current_user` and `_current_role` module globals. On 3 consecutive failures, calls `sys.exit(1)`.

**Password storage:**  
`data/users.json` stores only `{hash, salt, role}` — never plaintext. A fresh 16-byte random salt (`secrets.token_hex(16)`) is generated for each user entry, preventing rainbow-table attacks.

```json
{
  "admin": { "hash": "<sha256_hex>", "salt": "<random_hex>", "role": "admin" },
  "alice":  { "hash": "<sha256_hex>", "salt": "<random_hex>", "role": "user"  }
}
```

### Role-Based Access Control

Two roles control what operations are permitted:

| Operation | admin | user |
|-----------|-------|------|
| All file reads | ✅ | Default: ✅ (unless denied in permissions.json) |
| All file writes | ✅ | Default: ❌ (unless granted in permissions.json) |
| `useradd` | ✅ | ❌ — "permission denied (admin only)" |
| `chmod` | ✅ | ❌ — "permission denied (admin only)" |

`check_permission(path, op)` is called in `main.py` before dispatching `cat`, `ls`, `rm`, `touch`, `mkdir`, `rmdir`. Admins always pass. For standard users the lookup proceeds as follows:

### File Permissions

`data/permissions.json` stores per-path entries:

```json
{
  "system/config.txt": { "admin": "rwx", "user": "---" },
  "system/log.txt":    { "admin": "rwx", "user": "r--" },
  "myfile.txt":        { "admin": "rwx", "user": "rwx" }
}
```

`check_permission(path, op)`:
1. If role == `"admin"` → return `True` immediately.
2. Look up the path in `permissions.json` (exact match, then `os.path.normpath` match).
3. If no entry exists → default: `"r"` allowed, write/execute denied.
4. If an entry exists → check whether `op` (`'r'`, `'w'`, or `'x'`) appears in the `user` permission string.

`chmod <path> <perms>` (admin only) updates `data/permissions.json` in-place, persisting across sessions.

## 4. Challenges and Improvements

### Challenges

1. **File-descriptor ownership in pipelines**: The classic "pipeline hangs" bug — where `sort` waits indefinitely for EOF because the parent still holds the read end of the pipe — required carefully closing `prev_proc.stdout` in the parent immediately after passing it to the next child. This is subtle and not obvious from the `subprocess` documentation.

2. **Timing-safe password comparison**: A naive `==` comparison of password hashes is vulnerable to timing attacks. Using `hmac.compare_digest` ensures the comparison takes constant time regardless of where a mismatch occurs.

3. **Bootstrapping data files**: The `data/users.json` and `data/permissions.json` files must exist before login. The `_bootstrap_*` functions create them with default accounts and entries if they are absent, enabling the shell to run in a fresh clone without a manual setup step.

4. **Integrating security checks without modifying built-ins**: Rather than adding `check_permission` calls inside each built-in function (which would couple `builtins.py` to `security.py`), the permission check is placed in `main.py` immediately before dispatching to `BUILTINS[cmd]`. This keeps each module single-purpose.

5. **Pipe support for built-in commands**: Built-in commands (e.g., `ls`, `cat`) run in the same process and cannot have their `stdout` captured by `subprocess.PIPE`. For this simulation, piping is restricted to external executables. Fully supporting built-ins in pipelines would require forking the shell process or redirecting `sys.stdout` — a significant complexity increase left for future work.

### Potential Improvements

- Add a `sudo` command that temporarily elevates a user to admin for a single command after re-entering their password.
- Implement `getent passwd`-style user listing with a `users` command.
- Support piping from/to built-in commands by capturing their `sys.stdout` output into a `io.StringIO` buffer and feeding it as `stdin` to the next subprocess.
- Add an audit log that records every command executed, the user, timestamp, and outcome — addressing the OWASP "Security Logging and Monitoring Failures" control.
- Store `data/users.json` with file-system permissions (`chmod 600`) so only the shell process owner can read it.
