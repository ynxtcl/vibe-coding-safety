#!/usr/bin/env python3
"""safety_checkpoint.py — Checkpoint management"""
import json, subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

class CheckpointManager:
    def __init__(self, project_root: Path):
        self.root = project_root
        self.vd = project_root / ".vibe-safe"
        self.db_path = self.vd / "checkpoints.json"
        self._ensure_db()
    def _ensure_db(self):
        self.vd.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self.db_path.write_text('{"checkpoints": []}\n', encoding="utf-8")
    def _load_db(self) -> dict:
        return json.loads(self.db_path.read_text(encoding="utf-8"))
    def _save_db(self, db: dict):
        self.db_path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
    def _git(self, args: list) -> subprocess.CompletedProcess:
        return subprocess.run(["git"] + args, cwd=self.root, capture_output=True, text=True)
    def create(self, description: str) -> Optional[str]:
        tag_name = f"checkpoint/{datetime.now():%Y%m%d_%H%M%S}"
        result = self._git(["tag", "-a", tag_name, "-m", description])
        if result.returncode != 0:
            print("  [FAIL] checkpoint: " + result.stderr.strip()[:100])
            return None
        db = self._load_db()
        entry = {"tag": tag_name, "timestamp": datetime.now().isoformat(), "description": description, "branch": self._git(["branch", "--show-current"]).stdout.strip()}
        db["checkpoints"].append(entry)
        self._save_db(db)
        print("  [OK] checkpoint: " + tag_name + " - " + description)
        return tag_name
    def list_all(self):
        db = self._load_db()
        cps = db.get("checkpoints", [])
        if not cps:
            print("\n[Checkpoints]: none"); return
        print("\n[Checkpoints] (" + str(len(cps)) + "):")
        print("  TAG / Time / Description")
        print("  " + "-" * 70)
        for cp in reversed(cps):
            print(f"  {cp.get('tag','?'):<40} {cp.get('timestamp','?'):<25} {cp.get('description','?')}")
    def diff(self, tag1, tag2):
        print("\n[Diff] " + tag1 + " vs " + tag2)
        r = self._git(["diff", "--stat", tag1, tag2])
        print(r.stdout if r.stdout else "  no changes")
        r2 = self._git(["diff", tag1, tag2])
        if r2.stdout:
            lines = r2.stdout.split("\n")
            a = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
            d = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
            print(f"\n  stats: +{a} / -{d}")
        else: print("  no code diff")
    def find_latest(self) -> Optional[str]:
        db = self._load_db()
        cps = db.get("checkpoints", [])
        return cps[-1]["tag"] if cps else None
    def get_baseline(self) -> Optional[str]:
        r = self._git(["tag", "-l", "baseline/*"])
        tags = [t.strip() for t in r.stdout.strip().split("\n") if t.strip()]
        return tags[-1] if tags else None
