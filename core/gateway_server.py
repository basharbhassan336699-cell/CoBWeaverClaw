"""
Gateway Server — بوابة التحكم عبر المتصفح.
- localhost افتراضياً (127.0.0.1) — أأمن
- توكين إجباري لكل طلب
- يمكن فتحه للشبكة المحلية بأمر صريح (--host 0.0.0.0)
يعمل بمكتبة http.server القياسية — لا اعتماديات خارجية.
"""
import os
import json
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from gateway_auth import GatewayAuth


class GatewayHandler(http.server.BaseHTTPRequestHandler):
    """يعالج طلبات البوابة مع التحقق من التوكين."""

    auth = None          # تُحقن من الخارج
    dashboard_html = ""  # محتوى HTML

    def log_message(self, fmt, *args):
        pass  # كتم سجل الطلبات الافتراضي

    def _check_auth(self) -> bool:
        """يتحقق من التوكين في الـ query أو الـ header."""
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
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path

        # الصفحة الرئيسية تُقدّم HTML (التوكين يُتحقق منه عبر JS من الـ hash)
        if path == "/" or path == "/index.html":
            body = self.dashboard_html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
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

    def _handle_api(self, path: str, parsed):
        """معالجة نقاط الـ API بعد التحقق."""
        if path == "/api/status":
            import platform
            self._send_json({
                "agent":    "running",
                "platform": platform.system().lower(),
                "version":  "0.1.0",
            })
        elif path == "/api/account":
            import sys, os; sys.path.insert(0, os.path.dirname(__file__)); from account_manager import AccountManager
            am = AccountManager()
            self._send_json(am.get_or_create_account())
        else:
            self._send_json({"error": "not_found"}, 404)


def run_gateway(host: str = "127.0.0.1", port: int = 7878,
                config_dir: str = None, dashboard_html: str = ""):
    """
    يشغّل بوابة التحكم.
    host=127.0.0.1 → localhost فقط (افتراضي، أأمن)
    host=0.0.0.0   → الشبكة المحلية (يحتاج توكيناً، يُفعّل بأمر صريح)
    """
    auth  = GatewayAuth(config_dir)
    token = auth.get_or_create_token()

    GatewayHandler.auth           = auth
    GatewayHandler.dashboard_html = dashboard_html

    url = f"http://{host if host != '0.0.0.0' else '<your-ip>'}:{port}/#token={token}"

    print(f"\n🕷️  CoBWeaverClaw Gateway")
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
