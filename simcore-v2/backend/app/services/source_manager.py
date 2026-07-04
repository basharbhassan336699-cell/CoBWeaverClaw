"""
SimCore — مدير المصادر المفتوحة
يتصل بأي موقع أو منصة يدرجها المستخدم حسب توجهه
"""
import requests
from typing import Dict, Any


class SourceManager:

    @staticmethod
    def probe(url: str, api_key: str = None, secret: str = None) -> dict:
        result = {"url": url, "reachable": False, "needs_key": False,
                  "needs_secret": False, "suggested_type": "web", "error": None}
        url_l = url.lower()

        # كشف نوع المصدر
        if any(x in url_l for x in ["api.binance", "api.bybit", "api.kraken",
                                      "api.coinbase", "api.kucoin", "api.okx"]):
            result["suggested_type"] = "exchange"
            result["needs_key"]      = True
            result["needs_secret"]   = True
        elif any(x in url_l for x in ["api.", "/api/", "api.twitter", "api.telegram",
                                        "api.reddit", "api.discord"]):
            result["suggested_type"] = "api"
            result["needs_key"]      = True
        elif any(x in url_l for x in ["twitter.com", "x.com", "reddit.com",
                                        "discord.com", "t.me", "instagram.com"]):
            result["suggested_type"] = "social"
            result["needs_key"]      = True
            result["needs_secret"]   = True
        else:
            result["suggested_type"] = "web"

        # اتصال فعلي
        try:
            headers = {"User-Agent": "SimCore/1.0"}
            if api_key:
                headers["X-MBX-APIKEY"] = api_key  # Binance
                headers["Authorization"] = f"Bearer {api_key}"
            r = requests.get(url, headers=headers, timeout=8)
            result["status_code"] = r.status_code
            result["reachable"]   = r.status_code < 500
            if r.status_code in (401, 403):
                result["needs_key"]    = True
                result["auth_failed"]  = True
                result["error"]        = "مفتاح غير صحيح أو غير مصرح"
            elif r.status_code == 200 and api_key:
                result["auth_ok"] = True
        except requests.exceptions.ConnectionError:
            result["error"] = "تعذّر الاتصال بالموقع"
        except requests.exceptions.Timeout:
            result["error"] = "انتهت مهلة الاتصال"
        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def fetch(url: str, api_key: str = None, secret: str = None,
              account_id: str = None, query: str = "") -> dict:
        headers = {"User-Agent": "SimCore/1.0"}
        params  = {}

        if api_key:
            headers["Authorization"]  = f"Bearer {api_key}"
            headers["X-MBX-APIKEY"]   = api_key

        if secret:
            import hmac, hashlib, time
            ts        = str(int(time.time() * 1000))
            signature = hmac.new(secret.encode(), ts.encode(),
                                 hashlib.sha256).hexdigest()
            params["timestamp"] = ts
            params["signature"] = signature

        if query:       params["q"]       = query
        if account_id:  params["user_id"] = account_id

        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            return {"success": r.status_code == 200,
                    "content": r.text[:50000],
                    "status":  r.status_code,
                    "error":   None if r.status_code == 200 else f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}
