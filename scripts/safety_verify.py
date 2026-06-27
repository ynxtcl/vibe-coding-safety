#!/usr/bin/env python3
"""safety_verify.py — Verify: syntax check, tests, diff baseline"""
import json, subprocess, sys
from datetime import datetime
from pathlib import Path

def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def run_verify(project_root, baseline_tag=None):
    vd = project_root / ".vibe-safe"
    all_pass = True
    print("\n" + "=" * 60)
    print("  [CHECK] Vibe Safe - Verify")
    print("=" * 60)
    print("\n[1/3] Python syntax...")
    py_files = [f for f in project_root.rglob("*.py") if ".vibe-safe" not in str(f) and ".git" not in str(f) and "__pycache__" not in str(f)]
    errors = []
    for f in py_files:
        r = _run([sys.executable, "-m", "py_compile", str(f)], project_root)
        if r.returncode != 0:
            errors.append(str(f))
            print("  FAIL: " + f.name + " - " + r.stderr.strip()[:100])
    if errors:
        print("  FAIL: " + str(len(errors)) + " files")
        all_pass = False
    else:
        print("  OK: " + str(len(py_files)) + " files")
    print("\n[2/3] Tests...")
    tr = _run([sys.executable, "-m", "pytest", "-v", "--tb=short"], project_root)
    print(tr.stdout[:2000])
    if tr.returncode == 0:
        print("  OK: all tests passed")
    else:
        print("  FAIL: tests (exit=" + str(tr.returncode) + ")")
        all_pass = False
    print("\n[3/3] Diff baseline...")
    if not baseline_tag:
        r = _run(["git", "tag", "-l", "checkpoint/*"], project_root)
        tags = [t for t in r.stdout.strip().split("\n") if t.strip()]
        if tags:
            baseline_tag = tags[-1]
        else:
            r = _run(["git", "tag", "-l", "baseline/*"], project_root)
            tags = [t for t in r.stdout.strip().split("\n") if t.strip()]
            if tags:
                baseline_tag = tags[-1]
    if baseline_tag:
        print("  vs: " + baseline_tag)
        dr = _run(["git", "diff", "--stat", baseline_tag, "HEAD"], project_root)
        if dr.stdout:
            print(dr.stdout)
        else:
            print("  no changes")
    else:
        print("  no baseline")
    (vd / "last_verify.json").write_text(json.dumps({"ts": datetime.now().isoformat(), "pass": all_pass, "syntax_errors": len(errors), "test_exit": tr.returncode, "baseline": baseline_tag}), encoding="utf-8")
    print("\n" + "=" * 60)
    if all_pass:
        print("  RESULT: PASS")
    else:
        print("  RESULT: FAIL - run 'vibe-safe recover'")
    print("=" * 60)
    return all_pass
