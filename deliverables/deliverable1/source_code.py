"""
=============================================================================
Deliverable 1 — Custom Shell: Source Code
=============================================================================
This file consolidates all source modules required for Deliverable 1:
  • shell/parser.py        — input tokenizer
  • shell/builtins.py      — 12 built-in commands
  • shell/process_manager.py — external command execution & job control
  • main.py                — REPL entry point (D1 portion)

Run the shell:
    python main.py
=============================================================================
"""

# =============================================================================
# FILE: shell/parser.py
# =============================================================================
"""
parser.py — Tokenizes shell input lines.

Returns a (tokens, is_pipe, background) tuple:
  tokens     — list of str for a simple command, or list of list[str] for pipes
  is_pipe    — True when the command contains one or more '|' separators
  background — True when the command ends with '&'
"""
import shlex


def parse(line: str):
    """Parse a raw input line into command tokens.

    Returns:
        (tokens, is_pipe, background)
        On parse error returns (None, False, False).
    """
    line = line.strip()
    if not line:
        return None, False, False

    # Detect and strip trailing '&' for background execution
    background = False
    if line.endswith("&"):
        background = True
        line = line[:-1].strip()

    # Detect pipes — split on '|' at the top level
    if "|" in line:
        segments = line.split("|")
        try:
            commands = [shlex.split(seg.strip()) for seg in segments if seg.strip()]
        except ValueError as exc:
            print(f"shell: parse error: {exc}")
            return None, False, False
        if not commands:
            return None, False, False
        return commands, True, background

    # Plain command
    try:
        tokens = shlex.split(line)
    except ValueError as exc:
        print(f"shell: parse error: {exc}")
        return None, False, False

    if not tokens:
        return None, False, False

    return tokens, False, background


# =============================================================================
# FILE: shell/builtins.py
# =============================================================================
"""
builtins.py — Built-in shell command implementations.

Each command is registered in the BUILTINS dict under its command name.
Every handler receives a list of argument strings (argv[1:]) and returns None.
"""
import os
import signal
import sys

# Maps command name -> handler function
BUILTINS: dict = {}


def _register(name: str):
    """Decorator that registers a function as a built-in command."""
    def decorator(func):
        BUILTINS[name] = func
        return func
    return decorator


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

@_register("cd")
def do_cd(args: list) -> None:
    """Change the current working directory."""
    target = args[0] if args else os.path.expanduser("~")
    try:
        os.chdir(target)
    except FileNotFoundError:
        print(f"shell: cd: {target}: No such file or directory")
    except NotADirectoryError:
        print(f"shell: cd: {target}: Not a directory")
    except PermissionError:
        print(f"shell: cd: {target}: Permission denied")


@_register("pwd")
def do_pwd(args: list) -> None:
    """Print the current working directory."""
    print(os.getcwd())


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@_register("echo")
def do_echo(args: list) -> None:
    """Print arguments to stdout."""
    print(" ".join(args))


# ---------------------------------------------------------------------------
# File system — read
# ---------------------------------------------------------------------------

@_register("ls")
def do_ls(args: list) -> None:
    """List directory contents."""
    target = args[0] if args else "."
    try:
        entries = sorted(os.listdir(target))
        if entries:
            print("  ".join(entries))
    except FileNotFoundError:
        print(f"shell: ls: {target}: No such file or directory")
    except NotADirectoryError:
        print(f"shell: ls: {target}: Not a directory")
    except PermissionError:
        print(f"shell: ls: {target}: Permission denied")


@_register("cat")
def do_cat(args: list) -> None:
    """Concatenate and display file contents."""
    if not args:
        print("shell: cat: missing file operand")
        return
    for filename in args:
        try:
            with open(filename, "r", encoding="utf-8", errors="replace") as fh:
                print(fh.read(), end="")
        except FileNotFoundError:
            print(f"shell: cat: {filename}: No such file or directory")
        except IsADirectoryError:
            print(f"shell: cat: {filename}: Is a directory")
        except PermissionError:
            print(f"shell: cat: {filename}: Permission denied")


# ---------------------------------------------------------------------------
# File system — write / modify
# ---------------------------------------------------------------------------

