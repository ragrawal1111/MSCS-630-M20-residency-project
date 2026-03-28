# Deliverable 4 — Integration and Security Implementation

## Status: Complete

## What to Submit
- [x] Complete integrated source code (all modules wired in `main.py`)
- [x] Updated `data/users.json` and `data/permissions.json`
- [x] Report (see `report.md`)
- [x] Screenshots (place in `screenshots/` folder)

## Key Files
| File | Purpose |
|------|---------|
| `shell/pipe_handler.py` | Pipeline construction and subprocess chaining |
| `shell/security.py` | Auth system, role checks, file permission enforcement |
| `data/users.json` | Hashed credentials and roles |
| `data/permissions.json` | Per-file permission entries |
| `main.py` | Full integration: auth → REPL → security checks → dispatch |

## Piping to Demonstrate
```
ls | grep txt
cat log.txt | grep error | sort
cat file.txt | grep warning | sort | uniq
```

## Security to Demonstrate
```
# Login as admin
whoami                    # admin
useradd testuser          # create a new user

# Login as testuser (standard user)
whoami                    # testuser / user
cat /system/config.txt    # Permission denied
cat ~/myfile.txt          # Allowed
chmod myfile.txt rwx      # Permission denied (not admin)
```

## Integration Check
- [ ] Scheduling commands work inside the full shell
- [ ] Memory commands work inside the full shell
- [ ] Sync demos work inside the full shell
- [ ] Piping works alongside job control and security checks
- [ ] No regressions from Deliverables 1–3

## Notes
<!-- Add implementation notes here as you work -->
