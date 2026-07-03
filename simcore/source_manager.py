"""
SimCore — مدير المصادر
يدير الاتصال بأي موقع أو API يدرجه المستخدم
"""
import requests
from typing import Dict, Any, Optional
from .config import SourceConfig


class SourceManager:

    @staticmethod
    def probe(url: str) -> Dict[str, Any]:
        """
        اكتشاف نوع المصدر وما يحتاجه.
        يعيد: { reachable, needs_key, needs_id, suggested_type }
        """
        result = {
            "url":            url,
            "reachable":      False,
            "needs_key":      False,
            "needs_id":       False,
            "suggested_type": "web",
            "status_code":    None,
            "error":          None,
        }
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "SimCore/1.0"})
            result["status_code"] = r.status_code
            result["reachable"]   = r.status_code < 500

            # كشف تلقائي: 401/403 = يحتاج مفتاح
            if r.status_code in (401, 403):
                result["needs_key"] = True

            # كشف نوع المصدر من الـ URL
            url_lower = url.lower()
            if any(x in url_lower for x in ["api.", "/api/", "api.twitter", "api.binance",
                                              "api.coinbase", "api.reddit"]):
                result["suggested_type"] = "api"
                result["needs_key"]      = True
            elif any(x in url_lower for x in ["twitter", "x.com", "reddit", "telegram",
                                                "discord", "instagram", "tiktok"]):
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
    def fetch_content(source: SourceConfig, query: str = "") -> Dict[str, Any]:
        """
        جلب المحتوى من مصدر.
        يعيد: { success, content, error }
        """
        headers = {"User-Agent": "SimCore/1.0"}
        if source.api_key:
            headers["Authorization"] = f"Bearer {source.api_key}"

        params = {}
        if query:
            params["q"] = query
        if source.account_id:
            params["user_id"] = source.account_id

        try:
            r = requests.get(source.url, headers=headers, params=params, timeout=15)
            return {
                "success": r.status_code == 200,
                "content": r.text[:50000],   # حد 50k حرف
                "status":  r.status_code,
                "error":   None if r.status_code == 200 else f"HTTP {r.status_code}",
            }
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}
