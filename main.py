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
import shell.memory_manager as mem_mod
from shell.memory_manager import MemoryManager, set_memory_manager, get_memory_manager
import shell.synchronization as sync_mod
import shell.security as security
from shell.pipe_handler import run_pipeline

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


# ---------------------------------------------------------------------------
# Memory management command handlers (Deliverable 3)
# ---------------------------------------------------------------------------

def _cmd_mem_init(args: list[str]) -> None:
    """mem-init <frames> [fifo|lru]"""
    if not args:
        print("shell: mem-init: usage: mem-init <frames> [fifo|lru]")
        return
    try:
        frames = int(args[0])
    except ValueError:
        print(f"shell: mem-init: invalid frame count '{args[0]}'")
        return
    algo = args[1].lower() if len(args) > 1 else "fifo"
    if algo not in ("fifo", "lru"):
        print(f"shell: mem-init: unknown algorithm '{algo}'. Use fifo or lru.")
        return
    set_memory_manager(MemoryManager(frames, algo))
    print(f"Memory manager initialised: {frames} frames, {algo.upper()} replacement.")


def _cmd_mem_alloc(args: list[str]) -> None:
    """mem-alloc <proc_id> <page0> [page1 ...]"""
    if len(args) < 2:
        print("shell: mem-alloc: usage: mem-alloc <proc_id> <pages...>")
        return
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-alloc: no memory manager. Run 'mem-init' first.")
        return
    proc_id = args[0]
    try:
        pages = [int(p) for p in args[1:]]
    except ValueError:
        print("shell: mem-alloc: page numbers must be integers")
        return
    mem.alloc(proc_id, pages)


def _cmd_mem_access(args: list[str]) -> None:
    """mem-access <proc_id> <page>"""
    if len(args) < 2:
        print("shell: mem-access: usage: mem-access <proc_id> <page>")
        return
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-access: no memory manager. Run 'mem-init' first.")
        return
    try:
        page = int(args[1])
    except ValueError:
        print(f"shell: mem-access: invalid page number '{args[1]}'")
        return
    mem.access(args[0], page)


def _cmd_mem_status(args: list[str]) -> None:
    """mem-status"""
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-status: no memory manager. Run 'mem-init' first.")
        return
    mem.status()


def _cmd_mem_free(args: list[str]) -> None:
    """mem-free <proc_id>"""
    if not args:
        print("shell: mem-free: usage: mem-free <proc_id>")
        return
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-free: no memory manager. Run 'mem-init' first.")
        return
    mem.free(args[0])


# ---------------------------------------------------------------------------
# Synchronization command handlers (Deliverable 3)
# ---------------------------------------------------------------------------

def _cmd_mutex_create(args: list[str]) -> None:
    if not args:
        print("shell: mutex-create: usage: mutex-create <name>"); return
    sync_mod.mutex_create(args[0])


def _cmd_mutex_lock(args: list[str]) -> None:
    if not args:
        print("shell: mutex-lock: usage: mutex-lock <name>"); return
    sync_mod.mutex_lock(args[0])


def _cmd_mutex_unlock(args: list[str]) -> None:
    if not args:
        print("shell: mutex-unlock: usage: mutex-unlock <name>"); return
    sync_mod.mutex_unlock(args[0])


def _cmd_sem_create(args: list[str]) -> None:
    if len(args) < 2:
        print("shell: sem-create: usage: sem-create <name> <value>"); return
    try:
        val = int(args[1])
    except ValueError:
        print(f"shell: sem-create: invalid value '{args[1]}'"); return
    sync_mod.sem_create(args[0], val)


def _cmd_sem_wait(args: list[str]) -> None:
    if not args:
        print("shell: sem-wait: usage: sem-wait <name>"); return
    sync_mod.sem_wait(args[0])


def _cmd_sem_signal(args: list[str]) -> None:
    if not args:
        print("shell: sem-signal: usage: sem-signal <name>"); return
    sync_mod.sem_signal(args[0])


