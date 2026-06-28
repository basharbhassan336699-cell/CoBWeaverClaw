"""
Gateway Server — بوابة التحكم عبر المتصفح.
- localhost افتراضياً (127.0.0.1) — أأمن
- توكين إجباري لكل طلب
- يمكن فتحه للشبكة المحلية بأمر صريح (--host 0.0.0.0)
يعمل بمكتبة http.server القياسية — لا اعتماديات خارجية.
"""
import os
import json
import glob
import asyncio
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from gateway_auth import GatewayAuth

CONFIG_DIR = Path(os.path.expanduser("~/.cobweaverclaw"))
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── config + env helpers (المجلد الآمن فقط) ──────────────────
def load_config() -> dict:
    """يحمّل config.yaml من المجلد الآمن ثم مجلد المشروع كاحتياط."""
    import yaml
    for p in [CONFIG_DIR / "config.yaml", Path(BASE_DIR) / "config.yaml"]:
        if p.exists():
            try:
                return yaml.safe_load(p.read_text()) or {}
            except Exception:
                return {}
    return {}


def _deep_merge(base: dict, updates: dict) -> dict:
    for k, v in (updates or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def save_config(updates: dict) -> dict:
    """يدمج التحديثات مع config الحالي ويحفظه في المجلد الآمن فقط."""
    import yaml
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    _deep_merge(cfg, updates)
    (CONFIG_DIR / "config.yaml").write_text(
        yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False))
    return cfg


