# Deliverable 1 — Basic Shell Implementation and Process Management

## Status: Complete

## What to Submit
- [x] Complete source code (`main.py`, `shell/parser.py`, `shell/builtins.py`, `shell/process_manager.py`)
- [x] Report (see `report.md`)
- [ ] Screenshots (place in `screenshots/` folder)

## Key Files
| File | Purpose |
|------|---------|
| `shell/parser.py` | Tokenizes input, detects pipes and `&` |
| `shell/builtins.py` | All built-in command implementations |
| `shell/process_manager.py` | `run_command()`, job table, fg/bg/jobs |

## Commands to Demonstrate
- `cd`, `pwd`, `ls`, `echo`, `cat`, `mkdir`, `rmdir`, `rm`, `touch`, `kill`, `clear`, `exit`
- `jobs`, `fg [id]`, `bg [id]`
- A command run in background with `&`
- An invalid command producing an error

## Notes
<!-- Add implementation notes here as you work -->
