"""
SimCore — اتصال المنصات والمواقع + تخزينها.

المنصات (منصات تداول/تواصل عبر مفتاح+سكريت): connect يجري اتصالاً مصادَقاً
حقيقياً (توقيع HMAC) ويعيد نتيجة فعلية (أرصدة Binance مثلاً).
المواقع (ويب): connect يفحص الوصول وهل يحتاج auth.
التخزين ملفات JSON في ~/.cobweaverclaw/simcore/ (بلا حفظ الأسرار).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

import requests

_DIR = Path.home() / ".cobweaverclaw" / "simcore"
PLATFORMS_FILE = _DIR / "platforms.json"
WEBSITES_FILE = _DIR / "websites.json"

_EXCHANGES = ("binance", "bybit", "kraken", "coinbase", "kucoin", "okx")


# ── تخزين ─────────────────────────────────────────────────────
def _load(path: Path) -> List[Dict[str, Any]]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8")) or []
    except Exception:
        pass
    return []


def _save(path: Path, rows: List[Dict[str, Any]]) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def _detect_exchange(base_url: str) -> str:
    u = (base_url or "").lower()
    for ex in _EXCHANGES:
        if ex in u:
            return ex
    return ""


# ── اتصال منصة (مصادَق) ───────────────────────────────────────
def _binance_balances(base_url: str, api_key: str, secret: str) -> Dict[str, Any]:
    """طلب موقّع لـ Binance /api/v3/account — يعيد الأرصدة غير الصفرية."""
    base = base_url.rstrip("/")
    if "/api/v3/account" not in base:
        base = base + "/api/v3/account"
    ts = str(int(time.time() * 1000))
    qs = urllib.parse.urlencode({"timestamp": ts, "recvWindow": "5000"})
    sig = hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f"{base}?{qs}&signature={sig}"
    r = requests.get(url, headers={"X-MBX-APIKEY": api_key,
                                   "User-Agent": "SimCore/1.0"}, timeout=12)
    if r.status_code == 200:
        data = r.json()
        balances = [b for b in data.get("balances", [])
                    if float(b.get("free", 0)) > 0 or float(b.get("locked", 0)) > 0]
        return {"success": True, "platform": "binance",
                "balances": [{"asset": b["asset"], "free": b["free"],
                              "locked": b.get("locked", "0")} for b in balances[:50]],
                "account_type": data.get("accountType", ""),
                "can_trade": data.get("canTrade")}
    try:
        detail = r.json().get("msg") or r.text[:200]
    except Exception:
        detail = r.text[:200]
    return {"success": False, "platform": "binance", "status": r.status_code,
            "error": f"Binance رفض: {detail}"}


def connect_platform(name: str = "", base_url: str = "", api_key: str = "",
                     secret_key: str = "", passphrase: str = "",
                     **_extra) -> Dict[str, Any]:
    """يتصل بالمنصة بمصادقة حقيقية ويعيد نتيجة فعلية."""
    base_url = (base_url or "").strip()
    if not base_url:
        return {"success": False, "error": "base_url مطلوب"}
    ex = _detect_exchange(base_url)
    try:
        if ex == "binance":
            res = _binance_balances(base_url, api_key, secret_key)
        else:
            # منصات أخرى: طلب موقّع عام (قد يتطلب مخطط توقيع خاص بالمنصة)
            from .source_manager import SourceManager
            f = SourceManager.fetch(base_url, api_key=api_key, secret=secret_key)
            res = {"success": bool(f.get("success")),
                   "platform": ex or "api",
                   "status": f.get("status"),
                   "content": (f.get("content") or "")[:2000],
                   "error": f.get("error")}
            if ex in ("kucoin", "okx") and passphrase:
                res["passphrase_used"] = True
        if res.get("success"):
            _persist_platform(name, base_url, res.get("platform", ex or "api"))
        return res
    except Exception as e:
        return {"success": False, "platform": ex or "api", "error": str(e)[:160]}


def _persist_platform(name: str, base_url: str, platform_type: str) -> None:
    rows = _load(PLATFORMS_FILE)
    key = (name or base_url).strip()
    rows = [r for r in rows if r.get("name") != key]     # لا تكرار
    rows.append({"name": key, "base_url": base_url,
                 "platform_type": platform_type, "added_at": int(time.time())})
    _save(PLATFORMS_FILE, rows)   # لا نحفظ المفتاح/السكريت


def list_platforms() -> Dict[str, Any]:
    return {"success": True, "platforms": _load(PLATFORMS_FILE)}


def delete_platform(name: str) -> Dict[str, Any]:
    rows = _load(PLATFORMS_FILE)
    kept = [r for r in rows if r.get("name") != name]
    _save(PLATFORMS_FILE, kept)
    return {"success": len(kept) != len(rows)}


# ── اتصال موقع ويب ────────────────────────────────────────────
def connect_website(name: str = "", url: str = "", api_key: str = "",
                    **_extra) -> Dict[str, Any]:
    """يفحص وصول الموقع وهل يحتاج مصادقة (login)."""
    url = (url or "").strip()
    if not url:
        return {"success": False, "error": "url مطلوب"}
    from .source_manager import SourceManager
    p = SourceManager.probe(url, api_key=api_key or None)
    needs_auth = bool(p.get("needs_key") or p.get("auth_failed")
                      or p.get("status_code") in (401, 403))
    res = {"success": bool(p.get("reachable")),
           "reachable": bool(p.get("reachable")),
           "needs_auth": needs_auth,
           "auth_ok": bool(p.get("auth_ok")),
           "suggested_type": p.get("suggested_type"),
           "status": p.get("status_code"),
           "login_url": url if needs_auth else None,
           "error": p.get("error")}
    if res["success"]:
        rows = _load(WEBSITES_FILE)
        key = (name or url).strip()
        rows = [r for r in rows if r.get("name") != key]
        rows.append({"name": key, "url": url, "needs_auth": needs_auth,
                     "added_at": int(time.time())})
        _save(WEBSITES_FILE, rows)
    return res


def list_websites() -> Dict[str, Any]:
    return {"success": True, "websites": _load(WEBSITES_FILE)}
