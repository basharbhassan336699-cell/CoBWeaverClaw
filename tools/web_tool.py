"""
CoBWeaverClaw — Web Tool
أداة ويب موحدة تُستدعى تلقائياً من الوكيل حسب الطلب
"""
from __future__ import annotations
import logging
import os
from typing import Any

logger = logging.getLogger("cobweaverclaw.web_tool")

# ── Schema للوكيل ──────────────────────────────────────────
WEB_TOOL_SCHEMA = {
    "name": "web_intelligence",
    "description": (
        "أداة ذكاء ويب متكاملة. استخدمها عند أي طلب يتعلق بـ:\n"
        "- جلب محتوى موقع أو صفحة ويب\n"
        "- البحث عن أخبار أو معلومات من الإنترنت\n"
        "- التفاعل مع موقع (تسجيل دخول، ضغط، ملء نموذج)\n"
        "- زحف موقع كامل أو اكتشاف روابطه\n"
        "تختار الأداة المناسبة تلقائياً:\n"
        "  stealth → HTTP سريع يُقلّد Chrome (0.4 ث)\n"
        "  crawl   → Markdown نظيف جاهز للـ LLM (3.4 ث)\n"
        "  browser → متصفح Chromium حقيقي مع AI (5-10 ث)"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["fetch", "search", "interact", "crawl", "map"],
                "description": (
                    "fetch: جلب محتوى URL واحد\n"
                    "search: بحث في الويب بكلمات مفتاحية\n"
                    "interact: تفاعل مع صفحة (ضغط، كتابة، تسجيل دخول)\n"
                    "crawl: زحف موقع كامل\n"
                    "map: اكتشاف كل روابط موقع"
                )
            },
            "url": {
                "type": "string",
                "description": "الرابط المطلوب (مطلوب لـ fetch/interact/crawl/map)"
            },
            "query": {
                "type": "string",
                "description": "كلمات البحث (مطلوب لـ search)"
            },
            "task": {
                "type": "string",
                "description": "وصف ما تريد فعله بلغة طبيعية (لـ interact)"
            },
            "tool": {
                "type": "string",
                "enum": ["auto", "stealth", "crawl", "browser"],
                "description": "أجبر أداة معينة — auto يختار تلقائياً",
                "default": "auto"
            },
            "limit": {
                "type": "integer",
                "description": "عدد النتائج لـ search وعدد الصفحات لـ crawl",
                "default": 5
            },
            "screenshot": {
                "type": "boolean",
                "description": "التقط screenshot بعد التفاعل (لـ interact فقط)",
                "default": False
            },
            "extract_prompt": {
                "type": "string",
                "description": "prompt لاستخراج بيانات منظمة JSON بدل Markdown"
            }
        },
        "required": ["action"]
    }
}