@_register("mkdir")
def do_mkdir(args: list) -> None:
    """Create a directory."""
    if not args:
        print("shell: mkdir: missing operand")
        return
    for dirname in args:
        try:
            os.mkdir(dirname)
        except FileExistsError:
            print(f"shell: mkdir: cannot create directory '{dirname}': File exists")
        except PermissionError:
            print(f"shell: mkdir: cannot create directory '{dirname}': Permission denied")
        except OSError as exc:
            print(f"shell: mkdir: cannot create directory '{dirname}': {exc.strerror}")


@_register("rmdir")
def do_rmdir(args: list) -> None:
    """Remove an empty directory."""
    if not args:
        print("shell: rmdir: missing operand")
        return
    for dirname in args:
        try:
            os.rmdir(dirname)
        except FileNotFoundError:
            print(f"shell: rmdir: failed to remove '{dirname}': No such file or directory")
        except OSError as exc:
            print(f"shell: rmdir: failed to remove '{dirname}': {exc.strerror}")


@_register("rm")
def do_rm(args: list) -> None:
    """Remove a file."""
    if not args:
        print("shell: rm: missing operand")
        return
    for filename in args:
        try:
            os.remove(filename)
        except FileNotFoundError:
            print(f"shell: rm: cannot remove '{filename}': No such file or directory")
        except IsADirectoryError:
            print(f"shell: rm: cannot remove '{filename}': Is a directory")
        except PermissionError:
            print(f"shell: rm: cannot remove '{filename}': Permission denied")


@_register("touch")
def do_touch(args: list) -> None:
    """Create a file or update its modification timestamp."""
    if not args:
        print("shell: touch: missing file operand")
        return
    for filename in args:
        try:
            with open(filename, "a", encoding="utf-8"):
                os.utime(filename, None)
        except PermissionError:
            print(f"shell: touch: cannot touch '{filename}': Permission denied")
        except OSError as exc:
            print(f"shell: touch: cannot touch '{filename}': {exc.strerror}")


# ---------------------------------------------------------------------------
# Process control
# ---------------------------------------------------------------------------

@_register("kill")
def do_kill(args: list) -> None:
    """Send SIGTERM to a process by PID."""
    if not args:
        print("shell: kill: usage: kill <pid>")
        return
    try:
        pid = int(args[0])
    except ValueError:
        print(f"shell: kill: {args[0]}: invalid pid")
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print(f"shell: kill: ({args[0]}) - No such process")
    except PermissionError:
        print(f"shell: kill: ({args[0]}) - Operation not permitted")
    except OSError as exc:
        print(f"shell: kill: ({args[0]}) - {exc.strerror}")


# ---------------------------------------------------------------------------
# Terminal / session
# ---------------------------------------------------------------------------

@_register("clear")
def do_clear(args: list) -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


@_register("exit")
def do_exit(args: list) -> None:
    """Exit the shell."""
    try:
        code = int(args[0]) if args else 0
    except ValueError:
        code = 0
    sys.exit(code)


# =============================================================================
# FILE: shell/process_manager.py
# =============================================================================
"""
process_manager.py — External command execution and job control.

Provides:
  run_command(tokens, background) — launch a foreground or background process
  jobs(args)                      — list background/stopped jobs
  fg(args)                        — bring a job to the foreground
  bg(args)                        — resume a stopped job in the background
"""
import subprocess

# ---------------------------------------------------------------------------
# Job table
# Each entry: { 'pid': int, 'status': str, 'cmd': str, 'process': Popen }
# ---------------------------------------------------------------------------
_jobs: dict = {}
_next_job_id: int = 1


def _reap_finished_jobs() -> None:
    """Remove jobs whose processes have already exited from the table."""
    finished = [jid for jid, job in _jobs.items()
                if job["process"].poll() is not None]
    for jid in finished:
        del _jobs[jid]


def _resolve_job_id(args: list, verb: str):
    """Return a validated job ID from args, or None on error."""
    _reap_finished_jobs()
    if not _jobs:
        print(f"shell: {verb}: no current job")
        return None
    if not args:
        return max(_jobs.keys())
    try:
        jid = int(args[0])
    except ValueError:
        print(f"shell: {verb}: {args[0]}: invalid job id")
        return None
    if jid not in _jobs:
        print(f"shell: {verb}: {jid}: no such job")
        return None
    return jid


