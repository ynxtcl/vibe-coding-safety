#!/usr/bin/env python3
"""
demo_recover.py — 崩溃恢复演示
"""
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path("C:/Users/Administrator/Desktop/quantitative_trading").resolve()
SCRIPTS_DIR = SCRIPT_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def print_step(num: int, msg: str):
    print(f"\n{'='*60}")
    print(f"  STEP {num}: {msg}")
    print(f"{'='*60}")


def run(cmd: list, cwd: Path = PROJECT_DIR) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


def main():
    print("=" * 60)
    print("  Vibe Safe Protocol - Demo")
    print("=" * 60)
    print_step(1, "Check environment")
    git_ver = run(["git", "--version"], Path.cwd())
    print(f"  Git: {git_ver.stdout.strip()}")
    py_ver = run([sys.executable, "--version"], Path.cwd())
    print(f"  Python: {py_ver.stdout.strip()}")
    print("  OK: environment ready")
    print_step(2, "Init Vibe Safe")
    from safety_init import run_init
    vibe_dir = PROJECT_DIR / ".vibe-safe"
    if vibe_dir.exists():
        print("  .vibe-safe exists, skip")
    else:
        run_init(PROJECT_DIR, remote=None)
    print("  OK: init complete")
    print_step(3, "Create baseline checkpoint")
    from safety_checkpoint import CheckpointManager
    cm = CheckpointManager(PROJECT_DIR)
    baseline = cm.create("demo: baseline")
    cm.list_all()
    print("  OK: baseline")
    print_step(4, "Simulate coding session")
    from safety_init import SessionManager
    sm = SessionManager(PROJECT_DIR)
    sm.start("demo: add log")
    test_file = PROJECT_DIR / "demo_test_feature.py"
    test_file.write_text("# demo feature\ndef demo_hello():\n    return 'Hello from Vibe Safe Demo'\n", encoding="utf-8")
    print("  created demo_test_feature.py")
    sm.commit("feat: add hello function")
    cm.create("demo: after good changes")
    print("  OK: good changes")
    print_step(5, "Simulate AI crash")
    crash_file = PROJECT_DIR / "demo_crash_file.py"
    crash_file.write_text("import nonexistent_module\n\ndef this_will_crash(\n    return None\n", encoding="utf-8")
    print("  created crash file")
    if test_file.exists():
        test_file.write_text(test_file.read_text(encoding="utf-8") + "\ndef broken_function(:\n    return\n", encoding="utf-8")
        print("  injected syntax error")
    sm.commit("wip: AI changes WITH ERRORS")
    print("  AI crash! System corrupted")
    print_step(6, "Verify fails (expected)")
    from safety_verify import run_verify
    result = run_verify(PROJECT_DIR)
    if not result:
        print("  OK: expected failure")
    print_step(7, "Execute recovery")
    sm.status()
    cm.list_all()
    print("  Recovering...")
    from safety_recover import run_recover
    run_recover(PROJECT_DIR)
    print("  OK: recovery done")
    print_step(8, "Verify recovery")
    recovery_check = run_verify(PROJECT_DIR)
    if recovery_check:
        print("  OK: recovery successful!")
    else:
        print("  WARN: recovery issues, check report")
    print_step(9, "Cleanup")
    if crash_file.exists():
        crash_file.unlink()
        print(f"  removed {crash_file.name}")
    if test_file.exists():
        test_file.unlink()
        print(f"  removed {test_file.name}")
    run(["git", "checkout", "main"], PROJECT_DIR)
    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
