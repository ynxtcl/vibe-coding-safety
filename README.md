# Vibe Safe Protocol

> Safety checkpoint system for AI-assisted coding (Vibe Coding)

When AI helps you write code, how do you ensure the project doesn't crash and you can always rollback?

## Quick Start

```bash
git clone https://github.com/ynxtcl/vibe-coding-safety.git
cd your-project

# Initialize Vibe Safe
python /path/to/vibe-coding-safety/scripts/vibe_safe.py init

# Start a coding session
python scripts/vibe_safe.py session start "implement X"

# ... AI does its work ...

# Atomic commit
python scripts/vibe_safe.py session commit "added feature"

# End with verification
python scripts/vibe_safe.py session end

# If AI crashes
python scripts/vibe_safe.py recover
python scripts/vibe_safe.py recover --dry-run  # preview
```

## 16 Commands

| Command | Purpose | Safety Feature |
|---------|---------|----------------|
| `init` | Initialize project | Git + checkpoints + hooks |
| `session start` | Begin coding session | Branch + guardian + deps freeze |
| `session commit` | Atomic save | Pre-commit syntax check |
| `session end` | Verify + cleanup | Auto-test + guardian stop |
| `checkpoint create/list/diff` | Snapshot management | Git tags + metadata |
| `verify` | Run all checks | Syntax + pytest + diff baseline |
| `recover` | Rollback | 7-step + smoke test |
| `recover --dry-run` | Simulate recovery | Zero-risk preview |
| `guard start/stop/status` | Auto-daemon | 5min auto-checkpoint |
| `audit` | Integrity check | SHA256 manifest verify |
| `audit --init` | Create manifest | First hash snapshot |
| `freeze` | Deps snapshot | pip freeze save |
| `freeze --diff` | Deps comparison | Track dependency changes |
| `impact` | Change analysis | Module risk scoring |
| `gitignore-check` | Secret detection | Find committed secrets |
| `status/log` | Session info | Current state + history |

## Architecture

```
PREPARE -> SESSION -> VERIFY -> RECOVER
            |
         Guardian
         (every 5min
         auto-cp)
```

## License
MIT