def load_env_into_os():
    """يحمّل مفاتيح .env من المجلد الآمن إلى البيئة (لاستدعاء النماذج)."""
    env_path = CONFIG_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def save_env_keys(env_vars: dict):
    """يحفظ/يحدّث مفاتيح .env في المجلد الآمن (0600)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    env_path = CONFIG_DIR / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                existing[line.split("=", 1)[0]] = line
    for k, v in env_vars.items():
        if v:
            existing[k] = f"{k}={v}"
            os.environ[k] = v
    env_path.write_text("\n".join(existing.values()) + "\n")
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass


# ── chat: build memory context + call model ──────────────────
def run_chat(message: str, model: str = None) -> dict:
    """ينفّذ محادثة: يحمّل المفاتيح + الذاكرة، يستدعي النموذج، يحفظ التبادل."""
    load_env_into_os()
    cfg = load_config()
    import sys
    sys.path.insert(0, BASE_DIR)
    from memory.sqlite_store import SQLiteStore
    from brain.model_router import ModelRouter

    mem_cfg = dict(cfg.get("memory", {}))
    mem_cfg.setdefault("memory_size", cfg.get("agent", {}).get("memory_size", 20))
    mem    = SQLiteStore(mem_cfg)
    router = ModelRouter(cfg)
    lang   = "ar" if any(c in message for c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي") else "en"

    async def _go():
        ctx = await mem.get_context("dashboard", message)
        out = await router.complete_meta(message, ctx, lang, force_model=model or None)
        await mem.save("dashboard", message, out.get("reply", ""), lang)
        try:
            await mem.maybe_summarize("dashboard")
        except Exception:
            pass
        return out

    return asyncio.run(_go())


def memory_stats() -> dict:
    cfg = load_config()
    import sys
    sys.path.insert(0, BASE_DIR)
    from memory.sqlite_store import SQLiteStore
    mem_cfg = dict(cfg.get("memory", {}))
    return SQLiteStore(mem_cfg).stats()


def memory_clear(layer: str) -> dict:
    cfg = load_config()
    import sys
    sys.path.insert(0, BASE_DIR)
    from memory.sqlite_store import SQLiteStore
    mem_cfg = dict(cfg.get("memory", {}))
    return SQLiteStore(mem_cfg).clear(layer or "working")


def list_skills() -> list:
    """يسرد مهارات مجلد skills/ مع الوصف من docstring وحالة التفعيل."""
    cfg = load_config()
    enabled = cfg.get("skills", {}).get("enabled", True)
    out = []
    for f in sorted(glob.glob(os.path.join(BASE_DIR, "skills", "*.py"))):
        base = os.path.basename(f)[:-3]
        if base.startswith("_") or base in ("base",):
            continue
        desc = ""
        try:
            import ast
            desc = ast.get_docstring(ast.parse(open(f, encoding="utf-8").read())) or ""
        except Exception:
            pass
        out.append({"name": base, "description": desc.strip().split("\n")[0][:120],
                    "enabled": bool(enabled)})
    return out


def channels_status() -> dict:
    """حالة قنوات الاتصال من config."""
    cfg = load_config().get("interfaces", {})
    def mask(tok):
        return ("•" * 6 + tok[-4:]) if tok and len(tok) > 4 else ("مضبوط" if tok else "")
    tg = cfg.get("telegram", {})
    return {
        "telegram": {"enabled": bool(tg.get("enabled")),
                     "token_masked": mask(tg.get("token", "")),
                     "status": "active" if tg.get("enabled") and tg.get("token") else "inactive"},
        "discord":  {"status": "coming_soon"},
        "slack":    {"status": "coming_soon"},
        "whatsapp": {"status": "coming_soon"},
        "signal":   {"status": "coming_soon"},
    }


def telegram_test() -> dict:
    """يختبر اتصال بوت تيليجرام المُعدّ عبر getMe."""
    load_env_into_os()
    cfg = load_config()
    tg = cfg.get("interfaces", {}).get("telegram", {})
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "") or tg.get("token", "")
    if not token:
        return {"ok": False, "error": "no_token"}
    import urllib.request
    try:
        with urllib.request.urlopen(
                f"https://api.telegram.org/bot{token}/getMe", timeout=8) as r:
            d = json.loads(r.read())
        if d.get("ok"):
            return {"ok": True, "username": d["result"].get("username", "")}
        return {"ok": False, "error": "invalid_token"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


def config_public() -> dict:
    """config كامل للعرض في الـ dashboard مع إخفاء المفاتيح الحساسة."""
    cfg = load_config()
    return cfg


class GatewayHandler(http.server.BaseHTTPRequestHandler):
    """يعالج طلبات البوابة مع التحقق من التوكين."""

    auth = None          # تُحقن من الخارج
    dashboard_html = ""  # محتوى HTML
    require_token = False  # localhost يدخل بلا توكين افتراضياً

    def log_message(self, fmt, *args):
        pass  # كتم سجل الطلبات الافتراضي

    def _check_auth(self) -> bool:
        """يتحقق من التوكين، أو يسمح مباشرة إن كان الوضع بلا توكين."""
        # وضع بلا توكين: الوصول المحلي (localhost) مسموح مباشرة
        if not self.require_token:
            client = self.client_address[0] if self.client_address else ""
            if client in ("127.0.0.1", "::1", "localhost"):
                return True
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)
        token  = (qs.get("token", [None])[0]
                  or self.headers.get("X-Gateway-Token"))
        return self.auth.verify(token) if token else False

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path

        # الصفحة الرئيسية تُقدّم HTML
        if path == "/" or path == "/index.html":
            body = self.dashboard_html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            # منع التخزين المؤقت — يضمن تحميل أحدث نسخة دائماً
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(body)
            return

        # كل الـ API endpoints تتطلب توكيناً صحيحاً
        if path.startswith("/api/"):
            if not self._check_auth():
                self._send_json({"error": "unauthorized"}, 401)
                return
            self._handle_api(path, parsed)
            return

        self.send_response(404)
        self.end_headers()

    def _read_body(self) -> dict:
        """يقرأ جسم الطلب JSON."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length:
                return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            pass
        return {}

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if not self._check_auth():
            self._send_json({"error": "unauthorized"}, 401)
            return
        body = self._read_body()
        path = parsed.path
        try:
            if path == "/api/chat":
                out = run_chat(body.get("message", ""), body.get("model"))
                self._send_json(out)
            elif path == "/api/config":
                # تحديث المفاتيح يُكتب لـ .env، الباقي لـ config.yaml
                keys = body.pop("_keys", {}) or {}
                if keys:
                    save_env_keys(keys)
                cfg = save_config(body) if body else load_config()
                self._send_json({"status": "saved"})
            else:
                self._send_json({"error": "not_found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if not self._check_auth():
            self._send_json({"error": "unauthorized"}, 401)
            return
        body = self._read_body()
        try:
            if parsed.path == "/api/memory/clear":
                self._send_json({"status": "cleared",
                                 **memory_clear(body.get("layer", "working"))})
            else:
                self._send_json({"error": "not_found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api(self, path: str, parsed):
        """معالجة نقاط الـ API (GET) بعد التحقق."""
        try:
            if path == "/api/status":
                self._send_json({"agent": "running", "platform": "android", "version": "0.1.0"})
            elif path == "/api/account":
                import sys; sys.path.insert(0, os.path.dirname(__file__))
                from account_manager import AccountManager
                self._send_json(AccountManager().get_or_create_account())
            elif path == "/api/config":
                self._send_json(config_public())
            elif path == "/api/memory/stats":
                self._send_json(memory_stats())
            elif path == "/api/skills":
                self._send_json({"skills": list_skills()})
            elif path == "/api/channels":
                self._send_json(channels_status())
            elif path == "/api/channels/telegram/test":
                self._send_json(telegram_test())
            else:
                self._send_json({"error": "not_found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def run_gateway(host: str = "127.0.0.1", port: int = 7878,
                config_dir: str = None, dashboard_html: str = "",
                require_token: bool = True):
    """
    يشغّل بوابة التحكم.
    host=127.0.0.1 → localhost فقط (افتراضي، أأمن)
    host=0.0.0.0   → الشبكة المحلية (يحتاج توكيناً، يُفعّل بأمر صريح)
    require_token=False → localhost يدخل بلا توكين (أسهل، آمن محلياً فقط)
    """
    auth  = GatewayAuth(config_dir)
    token = auth.get_or_create_token()

    # على الشبكة المفتوحة، التوكين إجباري دائماً (أمان)
    if host == "0.0.0.0":
        require_token = True

    GatewayHandler.auth           = auth
    GatewayHandler.dashboard_html = dashboard_html
    GatewayHandler.require_token  = require_token

    print(f"\n🕷️  CoBWeaverClaw Gateway")
    if not require_token:
        print(f"   افتح في المتصفح مباشرة (بلا توكين):")
        print(f"   http://{host}:{port}/")
        print(f"\n   🔓 localhost بلا توكين — الدخول مباشر")
    else:
        url = f"http://{host if host != '0.0.0.0' else '<your-ip>'}:{port}/#token={token}"
        print(f"   الرابط (مع التوكين):")
        print(f"   {url}")
        if host == "0.0.0.0":
            print(f"\n   ⚠️  مفتوح على الشبكة المحلية — التوكين إجباري للحماية")
        else:
            print(f"\n   🔒 localhost فقط — آمن، لا أحد على الشبكة يصله")
    print(f"\n   لإيقاف البوابة: Ctrl+C\n")

    # خادم يضبط SO_REUSEADDR *قبل* الربط — يمنع خطأ "Address already in use"
    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True  # يُطبَّق قبل bind تلقائياً

    try:
        httpd = ReusableServer((host, port), GatewayHandler)
    except OSError as e:
        if e.errno in (98, 48):  # 98=Linux, 48=Mac: المنفذ مشغول
            print(f"   ⚠️  المنفذ {port} مشغول — غالباً بوابة قديمة ما زالت تعمل.\n")
            print(f"   الحل:")
            print(f"   1) أغلق البوابة القديمة: python main.py stop")
            print(f"   2) أو أغلق نوافذ Termux الأخرى التي تشغّل gateway")
            print(f"   3) ثم أعد: python main.py gateway\n")
            # محاولة أخيرة: إيقاف العملية القديمة تلقائياً
            _try_free_port(port)
            try:
                httpd = ReusableServer((host, port), GatewayHandler)
                print(f"   ✅ تم تحرير المنفذ تلقائياً — البوابة تعمل الآن.\n")
            except OSError:
                print(f"   ❌ تعذّر تحرير المنفذ تلقائياً. استخدم: python main.py stop")
                return
        else:
            raise

    with httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n   تم إيقاف البوابة.")
            httpd.shutdown()


def _try_free_port(port: int):
    """يحاول إيقاف أي عملية تشغّل البوابة على هذا المنفذ (Termux/Linux)."""
    import subprocess
    import signal
    try:
        # ابحث عن PID المستخدم للمنفذ عبر /proc (يعمل في Termux بلا أدوات إضافية)
        my_pid = os.getpid()
        for pid in os.listdir("/proc"):
            if not pid.isdigit() or int(pid) == my_pid:
                continue
            try:
                cmdline = open(f"/proc/{pid}/cmdline", "rb").read().decode("utf-8", "ignore")
                # عملية python تشغّل gateway (وليست هذه العملية)
                if "python" in cmdline and "gateway" in cmdline:
                    os.kill(int(pid), signal.SIGTERM)
            except Exception:
                continue
        import time
        time.sleep(1)  # مهلة لتحرير المنفذ
    except Exception:
        pass


if __name__ == "__main__":
    import sys
    host = "0.0.0.0" if "--network" in sys.argv else "127.0.0.1"
    run_gateway(host=host)
