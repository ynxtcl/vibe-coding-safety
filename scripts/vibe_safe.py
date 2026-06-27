#!/usr/bin/env python3
"""vibe_safe.py — Vibe Coding Safety Protocol CLI

Commands:
  init [--remote <url>]              Initialize project
  session start|commit|end [args]    Session lifecycle
  checkpoint create|list|diff        Checkpoint management
  verify [--baseline <tag>]          Run verification
  recover [--tag <tag>] [--dry-run]  Recovery (with dry-run)
  guard start|stop|status            Guardian auto-checkpoint daemon
  audit <tag>                        File integrity audit
  audit --init                       Create hash manifest
  freeze                             Dependency snapshot
  impact [tag1] [tag2]               Change impact analysis
  gitignore-check                    Secret file validation
  status                             Session status
  log                                Show session history
"""
import sys
from pathlib import Path

def find_project_root():
    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".vibe-safe-config").exists() or (parent / ".git").exists():
            return parent
    return cwd

PROJECT_ROOT = find_project_root()
SCRIPTS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPTS_DIR))

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "init":
        from safety_init import run_init
        remote = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[2] == "--remote" else None
        run_init(PROJECT_ROOT, remote)
    elif cmd == "checkpoint":
        if len(sys.argv) < 3: print("Usage: checkpoint <create|list|diff>"); sys.exit(1)
        from safety_checkpoint import CheckpointManager
        mgr = CheckpointManager(PROJECT_ROOT)
        sub = sys.argv[2]
        if sub == "create":
            mgr.create(sys.argv[3] if len(sys.argv) >= 4 else "checkpoint")
        elif sub == "list": mgr.list_all()
        elif sub == "diff":
            if len(sys.argv) < 5: print("Usage: checkpoint diff <tag1> <tag2>"); sys.exit(1)
            mgr.diff(sys.argv[3], sys.argv[4])
    elif cmd == "session":
        if len(sys.argv) < 3: print("Usage: session <start|commit|end>"); sys.exit(1)
        from safety_init import SessionManager
        sm = SessionManager(PROJECT_ROOT)
        sub = sys.argv[2]
        if sub == "start":
            desc = sys.argv[3] if len(sys.argv) >= 4 else "vibe session"
            sm.start(desc)
            try:
                from safety_guard import Guardian
                Guardian(PROJECT_ROOT, interval=5, session_desc=desc).start()
                from safety_audit import freeze_deps
                freeze_deps(PROJECT_ROOT, "session-start: " + desc)
            except Exception as e: print("  [WARN] extra: " + str(e))
        elif sub == "commit":
            sm.commit(sys.argv[3] if len(sys.argv) >= 4 else "wip")
        elif sub == "end":
            sm.end()
            try:
                from safety_guard import cmd_stop
                cmd_stop(PROJECT_ROOT)
                from safety_audit import freeze_deps
                freeze_deps(PROJECT_ROOT, "session-end")
            except Exception as e: print("  [WARN] cleanup: " + str(e))
    elif cmd == "verify":
        from safety_verify import run_verify
        baseline = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[2] == "--baseline" else None
        run_verify(PROJECT_ROOT, baseline)
    elif cmd == "recover":
        from safety_recover import run_recover
        tag = None; dry = "--dry-run" in sys.argv
        if "--tag" in sys.argv:
            idx = sys.argv.index("--tag")
            if idx + 1 < len(sys.argv): tag = sys.argv[idx + 1]
        run_recover(PROJECT_ROOT, tag, dry)
    elif cmd == "guard":
        if len(sys.argv) < 3: print("Usage: guard <start|stop|status>"); sys.exit(1)
        from safety_guard import cmd_start, cmd_stop, cmd_status
        sub = sys.argv[2]; interval = 5
        if sub == "start":
            if "--interval" in sys.argv:
                i = sys.argv.index("--interval")
                if i + 1 < len(sys.argv): interval = int(sys.argv[i + 1])
            cmd_start(PROJECT_ROOT, interval, "cli-guard")
        elif sub == "stop": cmd_stop(PROJECT_ROOT)
        elif sub == "status": cmd_status(PROJECT_ROOT)
    elif cmd == "audit":
        from safety_audit import create_manifest, verify_manifest
        if "--init" in sys.argv: create_manifest(PROJECT_ROOT, "manual-init")
        else: verify_manifest(PROJECT_ROOT, sys.argv[2] if len(sys.argv) >= 3 else None)
    elif cmd == "freeze":
        from safety_audit import freeze_deps, compare_freeze
        if "--diff" in sys.argv: compare_freeze(PROJECT_ROOT)
        else: freeze_deps(PROJECT_ROOT, sys.argv[2] if len(sys.argv) >= 3 else "manual")
    elif cmd == "impact":
        from safety_audit import analyze_impact
        analyze_impact(PROJECT_ROOT, sys.argv[2] if len(sys.argv) >= 3 else None,
                       sys.argv[3] if len(sys.argv) >= 4 else "HEAD")
    elif cmd == "gitignore-check":
        from safety_audit import check_gitignore
        check_gitignore(PROJECT_ROOT)
    elif cmd == "status":
        from safety_init import SessionManager
        SessionManager(PROJECT_ROOT).status()
        from safety_guard import cmd_status
        cmd_status(PROJECT_ROOT)
    elif cmd == "log":
        lp = PROJECT_ROOT / ".vibe-safe" / "session.log"
        if lp.exists(): print(lp.read_text(encoding="utf-8"))
        else: print("no session log")
    else:
        print("Unknown: " + cmd); print(__doc__); sys.exit(1)

if __name__ == "__main__":
    main()