def _cmd_run_producer_consumer(args: list[str]) -> None:
    """run-producer-consumer <producers> <consumers> <items> <buffer_size>"""
    if len(args) < 4:
        print("shell: run-producer-consumer: usage: run-producer-consumer <producers> <consumers> <items> <buffer_size>")
        return
    try:
        p, c, items, buf = int(args[0]), int(args[1]), int(args[2]), int(args[3])
    except ValueError:
        print("shell: run-producer-consumer: all arguments must be integers"); return
    sync_mod.run_producer_consumer(p, c, items, buf)


def _cmd_run_dining_philosophers(args: list[str]) -> None:
    """run-dining-philosophers <num> <eat_time>"""
    if len(args) < 2:
        print("shell: run-dining-philosophers: usage: run-dining-philosophers <num> <eat_time>")
        return
    try:
        num = int(args[0])
        eat = float(args[1])
    except ValueError:
        print("shell: run-dining-philosophers: invalid arguments"); return
    sync_mod.run_dining_philosophers(num, eat)


def repl() -> None:
    """Read-Eval-Print Loop — runs until the user types 'exit' or sends EOF."""
    print("MyShell 1.0  —  Type 'exit' to quit, Ctrl-D to quit")

    while True:
        # Build a prompt that shows the current user and directory
        try:
            cwd = os.getcwd()
        except FileNotFoundError:
            cwd = "?"

        user = security.get_current_user() or "?"
        try:
            line = input(f"{user}@myshell:{cwd}$ ")
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

        # Pipe — Deliverable 4
        if is_pipe:
            run_pipeline(tokens, background)
            continue

        cmd = tokens[0]
        args = tokens[1:]

        # Security / user-management commands (Deliverable 4)
        if cmd == "whoami":
            security.cmd_whoami(args)
            continue
        if cmd == "passwd":
            security.cmd_passwd(args)
            continue
        if cmd == "useradd":
            security.cmd_useradd(args)
            continue
        if cmd == "chmod":
            security.cmd_chmod(args)
            continue

        # File-permission checks for built-ins that touch the filesystem
        _READ_CMDS  = {"cat", "ls"}
        _WRITE_CMDS = {"rm", "touch", "mkdir", "rmdir"}
        if cmd in _READ_CMDS:
            target = args[0] if args else "."
            if not security.check_permission(target, "r"):
                print(f"shell: {cmd}: {target}: Permission denied")
                continue
        if cmd in _WRITE_CMDS:
            target = args[0] if args else "."
            if not security.check_permission(target, "w"):
                print(f"shell: {cmd}: {target}: Permission denied")
                continue

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

        # Memory management commands (Deliverable 3)
        if cmd == "mem-init":
            _cmd_mem_init(args)
            continue
        if cmd == "mem-alloc":
            _cmd_mem_alloc(args)
            continue
        if cmd == "mem-access":
            _cmd_mem_access(args)
            continue
        if cmd == "mem-status":
            _cmd_mem_status(args)
            continue
        if cmd == "mem-free":
            _cmd_mem_free(args)
            continue

        # Synchronization commands (Deliverable 3)
        if cmd == "mutex-create":
            _cmd_mutex_create(args)
            continue
        if cmd == "mutex-lock":
            _cmd_mutex_lock(args)
            continue
        if cmd == "mutex-unlock":
            _cmd_mutex_unlock(args)
            continue
        if cmd == "sem-create":
            _cmd_sem_create(args)
            continue
        if cmd == "sem-wait":
            _cmd_sem_wait(args)
            continue
        if cmd == "sem-signal":
            _cmd_sem_signal(args)
            continue
        if cmd == "run-producer-consumer":
            _cmd_run_producer_consumer(args)
            continue
        if cmd == "run-dining-philosophers":
            _cmd_run_dining_philosophers(args)
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
        security.login()
        repl()
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        sys.exit(code)


if __name__ == "__main__":
    main()
