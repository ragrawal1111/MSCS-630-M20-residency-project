"""
main.py — Entry point and REPL loop for the custom shell.

Usage:
    python main.py
"""
import os
import sys

from shell.parser import parse
from shell.builtins import BUILTINS
import shell.process_manager as process_manager
import shell.scheduler as scheduler_mod
from shell.scheduler import (
    RoundRobinScheduler, PriorityScheduler,
    set_scheduler, get_scheduler,
)

# Job-control commands handled by process_manager
_JOB_CONTROL = {
    "jobs": process_manager.jobs,
    "fg": process_manager.fg,
    "bg": process_manager.bg,
}


# ---------------------------------------------------------------------------
# Scheduler command handlers
# ---------------------------------------------------------------------------

def _cmd_schedule(args: list[str]) -> None:
    """schedule rr <quantum>  |  schedule priority"""
    if not args:
        print("shell: schedule: usage: schedule rr <quantum> | schedule priority")
        return
    mode = args[0].lower()
    if mode == "rr":
        if len(args) < 2:
            print("shell: schedule rr: missing quantum argument")
            return
        try:
            quantum = float(args[1])
        except ValueError:
            print(f"shell: schedule rr: invalid quantum '{args[1]}'")
            return
        set_scheduler(RoundRobinScheduler(quantum))
        print(f"Round-Robin scheduler ready (quantum={quantum}s). Use 'add-task' then 'run-scheduler'.")
    elif mode == "priority":
        set_scheduler(PriorityScheduler())
        print("Priority scheduler ready. Use 'add-task' then 'run-scheduler'.")
    else:
        print(f"shell: schedule: unknown mode '{mode}'. Use 'rr' or 'priority'.")


def _cmd_add_task(args: list[str]) -> None:
    """add-task <name> <burst> <priority>"""
    if len(args) < 3:
        print("shell: add-task: usage: add-task <name> <burst> <priority>")
        return
    sched = get_scheduler()
    if sched is None:
        print("shell: add-task: no active scheduler. Run 'schedule rr <q>' or 'schedule priority' first.")
        return
    name = args[0]
    try:
        burst = float(args[1])
        priority = int(args[2])
    except ValueError:
        print("shell: add-task: burst must be a number, priority must be an integer")
        return
    sched.add_task(name, burst, priority)


def _cmd_run_scheduler(args: list[str]) -> None:
    """run-scheduler"""
    sched = get_scheduler()
    if sched is None:
        print("shell: run-scheduler: no active scheduler.")
        return
    sched.run()
    set_scheduler(None)   # reset after run


def repl() -> None:
    """Read-Eval-Print Loop — runs until the user types 'exit' or sends EOF."""
    print("MyShell 1.0  —  Type 'exit' to quit, Ctrl-D to quit")

    while True:
        # Build a prompt that shows the current directory
        try:
            cwd = os.getcwd()
        except FileNotFoundError:
            cwd = "?"

        try:
            line = input(f"myshell:{cwd}$ ")
        except EOFError:
            # Ctrl-D
            print()
            break
        except KeyboardInterrupt:
            # Ctrl-C at the prompt — just print a newline and continue
            print()
            continue

        line = line.strip()
        if not line:
            continue

        tokens, is_pipe, background = parse(line)
        if tokens is None:
            continue

        # Pipe support is implemented in Deliverable 4
        if is_pipe:
            print("shell: pipes are not yet supported (see Deliverable 4)")
            continue

        cmd = tokens[0]
        args = tokens[1:]

        # Scheduler commands
        if cmd == "schedule":
            _cmd_schedule(args)
            continue
        if cmd == "add-task":
            _cmd_add_task(args)
            continue
        if cmd == "run-scheduler":
            _cmd_run_scheduler(args)
            continue

        # Job-control built-ins
        if cmd in _JOB_CONTROL:
            _JOB_CONTROL[cmd](args)
            continue

        # Shell built-ins
        if cmd in BUILTINS:
            try:
                BUILTINS[cmd](args)
            except SystemExit:
                raise       # Let exit/sys.exit propagate cleanly
            continue

        # External command
        process_manager.run_command(tokens, background)


def main() -> None:
    try:
        repl()
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        sys.exit(code)


if __name__ == "__main__":
    main()
