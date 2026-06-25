"""
Dashboard API — FastAPI backend for Web Dashboard.
Run: uvicorn interfaces.dashboard.api:app --port 8080
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

app = FastAPI(
    title       = "CoBWeaverClaw Dashboard",
    description = "Control panel for CoBWeaverClaw AI Agent",
    version     = "0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

def verify_token(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    from auth.tokens import TokenManager
    tm      = TokenManager()
    payload = tm.verify(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            return f.read()
    return HTMLResponse("<h1>CoBWeaverClaw Dashboard</h1>")

@app.get("/api/status")
async def get_status(payload: dict = Depends(verify_token)):
    from core.platform import PlatformAdapter
    p = PlatformAdapter()
    return {
        "agent":     "running",
        "platform":  p.platform,
        "heartbeat": p.get_heartbeat_interval(),
        "memory":    p.get_memory_limit(),
        "version":   "0.1.0"
    }

@app.get("/api/devices")
async def get_devices(payload: dict = Depends(verify_token)):
    """قائمة كل الأجهزة المسجّلة."""
    from core.devices import DeviceRegistry
    dr = DeviceRegistry()
    return {
        "devices": dr.list_devices(),
        "current": dr.get_current_device()
    }

@app.delete("/api/devices/{device_id}")
async def revoke_device(device_id: str, payload: dict = Depends(verify_token)):
    """إلغاء جهاز معيّن."""
    from core.devices import DeviceRegistry
    dr = DeviceRegistry()
    ok = dr.revoke_device(device_id)
    return {"success": ok, "device_id": device_id}

@app.get("/api/updates")
async def get_updates(payload: dict = Depends(verify_token)):
    """حالة التحديثات وسجل الإشعارات."""
    from core.updater import Updater, CURRENT_VERSION
    u = Updater()
    latest  = u.get_latest_version()
    commit  = u.get_latest_commit()
    history = u.get_update_history()
    return {
        "current_version":  CURRENT_VERSION,
        "latest_version":   latest["version"] if latest else None,
        "latest_commit":    commit["sha"] if commit else None,
        "commit_message":   commit["message"] if commit else None,
        "update_available": latest and u._version_gt(latest["version"], CURRENT_VERSION),
        "history":          history[:10],
    }

@app.post("/api/updates/check")
async def check_updates(payload: dict = Depends(verify_token)):
    """فحص التحديثات يدوياً."""
    from core.updater import Updater
    u      = Updater()
    latest = u.get_latest_version()
    commit = u.get_latest_commit()
    return {
        "latest":  latest,
        "commit":  commit,
        "checked": True
    }

@app.get("/api/memory")
async def get_memory(payload: dict = Depends(verify_token)):
    import sqlite3
    db_path = os.path.expanduser("~/.cobweaverclaw/memory.db")
    if not os.path.exists(db_path):
        return {"facts": 0, "history": 0, "size_kb": 0}
    conn    = sqlite3.connect(db_path)
    facts   = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    history = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    conn.close()
    return {"facts": facts, "history": history, "size_kb": os.path.getsize(db_path)//1024}

@app.get("/api/skills")
async def get_skills(payload: dict = Depends(verify_token)):
    import glob
    skills = [{"name": os.path.basename(f)[:-3], "status": "active"}
              for f in glob.glob("skills/*.py")
              if not os.path.basename(f).startswith("_")]
    return {"skills": skills, "count": len(skills)}

@app.get("/api/models")
async def get_models(payload: dict = Depends(verify_token)):
    import yaml
    try:
        with open("config.yaml") as f:
            cfg = yaml.safe_load(f)
        brain = cfg.get("brain", {})
    except Exception:
        brain = {}
    return {
        "primary": brain.get("primary", "claude-sonnet-4-6"),
        "fast":    brain.get("fast",    "groq/llama-3.3-70b"),
        "local":   brain.get("local",   "ollama/mistral"),
        "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))
    }

@app.get("/api/logs")
async def get_logs(limit: int = 50, payload: dict = Depends(verify_token)):
    import sqlite3
    db_path = os.path.expanduser("~/.cobweaverclaw/memory.db")
    if not os.path.exists(db_path):
        return {"logs": []}
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT user_id, message, response, created FROM history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return {"logs": [{"user":r[0],"message":r[1][:80],"response":r[2][:80],"time":r[3]} for r in rows]}

@app.post("/api/doctor")
async def run_doctor(fix: bool = False, payload: dict = Depends(verify_token)):
    import yaml
    try:
        with open("config.yaml") as f:
            cfg = yaml.safe_load(f)
    except Exception:
        cfg = {}
    from commands.doctor import Doctor
    doc = Doctor(cfg)
    return await doc.run(fix=fix)

@app.post("/api/learn")
async def trigger_learning(payload: dict = Depends(verify_token)):
    return {"status": "started", "message": "Self-learning cycle initiated"}

@app.get("/api/token/verify")
async def verify_token_endpoint(token: str):
    from auth.tokens import TokenManager
    tm     = TokenManager()
    result = tm.verify(token)
    if result:
        return {"valid": True, "user_id": result.get("user_id"), "type": result.get("type")}
    return {"valid": False}

@app.post("/api/token/create")
async def create_token(user_id: str):
    from auth.tokens import TokenManager
    tm    = TokenManager()
    token = tm.create_master_token(user_id)
    return {"token": token, "user_id": user_id, "type": "master"}
