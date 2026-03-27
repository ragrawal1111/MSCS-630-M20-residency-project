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
