#!/usr/bin/env python3
"""safety_audit.py — File integrity + dependency freeze + change impact + gitignore"""
import hashlib, json, subprocess, sys
from datetime import datetime
from pathlib import Path

def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
def _git(args, root):
    return _run(["git"] + args, root)
def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def create_manifest(project_root, tag):
    vd = project_root / ".vibe-safe"
    vd.mkdir(parents=True, exist_ok=True)
    exclude = {".git", ".vibe-safe", "__pycache__", ".pytest_cache"}
    manifest = {}
    for f in project_root.rglob("*"):
        if f.is_file() and not any(p in str(f) for p in exclude):
            rel = str(f.relative_to(project_root))
            try:
                manifest[rel] = hash_file(f)
            except:
                manifest[rel] = "ERROR"
    data = {"tag": tag, "ts": datetime.now().isoformat(), "count": len(manifest), "files": manifest}
    (vd / "manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("  [AUDIT] manifest: " + str(len(manifest)) + " files")
    return manifest

def verify_manifest(project_root, tag=None):
    vd = project_root / ".vibe-safe"
    mp = vd / "manifest.json"
    if not mp.exists():
        print("  [AUDIT] no manifest. Run: audit --init"); return False
    stored = json.loads(mp.read_text(encoding="utf-8"))
    sf = stored.get("files", {})
    print("\n[Integrity] vs " + stored.get("tag", "?"))
    exclude = {".git", ".vibe-safe", "__pycache__", ".pytest_cache"}
    current = {}
    for f in project_root.rglob("*"):
        if f.is_file() and not any(p in str(f) for p in exclude):
            rel = str(f.relative_to(project_root))
            try:
                current[rel] = hash_file(f)
            except:
                pass
    changed = [r for r, h in sf.items() if r in current and current[r] != h]
    missing = [r for r in sf if r not in current]
    added = [r for r in current if r not in sf]
    match = len(sf) - len(changed) - len(missing)
    print("  match:" + str(match) + " changed:" + str(len(changed)) + " added:" + str(len(added)) + " missing:" + str(len(missing)))
    if changed:
        print("\n  CHANGED:"); [print("    " + f) for f in changed[:15]]
    clean = len(changed) == 0 and len(missing) == 0
    (vd / "last_audit.json").write_text(json.dumps({"ts": datetime.now().isoformat(), "clean": clean, "match": match, "changed": len(changed), "added": len(added)}), encoding="utf-8")
    if clean:
        print("  [AUDIT] INTEGRITY OK")
    else:
        print("  [AUDIT] INTEGRITY FAIL")
    return clean

def freeze_deps(project_root, label=""):
    vd = project_root / ".vibe-safe"
    vd.mkdir(parents=True, exist_ok=True)
    r = _run([sys.executable, "-m", "pip", "freeze"], project_root)
    deps = r.stdout.strip()
    ts = datetime.now().isoformat()
    data = {"ts": ts, "label": label, "count": len([l for l in deps.split("\n") if l and "==" in l]), "deps": deps}
    fp = vd / ("freeze_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (vd / "freeze_latest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("  [FREEZE] " + str(data["count"]) + " deps")
    return data

def compare_freeze(project_root):
    vd = project_root / ".vibe-safe"
    lp = vd / "freeze_latest.json"
    if not lp.exists():
        print("  [FREEZE] no snapshot. Run: vibe-safe freeze"); return
    stored = json.loads(lp.read_text(encoding="utf-8"))
    sd = set(l for l in stored["deps"].split("\n") if l and "==" in l)
    cur = _run([sys.executable, "-m", "pip", "freeze"], project_root).stdout.strip()
    cd = set(l for l in cur.split("\n") if l and "==" in l)
    added = cd - sd; removed = sd - cd
    print("\n[Deps Diff] stored:" + str(len(sd)) + " current:" + str(len(cd)) + " added:" + str(len(added)) + " removed:" + str(len(removed)))
    if added:
        print("  ADDED:"); [print("    + " + d) for d in sorted(added)[:15]]
    if removed:
        print("  REMOVED:"); [print("    - " + d) for d in sorted(removed)[:15]]
    return added, removed

def analyze_impact(project_root, tag1=None, tag2="HEAD"):
    if not tag1:
        r = _git(["tag", "-l", "checkpoint/*"], project_root)
        tags = [t for t in r.stdout.strip().split("\n") if t.strip()]
        if not tags:
            r = _git(["tag", "-l", "baseline/*"], project_root)
            tags = [t for t in r.stdout.strip().split("\n") if t.strip()]
        if tags:
            tag1 = tags[-1]
        else:
            print("  [IMPACT] no baseline"); return
    print("\n[Impact] " + tag1 + " vs " + tag2)
    dr = _git(["diff", "--stat", tag1, tag2], project_root)
    if not dr.stdout:
        print("  No changes"); return
    lines = dr.stdout.strip().split("\n")
    files = []
    for line in lines:
        if "|" in line:
            p = line.rsplit("|", 1)
            fname = p[0].strip()
            chg = p[1].strip().split(",")
            changes = sum(int(c.split()[0]) for c in chg if c.strip().split()[0].isdigit())
            files.append({"file": fname, "changes": changes})
    modules = {}
    for f in files:
        parts = f["file"].replace("\\", "/").split("/")
        mod = parts[0] if len(parts) > 1 else "(root)"
        if mod not in modules:
            modules[mod] = {"files": 0, "changes": 0}
        modules[mod]["files"] += 1
        modules[mod]["changes"] += f["changes"]
    risk = 0
    print("\n  Modules:")
    for mod, info in sorted(modules.items(), key=lambda x: -x[1]["changes"]):
        lvl = "LOW"
        if info["changes"] > 50: lvl = "HIGH"; risk += 2
        elif info["changes"] > 20: lvl = "MEDIUM"; risk += 1
        print("    " + mod.ljust(20) + " files:" + str(info["files"]).rjust(3) + " changes:" + str(info["changes"]).rjust(5) + " risk:" + lvl)
    print("\n  Risk Score: " + str(risk) + "/" + str(len(modules)*2))
    print("  " + ("LOW - safe" if risk == 0 else "MEDIUM - review" if risk <= 3 else "HIGH - full review"))
    vd = project_root / ".vibe-safe"
    (vd / "last_impact.json").write_text(json.dumps({"ts": datetime.now().isoformat(), "baseline": tag1, "files": len(files), "changes": sum(f["changes"] for f in files), "risk": risk, "modules": {k: v for k, v in modules.items()}}, indent=2), encoding="utf-8")

def check_gitignore(project_root):
    patterns = ["*.key", "*.pem", ".env*", "*cred*", "*secret*", "*password*", "*token*", "*auth*", ".netrc"]
    print("\n[Gitignore Check]")
    gi = project_root / ".gitignore"
    if not gi.exists():
        print("  WARN: no .gitignore"); return
    content = gi.read_text(encoding="utf-8").lower()
    missing = [p for p in patterns if p.replace("*", "").lower() not in content]
    if missing:
        print("  WARN: missing patterns:"); [print("    " + p) for p in missing]
    else:
        print("  OK: patterns covered")
    r = _git(["ls-files"], project_root)
    tracked = r.stdout.strip().split("\n")
    suspicious = [f for f in tracked if any(kw in f.lower() for kw in ["key", "secret", "cred", "password", "token", ".env"])]
    if suspicious:
        print("  WARN: tracked files may contain secrets:"); [print("    " + f) for f in suspicious[:10]]
    else:
        print("  OK: no secrets tracked")
