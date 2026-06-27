# Vibe Coding Safety Guide

## Golden Rule: Checkpoint First, Code Later

```
Before AI coding: checkpoint + test baseline
After AI coding: verify + compare baseline
AI crash: recover to latest checkpoint
```

## Standard Workflow

```bash
# 1. Init (once)
vibe-safe init

# 2. Start session
vibe-safe session start "implement X"
# -> creates dev/vibe-* branch + checkpoint + guardian + deps snapshot

# 3. AI coding... (guardian auto-checkpoints every 5min)
vibe-safe session commit "progress"

# 4. End session
vibe-safe session end
# -> final checkpoint + verify + guardian stop + deps snapshot

# 5. Merge
vibe-safe recover  # if something went wrong
vibe-safe recover --dry-run  # preview before executing
```

## Crash Recovery

```bash
vibe-safe recover              # auto-rollback to latest checkpoint
vibe-safe recover --tag TAG    # rollback to specific checkpoint
vibe-safe recover --dry-run    # simulate without changes
```

## Enhanced Safety

```bash
vibe-safe guard start --interval 5   # auto-checkpoint every 5min
vibe-safe audit --init                # create SHA256 manifest
vibe-safe audit                       # verify file integrity
vibe-safe freeze                      # snapshot dependencies
vibe-safe freeze --diff               # compare deps
vibe-safe impact                      # change impact analysis
vive-safe gitignore-check             # detect committed secrets
```

## Enhanced Safety Features

| Feature | Command | What it prevents |
|---------|---------|-----------------|
| Auto-checkpoint | `guard start` | AI forgetting to save |
| Crash detection | `guard` (auto) | Process crash data loss |
| File integrity | `audit` | Undetected file changes |
| Dependency tracking | `freeze` | Untracked dependency changes |
| Dry-run recovery | `recover --dry-run` | Irreversible recovery |
| Post-recovery smoke test | `recover` (auto) | Residual issues after recovery |
| Change impact | `impact` | Unknown module effects |
| Secret detection | `gitignore-check` | Committed secrets |

---

Full CLI: `vibe-safe --help`
