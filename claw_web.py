"""
CoBWeaverClaw — Web Intelligence Layer
يجمع ثلاث أدوات في نقطة دخول واحدة:

  ClawStealth  ← curl-impersonate  — طلبات HTTP تُقلّد بصمة Chrome/Firefox
  ClawBrowser  ← browser-use       — متصفح حقيقي مع AI agent
  ClawCrawl    ← firecrawl SDK     — scraping/crawling جاهز للـ LLM

المنهجية:
  1. ClawStealth  — للمواقع العادية السريعة (0.4 ثانية)
  2. ClawCrawl    — للبحث والأخبار والمحتوى الغني (3.4 ثانية، Markdown نظيف)
  3. ClawBrowser  — للمواقع المحمية وتسجيل الدخول والتفاعل (5-10 ثانية)

الاختيار تلقائي حسب الطلب والموقف.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("cobweaverclaw.web")


# ════════════════════════════════════════════════════════════
# نتيجة موحدة من أي أداة
# ════════════════════════════════════════════════════════════

@dataclass
class WebResult:
    success:    bool
    content:    str           # Markdown أو نص نظيف
    url:        str
    tool_used:  str           # "stealth" | "crawl" | "browser"
    screenshot: Optional[str] = None   # base64 إذا طُلب
    metadata:   dict          = field(default_factory=dict)
    error:      Optional[str] = None


# ════════════════════════════════════════════════════════════
# ClawStealth — curl-impersonate wrapper
# ════════════════════════════════════════════════════════════

class ClawStealth:
    """
    يُقلّد بصمة TLS وHTTP/2 لمتصفحات Chrome/Firefox.
    يستخدم claw-stealth/chrome/curl_chrome116 أو curl_ff117.
    لا يحتاج Python dependencies — يستدعي subprocess فقط.
    """

    STEALTH_DIR = Path(__file__).parent / "claw-stealth"

    BROWSERS = {
        "chrome116":       "chrome/curl_chrome116",
        "chrome110":       "chrome/curl_chrome110",
        "chrome107":       "chrome/curl_chrome107",
        "chrome99":        "chrome/curl_chrome99",
        "chrome99_android":"chrome/curl_chrome99_android",
        "edge101":         "chrome/curl_edge101",
        "safari15_5":      "chrome/curl_safari15_5",
        "ff117":           "firefox/curl_ff117",
        "ff109":           "firefox/curl_ff109",
        "ff102":           "firefox/curl_ff102",
    }

    def fetch(
        self,
        url:          str,
        browser:      str = "chrome116",
        extra_headers: list[str] | None = None,
        timeout:      int = 15,
        method:       str = "GET",
        data:         str | None = None,
    ) -> WebResult:
        """
        جلب URL بتقليد بصمة المتصفح المحدد.
        يعيد WebResult مع المحتوى الخام.
        """
        script = self.STEALTH_DIR / self.BROWSERS.get(browser, self.BROWSERS["chrome116"])

        if not script.exists():
            # fallback لـ requests عادي (بلا curl-impersonate مبني)
            import requests
            try:
                r = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36"
                }, timeout=timeout)
                return WebResult(success=True, content=r.text,
                                 url=url, tool_used="stealth-fallback")
            except Exception as e:
                return WebResult(success=False, content="", url=url,
                                 tool_used="stealth", error=str(e))

        cmd = [str(script), "-s", "-L", "--max-time", str(timeout)]

        if extra_headers:
            for h in extra_headers:
                cmd += ["-H", h]

        if method == "POST" and data:
            cmd += ["-X", "POST", "-d", data]

        cmd.append(url)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 5
            )
            if result.returncode == 0:
                logger.info("ClawStealth ✅ %s (%d chars)", url, len(result.stdout))
                return WebResult(
                    success=True, content=result.stdout,
                    url=url, tool_used="stealth",
                    metadata={"browser": browser}
                )
            return WebResult(
                success=False, content="", url=url, tool_used="stealth",
                error=f"exit {result.returncode}: {result.stderr[:200]}"
            )
        except subprocess.TimeoutExpired:
            return WebResult(success=False, content="", url=url, tool_used="stealth",
                             error="timeout")
        except Exception as e:
            return WebResult(success=False, content="", url=url, tool_used="stealth",
                             error=str(e))

    def fetch_many(self, urls: list[str], browser: str = "chrome116",
                   timeout: int = 15) -> list[WebResult]:
        """جلب قائمة URLs متوازية"""
        # subprocess pool بسيط
        results = []
        for url in urls:
            results.append(self.fetch(url, browser=browser, timeout=timeout))
        return results


# ════════════════════════════════════════════════════════════
# ClawCrawl — firecrawl Python SDK wrapper
# ════════════════════════════════════════════════════════════

class ClawCrawl:
    """
    Scraping وCrawling وSearch جاهز للـ LLM.
    يعيد Markdown نظيف مباشرة بدون معالجة إضافية.
    يستخدم حزمة firecrawl-py (تُثبَّت عبر pip عند الحاجة).
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key  = api_key  or os.environ.get("FIRECRAWL_API_KEY") or \
                        os.environ.get("CLAW_CRAWL_API_KEY", "")
        self.base_url = base_url or os.environ.get("CLAW_CRAWL_BASE_URL")
        self._client  = None

    def _get_client(self):
        if self._client is None:
            try:
                from firecrawl import Firecrawl as _FC
            except ImportError:
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "pip", "install",
                               "firecrawl-py", "-q"], check=True)
                from firecrawl import Firecrawl as _FC
            self._client = _FC(
                api_key=self.api_key,
                **({"base_url": self.base_url} if self.base_url else {})
            )
        return self._client

    def scrape(
        self,
        url:     str,
        formats: list[str] | None = None,
        prompt:  str | None = None,
    ) -> WebResult:
        """
        Scrape صفحة واحدة وأعد Markdown نظيف.
        prompt: إذا حدد، يستخرج بيانات منظمة JSON بدل Markdown.
        """
        if formats is None:
            formats = ["markdown"]
        try:
            client  = self._get_client()
            options = {"formats": formats}
            if prompt:
                options["jsonOptions"] = {"prompt": prompt}
            result  = client.scrape(url, **options)
            content = getattr(result, "markdown", "") or str(result)
            logger.info("ClawCrawl scrape ✅ %s (%d chars)", url, len(content))
            return WebResult(
                success=True, content=content, url=url, tool_used="crawl",
                metadata={"formats": formats}
            )
        except Exception as e:
            logger.error("ClawCrawl scrape ❌ %s: %s", url, e)
            return WebResult(success=False, content="", url=url, tool_used="crawl",
                             error=str(e))

    def search(
        self,
        query:  str,
        limit:  int = 5,
        format: str = "markdown",
    ) -> list[WebResult]:
        """
        ابحث في الويب وأعد المحتوى الكامل لكل نتيجة.
        يعيد قائمة WebResult واحدة لكل صفحة.
        """
        try:
            client  = self._get_client()
            results = client.search(query, limit=limit)
            output  = []
            for r in (results if isinstance(results, list) else [results]):
                url     = getattr(r, "url", str(r))
                content = getattr(r, "markdown", "") or getattr(r, "content", "")
                output.append(WebResult(
                    success=True, content=content, url=url, tool_used="crawl",
                    metadata={"query": query}
                ))
            logger.info("ClawCrawl search ✅ '%s' → %d نتيجة", query, len(output))
            return output
        except Exception as e:
            logger.error("ClawCrawl search ❌ '%s': %s", query, e)
            return [WebResult(success=False, content="", url="", tool_used="crawl",
                              error=str(e))]

    def crawl(
        self,
        url:    str,
        limit:  int = 10,
        format: str = "markdown",
    ) -> list[WebResult]:
        """
        زحف كامل موقع واجمع كل صفحاته.
        مفيد لاستخراج وثائق كاملة أو كاتالوج.
        """
        try:
            client  = self._get_client()
            job     = client.crawl_url(url, limit=limit,
                                       scrape_options={"formats": [format]})
            output  = []
            for page in (getattr(job, "data", []) or []):
                content = getattr(page, "markdown", "") or ""
                src_url = getattr(getattr(page, "metadata", None), "source_url", url)
                if content:
                    output.append(WebResult(
                        success=True, content=content,
                        url=src_url, tool_used="crawl"
                    ))
            logger.info("ClawCrawl crawl ✅ %s → %d صفحة", url, len(output))
            return output
        except Exception as e:
            logger.error("ClawCrawl crawl ❌ %s: %s", url, e)
            return [WebResult(success=False, content="", url=url, tool_used="crawl",
                              error=str(e))]

    def map_site(self, url: str, search: str = "") -> list[str]:
        """اكتشف كل روابط موقع فوراً"""
        try:
            client  = self._get_client()
            result  = client.map(url, search=search)
            links   = getattr(result, "links", result) or []
            return [l.get("url", str(l)) if isinstance(l, dict) else str(l)
                    for l in links]
        except Exception as e:
            logger.error("ClawCrawl map ❌ %s: %s", url, e)
            return []

    async def scrape_async(self, url: str, formats: list[str] | None = None) -> WebResult:
        """نسخة async من scrape"""
        try:
            try:
                from firecrawl import AsyncFirecrawl
            except ImportError:
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "pip", "install",
                               "firecrawl-py", "-q"], check=True)
                from firecrawl import AsyncFirecrawl
            client  = AsyncFirecrawl(api_key=self.api_key)
            result  = await client.scrape(url, formats=formats or ["markdown"])
            content = getattr(result, "markdown", "") or str(result)
            return WebResult(success=True, content=content, url=url, tool_used="crawl")
        except Exception as e:
            return WebResult(success=False, content="", url=url, tool_used="crawl",
                             error=str(e))