def run_command(tokens: list, background: bool = False) -> int:
    """Execute an external command.

    Foreground: blocks the REPL until the process exits.
    Background: starts the process and returns immediately; prints [id] pid.

    Returns the exit code (0 for background launches).
    """
    global _next_job_id

    _reap_finished_jobs()

    try:
        if background:
            process = subprocess.Popen(
                tokens,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            job_id = _next_job_id
            _next_job_id += 1
            _jobs[job_id] = {
                "pid": process.pid,
                "status": "Running",
                "cmd": " ".join(tokens),
                "process": process,
            }
            print(f"[{job_id}] {process.pid}")
            return 0

        # Foreground — block until done
        process = subprocess.Popen(tokens)
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            print()
        return process.returncode if process.returncode is not None else 0

    except FileNotFoundError:
        print(f"shell: command not found: {tokens[0]}")
        return 127
    except PermissionError:
        print(f"shell: {tokens[0]}: Permission denied")
        return 126
    except OSError as exc:
        print(f"shell: {tokens[0]}: {exc.strerror}")
        return 1


def jobs(args: list) -> None:
    """List all tracked background/stopped jobs."""
    _reap_finished_jobs()
    if not _jobs:
        return
    for jid, job in sorted(_jobs.items()):
        rc = job["process"].poll()
        status = "Done" if rc is not None else job["status"]
        print(f"[{jid}]  {status:<12} {job['cmd']}")


def fg(args: list) -> None:
    """Bring a background job to the foreground."""
    jid = _resolve_job_id(args, "fg")
    if jid is None:
        return

    job = _jobs.pop(jid)
    print(job["cmd"])

    if sys.platform != "win32":
        try:
            os.kill(job["pid"], signal.SIGCONT)
        except ProcessLookupError:
            pass

    try:
        job["process"].wait()
    except KeyboardInterrupt:
        job["process"].terminate()
        try:
            job["process"].wait(timeout=2)
        except subprocess.TimeoutExpired:
            job["process"].kill()
        print()


def bg(args: list) -> None:
    """Resume a stopped job in the background."""
    jid = _resolve_job_id(args, "bg")
    if jid is None:
        return

    job = _jobs[jid]

    if sys.platform != "win32":
        try:
            os.kill(job["pid"], signal.SIGCONT)
            job["status"] = "Running"
            print(f"[{jid}] {job['cmd']} &")
        except ProcessLookupError:
            print(f"shell: bg: ({jid}) - No such process")
            _jobs.pop(jid, None)
    else:
        job["status"] = "Running"
        print(f"[{jid}] {job['cmd']} &")


# =============================================================================
# FILE: main.py  (Deliverable 1 — core REPL)
# =============================================================================
"""
main.py — Entry point and REPL loop for the custom shell (Deliverable 1).
"""

_JOB_CONTROL = {
    "jobs": jobs,
    "fg": fg,
    "bg": bg,
}


def repl() -> None:
    """Read-Eval-Print Loop — runs until the user types 'exit' or sends EOF."""
    print("MyShell 1.0  —  Type 'exit' to quit, Ctrl-D to quit")

    while True:
        try:
            cwd = os.getcwd()
        except FileNotFoundError:
            cwd = "?"

        try:
            line = input(f"myshell:{cwd}$ ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        line = line.strip()
        if not line:
            continue

        tokens, is_pipe, background = parse(line)
        if tokens is None:
            continue

        if is_pipe:
            print("shell: pipes not supported in Deliverable 1 standalone mode")
            continue

        cmd = tokens[0]
        args = tokens[1:]

        # Job-control built-ins
        if cmd in _JOB_CONTROL:
            _JOB_CONTROL[cmd](args)
            continue

        # Shell built-ins
        if cmd in BUILTINS:
            try:
                BUILTINS[cmd](args)
            except SystemExit:
                raise
            continue

        # External command
        run_command(tokens, background)


def main() -> None:
    try:
        repl()
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        sys.exit(code)


if __name__ == "__main__":
    main()
