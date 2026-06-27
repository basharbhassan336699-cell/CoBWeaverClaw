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

    with socketserver.TCPServer((host, port), GatewayHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n   تم إيقاف البوابة.")


if __name__ == "__main__":
    import sys
    host = "0.0.0.0" if "--network" in sys.argv else "127.0.0.1"
    run_gateway(host=host)