# ════════════════════════════════════════════════════════════
# ClawBrowser — browser-use wrapper
# ════════════════════════════════════════════════════════════

class ClawBrowser:
    """
    متصفح Chromium حقيقي مع AI agent.
    يُقلّد سلوك إنساني كامل: حركة ماوس، تمرير، توقيت.
    يدعم: تسجيل دخول، ملء نماذج، screenshots، تصفح متعدد الصفحات.
    """

    def __init__(
        self,
        llm_api_key:   str | None = None,
        llm_base_url:  str | None = None,
        llm_model:     str = "claude-sonnet-4-6",
        headless:      bool = True,
    ):
        self.llm_api_key  = llm_api_key  or os.environ.get("ANTHROPIC_API_KEY") or \
                            os.environ.get("LLM_API_KEY", "")
        self.llm_base_url = llm_base_url or os.environ.get("LLM_BASE_URL")
        self.llm_model    = llm_model
        self.headless     = headless

    def _build_llm(self):
        """بناء LLM client من المفتاح المتاح"""
        if "claude" in self.llm_model.lower() or "anthropic" in (self.llm_base_url or ""):
            try:
                from browser_use.llm.anthropic.chat import ChatAnthropic
            except ImportError:
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "pip", "install",
                               "browser-use", "-q"], check=True)
                from browser_use.llm.anthropic.chat import ChatAnthropic
            return ChatAnthropic(
                model_name=self.llm_model,
                api_key=self.llm_api_key,
            )
        else:
            try:
                from browser_use.llm.openai.like import ChatOpenAILike
            except ImportError:
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "pip", "install",
                               "browser-use", "-q"], check=True)
                from browser_use.llm.openai.like import ChatOpenAILike
            return ChatOpenAILike(
                model=self.llm_model,
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
            )

    async def run_task(
        self,
        task:       str,
        start_url:  str | None = None,
        screenshot: bool = False,
        max_steps:  int = 20,
    ) -> WebResult:
        """
        شغّل مهمة في المتصفح الحقيقي.
        task: ما تريد تنفيذه بلغة طبيعية
        start_url: ابدأ من هذا URL (اختياري)
        screenshot: هل تريد screenshot عند الانتهاء؟
        """
        try:
            try:
                from browser_use import Agent, Browser, BrowserProfile
            except ImportError:
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "pip", "install",
                               "browser-use", "-q"], check=True)
                from browser_use import Agent, Browser, BrowserProfile

            llm     = self._build_llm()
            profile = BrowserProfile(headless=self.headless)
            browser = Browser(browser_profile=profile)

            if start_url:
                task = f"اذهب إلى {start_url} ثم: {task}"

            agent  = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_steps=max_steps,
            )
            result = await agent.run()

            # استخراج المحتوى النهائي
            content = ""
            if result and hasattr(result, "final_result"):
                content = str(result.final_result() or "")
            elif result and hasattr(result, "history"):
                history = result.history
                if history:
                    last = history[-1]
                    content = str(getattr(last, "result", "") or "")

            # screenshot اختياري
            screenshot_b64 = None
            if screenshot and hasattr(agent, "browser") and agent.browser:
                try:
                    session = await agent.browser.get_session()
                    if session and session.page:
                        shot = await session.page.screenshot(type="png")
                        import base64
                        screenshot_b64 = base64.b64encode(shot).decode()
                except Exception:
                    pass

            await browser.close()
            logger.info("ClawBrowser ✅ task=%s (%d chars)", task[:50], len(content))
            return WebResult(
                success=True, content=content,
                url=start_url or "", tool_used="browser",
                screenshot=screenshot_b64,
                metadata={"task": task, "steps": max_steps}
            )

        except Exception as e:
            logger.error("ClawBrowser ❌ %s", e)
            return WebResult(
                success=False, content="", url=start_url or "",
                tool_used="browser", error=str(e)
            )

    def run_task_sync(self, task: str, start_url: str | None = None,
                      screenshot: bool = False, max_steps: int = 20) -> WebResult:
        """نسخة sync من run_task"""
        return asyncio.run(self.run_task(task, start_url, screenshot, max_steps))


