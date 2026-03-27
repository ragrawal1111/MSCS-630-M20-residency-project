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
def do_cd(args: list[str]) -> None:
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
def do_pwd(args: list[str]) -> None:
    """Print the current working directory."""
    print(os.getcwd())


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@_register("echo")
def do_echo(args: list[str]) -> None:
    """Print arguments to stdout."""
    print(" ".join(args))


# ---------------------------------------------------------------------------
# File system — read
# ---------------------------------------------------------------------------

@_register("ls")
def do_ls(args: list[str]) -> None:
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
def do_cat(args: list[str]) -> None:
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
def do_mkdir(args: list[str]) -> None:
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
def do_rmdir(args: list[str]) -> None:
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
            # Covers both non-empty directory and permission denied
            print(f"shell: rmdir: failed to remove '{dirname}': {exc.strerror}")


@_register("rm")
def do_rm(args: list[str]) -> None:
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
def do_touch(args: list[str]) -> None:
    """Create a file or update its modification timestamp."""
    if not args:
        print("shell: touch: missing file operand")
        return
    for filename in args:
        try:
            # 'a' mode creates the file if absent; utime updates the timestamp
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
def do_kill(args: list[str]) -> None:
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
def do_clear(args: list[str]) -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


@_register("exit")
def do_exit(args: list[str]) -> None:
    """Exit the shell with an optional exit code."""
    code = 0
    if args:
        try:
            code = int(args[0])
        except ValueError:
            print(f"shell: exit: {args[0]}: numeric argument required")
    sys.exit(code)
