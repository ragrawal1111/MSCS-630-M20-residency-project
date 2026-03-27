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

# Job-control commands handled by process_manager
_JOB_CONTROL = {
    "jobs": process_manager.jobs,
    "fg": process_manager.fg,
    "bg": process_manager.bg,
}


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
