"""
Internal Browser — متصفح داخلي للوكيل.

ما يفعله فعلاً (بصدق):
- يجلب صفحات الويب ويستخرج نصها وروابطها
- يبحث في محركات البحث ويُعيد النتائج
- يحتفظ بسجل تصفّح وصفحات مفضّلة

ما لا يفعله (بوضوح):
- لا يُشغّل JavaScript (لا rendering كامل مثل Chrome)
- للصفحات التي تحتاج JS، يحتاج إضافة Playwright لاحقاً

يعمل بمكتبة urllib القياسية — لا اعتماديات إجبارية.
html.parser لاستخراج النص.
"""
import os
import json
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime


class _TextExtractor(HTMLParser):
    """يستخرج النص المرئي والروابط من HTML."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.links      = []
        self._skip      = False
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True
        if tag == "a":
            for k, v in attrs:
                if k == "href":
                    self._current_href = v

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag == "a":
            self._current_href = None

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if text:
            self.text_parts.append(text)
            if self._current_href:
                self.links.append({"text": text[:60], "url": self._current_href})


class InternalBrowser:
    """
    متصفح داخلي للوكيل.
    وضعان:
    - يدوي: المستخدم يطلب فتح/بحث صفحة محددة
    - تلقائي: الوكيل يبحث ويقرأ ويُلخّص لإنجاز مهمة
    """

    USER_AGENT = "Mozilla/5.0 (CoBWeaverClaw/0.1; +https://github.com/basharbhassan336699-cell/CoBWeaverClaw)"

    def __init__(self, config_dir: str = None):
        self.config_dir   = Path(config_dir or os.path.expanduser("~/.cobweaverclaw"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.history_file   = self.config_dir / "browser_history.json"
        self.favorites_file = self.config_dir / "browser_favorites.json"

    def fetch(self, url: str, max_chars: int = 5000) -> dict:
        """
        يجلب صفحة ويستخرج نصها وروابطها.
        يُرجع: {url, title, text, links, error}
        """
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                raw     = resp.read(2_000_000)  # حد أقصى 2MB
                html    = raw.decode(charset, errors="replace")
        except Exception as e:
            return {"url": url, "error": str(e), "text": "", "links": []}

        # استخراج العنوان
        title = ""
        low   = html.lower()
        if "<title>" in low:
            s = low.index("<title>") + 7
            e = low.index("</title>", s) if "</title>" in low[s:] else s
            title = html[s:e].strip()

        # استخراج النص والروابط
        parser = _TextExtractor()
        try:
            parser.feed(html)
        except Exception:
            pass

        text = " ".join(parser.text_parts)[:max_chars]
        self._add_history(url, title)

        return {
            "url":   url,
            "title": title,
            "text":  text,
            "links": parser.links[:30],
            "error": None,
        }

    def search(self, query: str, max_results: int = 5) -> dict:
        """
        يبحث عبر DuckDuckGo HTML (بلا مفتاح API).
        يُرجع نتائج البحث.
        """
        q   = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={q}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return {"query": query, "error": str(e), "results": []}

        # استخراج نتائج DuckDuckGo (روابط result__a)
        results = []
        parts   = html.split('class="result__a"')
        for part in parts[1:max_results + 1]:
            try:
                href_start = part.index('href="') + 6
                href_end   = part.index('"', href_start)
                href       = part[href_start:href_end]
                # فك ترميز رابط DuckDuckGo
                if "uddg=" in href:
                    href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                text_start = part.index(">", href_end) + 1
                text_end   = part.index("</a>", text_start)
                title      = part[text_start:text_end].strip()
                # إزالة وسوم HTML من العنوان
                import re
                title = re.sub(r"<[^>]+>", "", title)
                results.append({"title": title, "url": href})
            except Exception:
                continue

        return {"query": query, "results": results, "error": None}

    def auto_research(self, query: str, depth: int = 2) -> dict:
        """
        بحث تلقائي: يبحث ثم يقرأ أهم النتائج ويُجمّع ملخصاً.
        depth = عدد الصفحات التي يقرأها.
        """
        search_res = self.search(query, max_results=depth)
        if search_res.get("error"):
            return search_res

        pages = []
        for result in search_res["results"][:depth]:
            page = self.fetch(result["url"], max_chars=2000)
            if not page.get("error"):
                pages.append({
                    "title": page["title"] or result["title"],
                    "url":   page["url"],
                    "summary": page["text"][:500],
                })

        return {
            "query":   query,
            "sources": pages,
            "count":   len(pages),
        }

    # ── السجل والمفضلة ──────────────────────────────────────
    def _add_history(self, url: str, title: str):
        history = self._load(self.history_file, [])
        history.insert(0, {
            "url": url, "title": title,
            "time": datetime.now().isoformat(),
        })
        self._save(self.history_file, history[:100])  # آخر 100

    def get_history(self) -> list:
        return self._load(self.history_file, [])

    def add_favorite(self, url: str, name: str = "") -> bool:
        favs = self._load(self.favorites_file, [])
        if any(f["url"] == url for f in favs):
            return False
        favs.append({"url": url, "name": name or url, "added": datetime.now().isoformat()})
        self._save(self.favorites_file, favs)
        return True

    def get_favorites(self) -> list:
        return self._load(self.favorites_file, [])

    def _load(self, path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return default

    def _save(self, path: Path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
