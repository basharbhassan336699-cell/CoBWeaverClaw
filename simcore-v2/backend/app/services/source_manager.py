"""
SimCore — مدير المصادر المفتوحة
يتصل بأي موقع أو منصة يدرجها المستخدم حسب توجهه
"""
import requests
from typing import Dict, Any


class SourceManager:

    @staticmethod
    def probe(url: str) -> Dict[str, Any]:
        """اكتشاف نوع المصدر وما يحتاجه من مفتاح أو ID"""
        result = {
            "url": url, "reachable": False,
            "needs_key": False, "needs_id": False,
            "suggested_type": "web", "status_code": None, "error": None,
        }
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "SimCore/1.0"})
            result["status_code"] = r.status_code
            result["reachable"]   = r.status_code < 500
            if r.status_code in (401, 403):
                result["needs_key"] = True
            url_l = url.lower()
            if any(x in url_l for x in ["api.", "/api/", "api.binance", "api.coinbase",
                                          "api.twitter", "api.reddit", "api.telegram",
                                          "api.polymarket", "api.kraken", "api.bybit"]):
                result["suggested_type"] = "api"
                result["needs_key"]      = True
            elif any(x in url_l for x in ["twitter.com", "x.com", "reddit.com", "t.me",
                                            "discord.com", "instagram.com", "tiktok.com",
                                            "facebook.com", "linkedin.com", "telegram.org"]):
                result["suggested_type"] = "social"
                result["needs_key"]      = True
                result["needs_id"]       = True
        except requests.exceptions.ConnectionError:
            result["error"] = "connection_failed"
        except requests.exceptions.Timeout:
            result["error"] = "timeout"
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    def fetch(url: str, api_key: str = None, account_id: str = None,
              query: str = "") -> Dict[str, Any]:
        """جلب المحتوى من أي مصدر"""
        headers = {"User-Agent": "SimCore/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        params = {}
        if query:       params["q"]       = query
        if account_id:  params["user_id"] = account_id
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            return {
                "success": r.status_code == 200,
                "content": r.text[:50000],
                "status":  r.status_code,
                "error":   None if r.status_code == 200 else f"HTTP {r.status_code}",
            }
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}
