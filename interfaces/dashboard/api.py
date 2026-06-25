"""
Dashboard API — FastAPI backend for Web Dashboard.
Run: uvicorn interfaces.dashboard.api:app --port 8080
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import os
import sys

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

# ── Auth dependency ─────────────────────────────────────────
def verify_token(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    from auth.tokens import TokenManager
    tm      = TokenManager()
    payload = tm.verify(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# ── Routes ──────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard HTML."""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            return f.read()
    return HTMLResponse("<h1>CoBWeaverClaw Dashboard</h1><p>Loading...</p>")

@app.get("/api/status")
async def get_status(payload: dict = Depends(verify_token)):
    """Return current agent status."""
    from core.platform import PlatformAdapter
    p = PlatformAdapter()
    return {
        "agent":    "running",
        "platform": p.platform,
        "heartbeat": p.get_heartbeat_interval(),
        "memory":   p.get_memory_limit(),
        "version":  "0.1.0"
    }

@app.get("/api/memory")
async def get_memory(payload: dict = Depends(verify_token)):
    """Return memory statistics."""
    import sqlite3, os
    db_path = os.path.expanduser("~/.cobweaverclaw/memory.db")
    if not os.path.exists(db_path):
        return {"facts": 0, "history": 0, "size_kb": 0}
    conn = sqlite3.connect(db_path)
    facts   = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    history = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    conn.close()
    size_kb = os.path.getsize(db_path) // 1024
    return {"facts": facts, "history": history, "size_kb": size_kb}

@app.get("/api/skills")
async def get_skills(payload: dict = Depends(verify_token)):
    """Return list of installed skills."""
    import glob
    skills = []
    for f in glob.glob("skills/*.py"):
        name = os.path.basename(f)[:-3]
        if not name.startswith("_"):
            skills.append({"name": name, "status": "active"})
    return {"skills": skills, "count": len(skills)}

@app.get("/api/models")
async def get_models(payload: dict = Depends(verify_token)):
    """Return configured models and their status."""
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
    """Return recent activity logs."""
    import sqlite3, os
    db_path = os.path.expanduser("~/.cobweaverclaw/memory.db")
    if not os.path.exists(db_path):
        return {"logs": []}
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT user_id, message, response, created FROM history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return {"logs": [
        {"user": r[0], "message": r[1][:80], "response": r[2][:80], "time": r[3]}
        for r in rows
    ]}

@app.post("/api/doctor")
async def run_doctor(fix: bool = False, payload: dict = Depends(verify_token)):
    """Run diagnostic check."""
    import yaml
    try:
        with open("config.yaml") as f:
            cfg = yaml.safe_load(f)
    except Exception:
        cfg = {}
    from commands.doctor import Doctor
    doc    = Doctor(cfg)
    result = await doc.run(fix=fix)
    return result

@app.post("/api/learn")
async def trigger_learning(payload: dict = Depends(verify_token)):
    """Trigger self-learning cycle."""
    return {"status": "started", "message": "Self-learning cycle initiated (Phase 3)"}

@app.get("/api/token/verify")
async def verify(token: str):
    """Verify a token without requiring auth."""
    from auth.tokens import TokenManager
    tm      = TokenManager()
    result  = tm.verify(token)
    if result:
        return {"valid": True, "user_id": result.get("user_id"), "type": result.get("type")}
    return {"valid": False}

@app.post("/api/token/create")
async def create_token(user_id: str):
    """Create a new master token for a user."""
    from auth.tokens import TokenManager
    tm    = TokenManager()
    token = tm.create_master_token(user_id)
    return {"token": token, "user_id": user_id, "type": "master"}
