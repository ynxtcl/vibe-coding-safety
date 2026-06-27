#!/usr/bin/env python3
"""safety_init.py — Project init + Session manager"""
import json, subprocess, sys
from datetime import datetime
from pathlib import Path

def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [WARN] exit={r.returncode}: {r.stderr.strip()[:100]}")
    return r

def _check_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True); return True
    except FileNotFoundError:
        return False

def _install_hooks(root):
    hd = root / ".git" / "hooks"
    hd.mkdir(parents=True, exist_ok=True)
    c = ("#!/bin/sh\n# Vibe Safe: pre-commit\n"
         'echo "[vibe-safe] Pre-commit..."\n'
         'FILES=$(git diff --cached --name-only --diff-filter=ACMR | grep "\\.py$")\n'
         'if [ -n "$FILES" ]; then\n'
         '    echo "$FILES" | while read -r f; do\n'
         '        if [ -f "$f" ]; then\n'
         '            python -m py_compile "$f" 2>/dev/null\n'
         "            if [ $? -ne 0 ]; then\n"
         '                echo "  FAIL: $f syntax error"\n'
         '                python -m py_compile "$f"\n'
         "                exit 1\n"
         "            fi\n" "        fi\n" "    done\n"
         '    echo "  OK: Python syntax"\n' "fi\n")
    (hd / "pre-commit").write_text(c, encoding="utf-8")
    (hd / "pre-commit").chmod(0o755)
    print("  [OK] pre-commit hook")

def run_init(project_root, remote=None):
    print("=" * 60)
    print("  Vibe Safe Protocol - Project Init")
    print("=" * 60)
    if not _check_git():
        print("  FAIL: Git not found"); sys.exit(1)
    print("  [OK] Git")
    vd = project_root / ".vibe-safe"
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "baseline.json").write_text('{"created":"' + datetime.now().isoformat() + '"}\n', encoding="utf-8")
    (vd / "session.log").write_text("# Session Log\n# " + datetime.now().isoformat() + "\n\n", encoding="utf-8")
    (vd / "checkpoints.json").write_text('{"checkpoints":[]}\n', encoding="utf-8")
    print("  [OK] .vibe-safe")
    cfg = project_root / ".vibe-safe-config"
    if not cfg.exists():
        cfg.write_text("# Config\nROOT=" + str(project_root) + "\n", encoding="utf-8")
    print("  [OK] config")
    if not (project_root / ".git").exists():
        _run(["git", "init"], project_root)
        gi = project_root / ".gitignore"
        if not gi.exists():
            gi.write_text("__pycache__/\n*.pyc\n.vscode/\n.idea/\n*.parquet\n*.csv\n.pytest_cache/\n.vibe-safe/\n", encoding="utf-8")
        print("  [OK] git init")
    else:
        print("  [OK] already git repo")
    _run(["git", "checkout", "main"], project_root)
    s = _run(["git", "status", "--porcelain"], project_root)
    if s.stdout.strip():
        _run(["git", "add", "-A"], project_root)
        _run(["git", "commit", "-m", "chore: initial commit (vibe-safe)"], project_root)
        print("  [OK] first commit")
    tag = "baseline/" + datetime.now().strftime("%Y%m%d_%H%M%S")
    if _run(["git", "tag", tag], project_root).returncode == 0:
        print("  [OK] baseline: " + tag)
    _install_hooks(project_root)
    if remote:
        _run(["git", "remote", "add", "origin", remote], project_root)
        _run(["git", "push", "-u", "origin", "main"], project_root)
        _run(["git", "push", "--tags"], project_root)
    print("=" * 60)
    print("  [DONE] Init complete!")
    print("=" * 60)

class SessionManager:
    def __init__(self, project_root):
        self.root = project_root
        self.vd = project_root / ".vibe-safe"
        self.log = self.vd / "session.log"
        self.sf = self.vd / "current_session.json"
    def start(self, desc):
        ts = datetime.now().isoformat()
        bn = "dev/vibe-" + datetime.now().strftime("%Y%m%d_%H%M")
        print("\nSession: " + desc + " @ " + bn)
        _run(["git", "checkout", "main"], self.root)
        if _run(["git", "checkout", "-b", bn], self.root).returncode != 0:
            print("  FAIL: branch"); return
        from safety_checkpoint import CheckpointManager
        CheckpointManager(self.root).create("before: " + desc)
        import json
        self.sf.write_text(json.dumps({"ts": ts, "desc": desc, "branch": bn, "status": "active"}), encoding="utf-8")
        with open(self.log, "a", encoding="utf-8") as f:
            f.write("START [" + ts + "] " + desc + " @ " + bn + "\n")
        print("  [OK] session started")
    def commit(self, msg):
        ts = datetime.now().isoformat()
        print("\nCommit: " + msg)
        s = _run(["git", "status", "--porcelain"], self.root)
        if not s.stdout.strip():
            print("  nothing to commit"); return
        _run(["git", "add", "-A"], self.root)
        if _run(["git", "commit", "-m", msg], self.root).returncode == 0:
            with open(self.log, "a", encoding="utf-8") as f:
                f.write("  COMMIT [" + ts + "] " + msg + "\n")
            print("  [OK]")
    def end(self):
        if not self.sf.exists():
            print("  no active session"); return
        import json
        s = json.loads(self.sf.read_text(encoding="utf-8"))
        ts = datetime.now().isoformat()
        print("\nEnd: " + s["desc"])
        self.commit("session-end")
        from safety_checkpoint import CheckpointManager
        CheckpointManager(self.root).create("after: " + s["desc"])
        from safety_verify import run_verify
        ok = run_verify(self.root)
        s["status"] = "ok" if ok else "fail"
        s["ended"] = ts
        self.sf.write_text(json.dumps(s, indent=2), encoding="utf-8")
        with open(self.log, "a", encoding="utf-8") as f:
            f.write("END [" + ts + "] " + s["desc"] + " -> " + ("PASS" if ok else "FAIL") + "\n")
        if ok:
            print("\n  [OK] passed! Merge: --no-ff " + s["branch"])
        else:
            print("\n  [FAIL] run: vibe-safe recover")
        return ok
    def status(self):
        print("\nStatus\n" + "-" * 40)
        _run(["git", "branch", "--show-current"], self.root)
        if self.sf.exists():
            import json
            s = json.loads(self.sf.read_text(encoding="utf-8"))
            print("  Session: " + s.get("desc", "?") + " [" + s.get("status", "?") + "]")
        else:
            print("  No active session")
