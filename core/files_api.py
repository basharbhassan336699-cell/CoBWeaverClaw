"""
Files API — استقبال مرفقات لوحة التحكم وحفظها.
يحفظ في ~/.cobweaverclaw/uploads/ باسم موقوت، ويستخرج نص الملفات
النصية لحقنها في سياق المحادثة. حد الحجم 10MB للملف الواحد.
"""
from __future__ import annotations

import base64
import datetime
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path.home() / ".cobweaverclaw" / "uploads"
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB

# امتدادات تُقرأ نصاً وتُحقن في سياق النموذج
_TEXT_EXTS = {
    "txt", "md", "markdown", "csv", "json", "yaml", "yml", "xml", "html",
    "py", "js", "ts", "jsx", "tsx", "cpp", "c", "h", "hpp", "java", "go",
    "rs", "rb", "php", "sh", "bash", "sql", "toml", "ini", "cfg", "log",
}
_TEXT_INJECT_LIMIT = 12000  # حرف لكل ملف داخل السياق


def _safe_name(name: str) -> str:
    """اسم ملف آمن (يمنع اجتياز المسارات) مع الإبقاء على العربية."""
    name = (name or "file").replace("\\", "/").split("/")[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip(". ") or "file"
    return name[:120]


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def save_attachments(attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """يفكّ base64 ويحفظ كل مرفق باسم موقوت. يعيد قائمة نتائج لكل ملف.

    كل نتيجة: {name, path, size, type, saved, error?, text?}
    text يُملأ للملفات النصية (لحقنها في سياق النموذج).
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    out: List[Dict[str, Any]] = []
    for att in attachments or []:
        if not isinstance(att, dict):
            continue
        name = _safe_name(str(att.get("name", "file")))
        rec: Dict[str, Any] = {"name": name, "type": str(att.get("type", "")),
                               "saved": False, "path": None,
                               "size": int(att.get("size") or 0)}
        try:
            raw_b64 = str(att.get("data", ""))
            # اقبل صيغة data URL أيضاً
            if "," in raw_b64 and raw_b64.lstrip().startswith("data:"):
                raw_b64 = raw_b64.split(",", 1)[1]
            blob = base64.b64decode(raw_b64, validate=False)
            rec["size"] = len(blob)
            if len(blob) > MAX_FILE_BYTES:
                rec["error"] = "الملف يتجاوز الحد الأقصى 10MB"
                out.append(rec)
                continue
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = UPLOADS_DIR / f"{ts}_{name}"
            i = 1
            while dest.exists():
                dest = UPLOADS_DIR / f"{ts}_{i}_{name}"
                i += 1
            dest.write_bytes(blob)
            rec["saved"] = True
            rec["path"] = str(dest)
            if _ext(name) in _TEXT_EXTS:
                try:
                    rec["text"] = blob.decode("utf-8", errors="replace")[:_TEXT_INJECT_LIMIT]
                except Exception:
                    pass
            logger.info("Attachment saved: %s (%d bytes)", dest.name, len(blob))
        except Exception as e:
            rec["error"] = f"فشل الحفظ: {str(e)[:80]}"
        out.append(rec)
    return out


def build_context_block(saved: List[Dict[str, Any]]) -> str:
    """يبني كتلة نصية عن المرفقات تُلحق برسالة المستخدم للنموذج."""
    if not saved:
        return ""
    parts = ["\n\n[مرفقات المستخدم مع هذه الرسالة]"]
    for r in saved:
        size_kb = round((r.get("size") or 0) / 1024, 1)
        head = f"• {r['name']} ({r.get('type') or 'ملف'}, {size_kb}KB)"
        if not r.get("saved"):
            parts.append(head + f" — لم يُحفظ: {r.get('error', '?')}")
            continue
        if r.get("text"):
            parts.append(head + " — المحتوى:\n```\n" + r["text"] + "\n```")
        else:
            parts.append(head + f" — حُفظ في {r['path']} (ملف ثنائي؛ صفه للمستخدم "
                                "واذكر أنه محفوظ لديه)")
    return "\n".join(parts)


def upload_files(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """معالج POST /api/files/upload — {files: [{name,type,size,data}]}"""
    files = (data or {}).get("files") or []
    if not files:
        return {"success": False, "error": "لا ملفات في الطلب"}, 400
    saved = save_attachments(files)
    return {"success": True,
            "files": [{k: r.get(k) for k in ("name", "path", "size", "saved", "error")}
                      for r in saved]}, 200
