#!/usr/bin/env python3
"""safety_recover.py — Recovery: dry-run, rollback, post-recovery smoke test"""
import json, subprocess, sys
from datetime import datetime
from pathlib import Path

def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr: print("  [WARN] " + r.stderr.strip()[:200])
    return r
def _branch(root):
    r = _run(["git", "branch", "--show-current"], root)
    return r.stdout.strip() or "(detached)"
def _uncommitted(root):
    r = _run(["git", "status", "--porcelain"], root)
    return [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
def _target(root, tag):
    if tag: return tag
    for p in ["checkpoint", "baseline"]:
        r = _run(["git", "tag", "-l", p + "/*"], root)
        ts = [t for t in r.stdout.strip().split("\n") if t.strip()]
        if ts: return ts[-1]
    return None
def _smoke(root):
    print("\n  [SMOKE] Quick check...")
    pf = [f for f in root.rglob("*.py") if ".vibe-safe" not in str(f) and ".git" not in str(f)]
    errs = 0
    for f in pf[:20]:
        r = _run([sys.executable, "-m", "py_compile", str(f)], root)
        if r.returncode != 0: print("    FAIL: " + f.name); errs += 1
    if errs == 0: print("    OK: syntax " + str(min(20, len(pf))) + " files")
    else: print("    FAIL: " + str(errs) + " errors")
    tr = _run([sys.executable, "-m", "pytest", "--co", "-q"], root)
    print("    " + ("OK: pytest" if tr.returncode in (0,5) else "WARN: pytest"))
    return errs == 0

def run_recover(project_root, tag=None, dry_run=False):
    print("\n" + "=" * 60)
    print("  [RECOVER]" + (" [DRY RUN]" if dry_run else ""))
    print("=" * 60)
    print("\n[1/7] State: branch=" + _branch(project_root) + " uncommitted=" + str(len(_uncommitted(project_root))))
    uf = _uncommitted(project_root)
    if uf and not dry_run: _run(["git", "stash", "push", "-m", "stash-" + datetime.now().strftime("%H%M%S")], project_root)
    print("\n[2/7] Target...")
    t = _target(project_root, tag)
    if not t: print("  FAIL: no tag"); sys.exit(1)
    print("  " + t)
    print("\n[3/7] Diff...")
    dr = _run(["git", "diff", "--stat", t, "HEAD"], project_root)
    if dr.stdout: print(dr.stdout + "  " + str(len([l for l in dr.stdout.split("\n") if "|" in l])) + " files")
    else: print("  (none)")
    print("\n[4/7] Branch...")
    rb = "recovery/" + datetime.now().strftime("%Y%m%d_%H%M%S")
    if not dry_run: _run(["git", "branch", rb, t], project_root); print("  " + rb)
    print("\n[5/7] main...")
    if not dry_run: _run(["git", "checkout", "main"], project_root)
    print("\n[6/7] Merge...")
    if not dry_run:
        mr = _run(["git", "merge", "--ff-only", t], project_root)
        if mr.returncode != 0: _run(["git", "reset", "--hard", t], project_root)
        print("  merged " + t)
    print("\n[7/7] Report...")
    if not dry_run:
        ok = _smoke(project_root)
        r2 = _run(["git", "diff", "--name-only", t, "HEAD"], project_root)
        changed = r2.stdout.strip() or "(none)"
        r3 = _run(["git", "rev-list", "--count", t + "..HEAD", "--"], project_root)
        lost = r3.stdout.strip() or "0"
        rp = project_root / ".vibe-safe" / ("recovery_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".md")
        report = "# Recovery Report\nTime: " + datetime.now().isoformat() + "\nTarget: " + t + "\nLost: " + lost + "\nSmoke: " + ("PASS" if ok else "FAIL") + "\n## Files\n" + changed + "\n---\n"
        rp.write_text(report, encoding="utf-8")
        print("  report: " + str(rp))
        print("\n" + "=" * 60)
        print("  [DONE]" + (" Smoke: PASS" if ok else " Smoke: FAIL"))
    else:
        r2 = _run(["git", "diff", "--name-only", t, "HEAD"], project_root)
        for f in r2.stdout.strip().split("\n")[:10]:
            if f.strip(): print("    revert: " + f.strip())
        print("\n" + "=" * 60)
        print("  [DRY RUN] No changes made")
    print("=" * 60)

if __name__ == "__main__":
    r = Path.cwd(); tag = None; dry = "--dry-run" in sys.argv
    if "--tag" in sys.argv:
        i = sys.argv.index("--tag")
        if i + 1 < len(sys.argv): tag = sys.argv[i + 1]
    run_recover(r, tag, dry)
