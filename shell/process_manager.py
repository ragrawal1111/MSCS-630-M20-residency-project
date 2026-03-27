"""
process_manager.py — External command execution and job control.

Provides:
  run_command(tokens, background) — launch a foreground or background process
  jobs(args)                      — list background/stopped jobs
  fg(args)                        — bring a job to the foreground
  bg(args)                        — resume a stopped job in the background
"""
import os
import signal
import subprocess
import sys

# ---------------------------------------------------------------------------
# Job table
# Each entry: { 'pid': int, 'status': str, 'cmd': str, 'process': Popen }
# ---------------------------------------------------------------------------
_jobs: dict[int, dict] = {}
_next_job_id: int = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reap_finished_jobs() -> None:
    """Remove jobs whose processes have already exited from the table."""
    finished = [jid for jid, job in _jobs.items()
                if job["process"].poll() is not None]
    for jid in finished:
        del _jobs[jid]


def _resolve_job_id(args: list[str], verb: str) -> int | None:
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_command(tokens: list[str], background: bool = False) -> int:
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
            # Ctrl-C: terminate child, let the REPL continue
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


def jobs(args: list[str]) -> None:
    """List all tracked background/stopped jobs."""
    _reap_finished_jobs()
    if not _jobs:
        return
    for jid, job in sorted(_jobs.items()):
        rc = job["process"].poll()
        status = "Done" if rc is not None else job["status"]
        print(f"[{jid}]  {status:<12} {job['cmd']}")


def fg(args: list[str]) -> None:
    """Bring a background job to the foreground."""
    jid = _resolve_job_id(args, "fg")
    if jid is None:
        return

    job = _jobs.pop(jid)
    print(job["cmd"])

    # On Unix, send SIGCONT so a stopped process resumes
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


def bg(args: list[str]) -> None:
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
        # Windows does not support SIGCONT; mark as running anyway
        job["status"] = "Running"
        print(f"[{jid}] {job['cmd']} &")
