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


def run_pipeline(commands: list[list[str]], background: bool = False) -> None:
    """Run *commands* as a Unix-style pipeline.

    Args:
        commands:   List of token-lists, e.g. [["ls"], ["grep", "txt"]]
        background: If True, don't wait for the last process to finish.
    """
    if not commands:
        return

    procs: list[subprocess.Popen] = []
    prev_proc: subprocess.Popen | None = None

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

    # Wait for all processes in reverse order (last first is fine either way)
    for proc in procs:
        proc.wait()


def _kill_all(procs: list[subprocess.Popen]) -> None:
    for p in procs:
        try:
            p.kill()
            p.wait()
        except Exception:
            pass
