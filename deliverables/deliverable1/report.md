# Deliverable 1 — Report

## 1. Process Management

### Overview

The shell follows a classic Read-Eval-Print Loop (REPL) design. On each iteration it reads a line from stdin, hands it to the parser, dispatches to a built-in handler or launches an external process, and then returns to the prompt.

### Foreground Processes

External commands that are **not** suffixed with `&` are run as foreground processes using `subprocess.Popen`. The REPL immediately calls `process.wait()`, which blocks until the child exits. During the wait, `KeyboardInterrupt` (Ctrl-C) is caught: the child is terminated and the shell returns to the prompt rather than exiting.

This mimics the Unix model where the parent process waits (`waitpid`) for the child to terminate, preventing zombie processes.

### Background Processes

When a command ends with `&`, it is launched with `subprocess.Popen` without blocking. The process's PID and metadata are stored in a **job table** (`_jobs` dict in `process_manager.py`). The shell immediately prints `[job_id] pid` and resumes the prompt.

```
myshell:/home$ sleep 10 &
[1] 19234
myshell:/home$
```

### Job Table and Job Control

The `_jobs` dictionary acts as the job table, keyed by an auto-incrementing job ID. Each entry stores:

| Field     | Description                        |
|-----------|------------------------------------|
| `pid`     | OS process identifier              |
| `status`  | `"Running"` or `"Done"`            |
| `cmd`     | The original command string        |
| `process` | The `Popen` object for the child   |

Three built-in commands interact with the table:

- **`jobs`** — calls `_reap_finished_jobs()` to remove exited processes, then prints the remaining entries.
- **`fg [id]`** — pops the entry from the table, sends `SIGCONT` on Unix to resume a stopped process, then calls `process.wait()` to bring it to the foreground.
- **`bg [id]`** — sends `SIGCONT` on Unix to resume a stopped process without blocking the shell.

### Zombie Reaping

`_reap_finished_jobs()` is called before every `jobs`, `fg`, and `bg` invocation. It iterates the table and removes entries where `process.poll()` returns a non-`None` exit code, which internally calls `waitpid` through Python's subprocess layer and prevents zombies from accumulating.

---

## 2. Error Handling

### Command Not Found

If `subprocess.Popen` raises `FileNotFoundError`, the shell prints:

```
shell: command not found: <cmd>
```

and returns exit code 127, matching the POSIX convention.

### Built-in Argument Errors

Every built-in validates its argument list before acting. Missing operands produce a usage hint:

```
shell: mkdir: missing operand
shell: cat: missing file operand
shell: kill: usage: kill <pid>
```

### File-System Errors

All file-system operations (`cd`, `ls`, `cat`, `mkdir`, `rmdir`, `rm`, `touch`) wrap the OS call in a `try/except` block that catches `FileNotFoundError`, `PermissionError`, `IsADirectoryError`, and `NotADirectoryError`. Each prints a descriptive message prefixed with `shell: <cmd>:`.

Example:
```
shell: cd: /root: Permission denied
shell: rm: cannot remove 'ghost.txt': No such file or directory
```

### Invalid PID for `kill`

`do_kill` first parses the argument as an integer; a non-numeric value raises `ValueError` and prints an "invalid pid" message. `ProcessLookupError` covers non-existent PIDs, and `PermissionError` covers insufficient privileges.

### Parse Errors

`shlex.split` raises `ValueError` on unclosed quotes. The parser catches this and prints `shell: parse error: <detail>`, then returns `None` so the REPL skips execution for that line.

### Signals at the Prompt

- **Ctrl-C** (`SIGINT`): caught in the REPL's `except KeyboardInterrupt` block — prints a newline and loops back to the prompt. The shell does **not** exit.
- **Ctrl-D** (`EOF`): caught as `EOFError` — the shell prints a newline and exits cleanly.

---

## 3. Challenges and Improvements

### Challenge 1 — Cross-Platform Signal Handling

Unix job control relies on `SIGCONT` and `SIGSTOP` to suspend and resume processes. Windows does not support these signals. The shell detects `sys.platform` and skips SIGCONT on Windows, meaning that `bg` on Windows marks the job as running but cannot actually un-stop a suspended child. A future improvement would be to use Windows Job Objects or a platform-specific threading approach for equivalent behaviour.

### Challenge 2 — Background I/O

Background processes currently share stdout/stderr with the shell. This means a background process can interleave its output with the shell prompt. A production shell would either redirect background output to a buffer or implement a proper terminal driver (PTY) to separate the streams. For this deliverable the behaviour is acceptable for demonstration purposes.

### Challenge 3 — Exit Code Propagation

Python's built-in `exit` name conflicts with our `do_exit` built-in. The solution was to register the handler under the string key `"exit"` using the `_register` decorator while keeping the function named `do_exit`. The REPL lets `SystemExit` propagate through a bare `raise`, which is then caught in `main()` where `sys.exit()` is called with the correct code.

### Possible Improvements

- **Tab completion** using `readline` for command and filename completion.
- **Command history** persisted to `~/.myshell_history`.
- **Redirections** (`>`, `>>`, `<`) for file I/O, a natural next step before pipes.
- **Signal forwarding**: route `SIGINT` from the prompt to the foreground child group rather than just terminating the child, to match bash behaviour more closely.