# ── التنفيذ ────────────────────────────────────────────────
def execute_web_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    ينفّذ طلب الويب ويعيد نتيجة منظمة للوكيل.
    يُستدعى من tool dispatcher في الوكيل الرئيسي.
    """
    action  = args.get("action", "fetch")
    url     = args.get("url", "")
    query   = args.get("query", "")
    task    = args.get("task", "")
    tool    = args.get("tool", "auto")
    limit   = int(args.get("limit", 5))
    shot    = bool(args.get("screenshot", False))
    prompt  = args.get("extract_prompt")

    # وضع افتراضي من اللوحة (env) عندما لا يحدّد النموذج أداة صراحةً
    if tool == "auto":
        tool = os.environ.get("WEB_TOOL_MODE", "auto") or "auto"
    force = None if tool == "auto" else tool

    # ── موافقة التثبيت: لا نُشغّل pip دون إذن المستخدم ──
    # نحدّد الحزمة اللازمة لهذا الطلب؛ إن غابت نطلب الموافقة بدل التثبيت الصامت.
    needed = None
    if action in ("search", "crawl", "map"):
        needed = ("firecrawl", "firecrawl-py")
    elif action == "interact":
        needed = ("browser_use", "browser-use")
    elif action == "fetch" and tool == "crawl":
        needed = ("firecrawl", "firecrawl-py")
    elif action == "fetch" and tool == "browser":
        needed = ("browser_use", "browser-use")
    # fetch/auto وstealth يعملان عبر requests بلا أي تثبيت
    if needed:
        try:
            from tools import pkg_guard
            if not pkg_guard.available(needed[0]):
                pkg_guard.remember(needed[0], needed[1])
                return {"success": False, "action": action, "needs_install": True,
                        "packages": [needed[1]], "message": pkg_guard.consent_message()}
        except Exception as e:
            logger.debug("pkg_guard unavailable: %s", e)

    try:
        from claw_web import get_claw_web, WebResult
    except Exception as e:
        logger.error("claw_web غير متوفّر: %s", e)
        return {"success": False, "action": action,
                "error": ("طبقة ذكاء الويب غير مُثبّتة. ثبّت المتطلّبات الاختيارية "
                          "(firecrawl-py / browser-use) وأضف CLAW_CRAWL_API_KEY.")}

    web = get_claw_web(
        crawl_api_key=os.environ.get("CLAW_CRAWL_API_KEY"),
        llm_api_key  =os.environ.get("LLM_API_KEY"),
    )

    try:
        if action == "fetch":
            if not url:
                return {"success": False, "error": "url مطلوب لـ fetch"}
            r = web.fetch(url, force=force, prompt=prompt)
            return _format_result(r)

        elif action == "search":
            if not query:
                return {"success": False, "error": "query مطلوب لـ search"}
            results = web.search(query, limit=limit, force=force)
            ok = [r for r in results if r.success]
            if not ok:
                err = next((r.error for r in results if r.error), None)
                return {"success": False, "action": "search", "query": query,
                        "count": 0, "results": [],
                        "error": err or "لا نتائج (تحقّق من CLAW_CRAWL_API_KEY والتبعيات)"}
            return {
                "success": True,
                "action": "search",
                "query": query,
                "count": len(ok),
                "results": [
                    {
                        "url":     r.url,
                        "content": r.content[:3000],
                        "tool":    r.tool_used,
                    }
                    for r in ok
                ]
            }

        elif action == "interact":
            if not task:
                return {"success": False, "error": "task مطلوب لـ interact"}
            r = web.interact(task, start_url=url or None, screenshot=shot)
            result = _format_result(r)
            if r.screenshot:
                result["screenshot_b64"] = r.screenshot
            return result

        elif action == "crawl":
            if not url:
                return {"success": False, "error": "url مطلوب لـ crawl"}
            pages = web.crawl_site(url, limit=limit)
            ok = [p for p in pages if p.success]
            if not ok:
                err = next((p.error for p in pages if p.error), None)
                return {"success": False, "action": "crawl", "url": url,
                        "pages_count": 0, "pages": [],
                        "error": err or "لا صفحات (تحقّق من CLAW_CRAWL_API_KEY والتبعيات)"}
            return {
                "success": True,
                "action": "crawl",
                "url": url,
                "pages_count": len(ok),
                "pages": [
                    {"url": p.url, "content": p.content[:2000]}
                    for p in ok
                ]
            }

        elif action == "map":
            if not url:
                return {"success": False, "error": "url مطلوب ل_map"}
            links = web.map_site(url, search=query)
            return {
                "success": True,
                "action": "map",
                "url": url,
                "links_count": len(links),
                "links": links[:50]
            }

        else:
            return {"success": False, "error": f"action غير معروف: {action}"}

    except Exception as e:
        logger.error("web_tool error: %s", e)
        return {"success": False, "error": str(e), "action": action}


def _format_result(r) -> dict:
    return {
        "success":   r.success,
        "action":    "fetch",
        "url":       r.url,
        "tool_used": r.tool_used,
        "content":   r.content[:8000] if r.success else "",
        "error":     r.error,
        "metadata":  r.metadata,
    }
