#!/usr/bin/env python3
"""safety_guard.py — Guardian daemon for auto-checkpoint"""
import json, os, signal, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path
GUARD_FILE = "guardian.json"
def _run(c, w): return subprocess.run(c, cwd=w, capture_output=True, text=True)
def _git(c, w): return _run(["git"]+c, w)

class GS:
    def __init__(self, r): self.p = Path(r) / ".vibe-safe" / GUARD_FILE
    def read(self):
        if self.p.exists(): return json.loads(self.p.read_text(encoding="utf-8"))
        return {"running": False, "pid": None}
    def write(self, d): self.p.write_text(json.dumps(d), encoding="utf-8")
    def is_running(self):
        d = self.read()
        if d.get("running") and d.get("pid"):
            if sys.platform == "win32":
                c = subprocess.run(["tasklist","/FI","PID eq "+str(d["pid"])], capture_output=True, text=True)
                return str(d["pid"]) in c.stdout
            else:
                try: os.kill(d["pid"], 0); return True
                except: return False
        return False

class Guardian:
    def __init__(self, r, iv=5, desc="auto"):
        self.r = Path(r); self.vd = self.r / ".vibe-safe"
        self.iv = iv; self.desc = desc; self._s = threading.Event(); self._t = None
    def _cp(self):
        s = _git(["status","--porcelain"], self.r)
        if not s.stdout.strip(): return
        tag = "auto/"+datetime.now().strftime("%Y%m%d_%H%M%S")
        _git(["add","-A"], self.r); _git(["commit","-m","auto: "+self.desc], self.r)
        _git(["tag","-a",tag,"-m","auto"], self.r)
        with open(self.vd/"session.log","a",encoding="utf-8") as f:
            f.write("  AUTO-CP ["+datetime.now().isoformat()+"] "+tag+"\n")
        print("  [GUARD] auto-cp: "+tag)
    def _loop(self):
        with open(self.vd/"session.log","a",encoding="utf-8") as f:
            f.write("  GUARD iv="+str(self.iv)+"min\n")
        while not self._s.is_set():
            for _ in range(self.iv*6):
                if self._s.is_set():
                    with open(self.vd/"session.log","a",encoding="utf-8") as f: f.write("  GUARD STOP\n")
                    return
                time.sleep(10)
            try: self._cp()
            except Exception as e: print("  [GUARD] err: "+str(e))
    def start(self):
        if self._t and self._t.is_alive(): print("  [GUARD] running"); return
        self._s.clear(); self._t = threading.Thread(target=self._loop, daemon=True); self._t.start()
        GS(self.r).write({"running":True,"pid":os.getpid(),"iv":self.iv,"desc":self.desc})
        print("  [GUARD] started (every "+str(self.iv)+"min, pid="+str(os.getpid())+")")
    def stop(self):
        if self._t and self._t.is_alive(): self._s.set(); self._t.join(timeout=30)
        GS(self.r).write({"running":False,"pid":None}); print("  [GUARD] stopped")

def cmd_start(r, iv=5, desc="auto"):
    g = Guardian(r, iv, desc); g.start()
    print("  [GUARD] background. Stop: guard stop")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: g.stop()
def cmd_stop(r):
    gs = GS(r); st = gs.read()
    if st.get("pid"):
        try:
            if sys.platform == "win32": subprocess.run(["taskkill","/F","/PID",str(st["pid"])], capture_output=True)
            else: os.kill(st["pid"], signal.SIGTERM)
        except: pass
    gs.write({"running":False,"pid":None}); print("  [GUARD] stopped")
def cmd_status(r):
    gs = GS(r); st = gs.read()
    print("\n[Guardian]\n  Running: "+str(gs.is_running())+"\n  PID: "+str(st.get("pid","N/A")))