# ════════════════════════════════════════════════════════════
# ClawWeb — نقطة الدخول الموحدة
# ════════════════════════════════════════════════════════════

class ClawWeb:
    """
    واجهة موحدة تختار الأداة المناسبة تلقائياً.

    المنهجية التلقائية:
      - طلب بحث/أخبار/مقالات      → ClawCrawl (Markdown جاهز للـ LLM)
      - طلب سريع/موقع عادي         → ClawStealth (HTTP سريع)
      - موقع محمي/تسجيل دخول/JS   → ClawBrowser (متصفح حقيقي)
      - force="stealth/crawl/browser" → يجبر أداة معينة

    مثال:
        web = ClawWeb(crawl_api_key="fc-xxx", llm_api_key="sk-xxx")
        result = web.fetch("https://coindesk.com/bitcoin-news")
        result = web.search("bitcoin price analysis today")
        result = web.interact("اضغط على زر Login وسجّل دخول", "https://binance.com")
    """

    def __init__(
        self,
        crawl_api_key:  str | None = None,
        crawl_base_url: str | None = None,
        llm_api_key:    str | None = None,
        llm_base_url:   str | None = None,
        llm_model:      str = "claude-sonnet-4-6",
        headless:       bool = True,
    ):
        self.stealth = ClawStealth()
        self.crawl   = ClawCrawl(crawl_api_key, crawl_base_url)
        self.browser = ClawBrowser(llm_api_key, llm_base_url, llm_model, headless)

    # ── الاختيار التلقائي ──────────────────────────────────

    def _should_use_crawl(self, url: str) -> bool:
        """هل الموقع يستحق ClawCrawl؟"""
        news_domains = [
            "coindesk", "cointelegraph", "reuters", "bloomberg", "bbc",
            "cnbc", "techcrunch", "github.com", "medium.com", "substack",
            "docs.", "blog.", "news.", "article", "post"
        ]
        return any(d in url.lower() for d in news_domains)

    def _should_use_browser(self, url: str, task: str = "") -> bool:
        """هل يحتاج متصفح حقيقي؟"""
        protected = [
            "cloudflare", "login", "signin", "dashboard", "account",
            "tradingview.com", "binance.com/login", "twitter.com"
        ]
        task_keywords = ["اضغط", "انقر", "سجّل", "ادخل", "افتح", "تفاعل", "screenshot"]
        return (any(d in url.lower() for d in protected) or
                any(k in task for k in task_keywords))

    # ── واجهة رئيسية ───────────────────────────────────────

    def fetch(
        self,
        url:    str,
        force:  str | None = None,   # "stealth" | "crawl" | "browser"
        prompt: str | None = None,
        browser_headless: bool = True,
    ) -> WebResult:
        """
        جلب محتوى URL.
        force: أجبر أداة معينة.
        prompt: إذا حدد مع crawl، يستخرج JSON منظم.
        """
        tool = force or (
            "browser" if self._should_use_browser(url) else
            "crawl"   if self._should_use_crawl(url)   else
            "stealth"
        )

        logger.info("ClawWeb fetch: tool=%s url=%s", tool, url)

        if tool == "crawl":
            return self.crawl.scrape(url, prompt=prompt)
        elif tool == "browser":
            return self.browser.run_task_sync(f"اجلب محتوى الصفحة", start_url=url)
        else:
            result = self.stealth.fetch(url)
            # إذا فشل stealth، جرب crawl
            if not result.success:
                logger.info("ClawStealth فشل، جرب ClawCrawl...")
                result = self.crawl.scrape(url)
            # إذا فشل crawl، جرب browser
            if not result.success:
                logger.info("ClawCrawl فشل، جرب ClawBrowser...")
                result = self.browser.run_task_sync(
                    "اجلب محتوى الصفحة كاملاً", start_url=url
                )
            return result

    def search(
        self,
        query: str,
        limit: int = 5,
        force: str | None = None,
    ) -> list[WebResult]:
        """
        بحث في الويب وأعد المحتوى الكامل.
        يستخدم ClawCrawl افتراضياً لأنه الأفضل للبحث.
        """
        tool = force or "crawl"
        logger.info("ClawWeb search: '%s' tool=%s", query, tool)

        if tool == "crawl":
            return self.crawl.search(query, limit=limit)
        elif tool == "browser":
            result = self.browser.run_task_sync(
                f"ابحث عن: {query} وأعطني ملخصاً شاملاً"
            )
            return [result]
        else:
            # stealth لا يدعم search — fallback لـ crawl
            return self.crawl.search(query, limit=limit)

    def interact(
        self,
        task:      str,
        start_url: str | None = None,
        screenshot: bool = False,
    ) -> WebResult:
        """
        تفاعل مع صفحة ويب: ضغط، كتابة، تسجيل دخول، تمرير.
        يستخدم ClawBrowser دائماً.
        """
        logger.info("ClawWeb interact: task='%s' url=%s", task[:50], start_url)
        return self.browser.run_task_sync(task, start_url, screenshot)

    def crawl_site(
        self,
        url:   str,
        limit: int = 10,
    ) -> list[WebResult]:
        """زحف كامل موقع"""
        return self.crawl.crawl(url, limit=limit)

    def map_site(self, url: str, search: str = "") -> list[str]:
        """اكتشف كل روابط موقع"""
        return self.crawl.map_site(url, search=search)

    def fetch_many(
        self,
        urls:  list[str],
        force: str | None = None,
    ) -> list[WebResult]:
        """جلب قائمة URLs"""
        return [self.fetch(url, force=force) for url in urls]


# ════════════════════════════════════════════════════════════
# دمج مع source_manager.py في CoBWeaverClaw
# ════════════════════════════════════════════════════════════

_claw_web_instance: ClawWeb | None = None


def get_claw_web(
    crawl_api_key: str | None = None,
    llm_api_key:   str | None = None,
) -> ClawWeb:
    """
    Singleton — استخدم هذه الدالة من source_manager.py:

        from claw_web import get_claw_web
        web    = get_claw_web()
        result = web.fetch(url, api_key, secret)
    """
    global _claw_web_instance
    if _claw_web_instance is None:
        _claw_web_instance = ClawWeb(
            crawl_api_key=crawl_api_key or os.environ.get("CLAW_CRAWL_API_KEY"),
            llm_api_key  =llm_api_key   or os.environ.get("LLM_API_KEY"),
        )
    return _claw_web_instance
