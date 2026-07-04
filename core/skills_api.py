"""
Skills API — مهارات SKILL.md من الجهاز.

المهارة ملف SKILL.md بهيكل صارم:
---
name: اسم-المهارة
version: 1
description: وصف قصير
tags: [tag1, tag2]
domain: general|trading|academic|technical
---
# اسم المهارة
## متى تستخدم هذه المهارة
## الخطوات
## مثال

تُحفظ في ~/.cobweaverclaw/skills/<name>/SKILL.md مع skill.json للـmetadata.
"""
from __future__ import annotations

import datetime
import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

SKILLS_DIR = Path.home() / ".cobweaverclaw" / "skills"
DOMAINS = ("general", "trading", "academic", "technical")
REQUIRED_FM = ("name", "version", "description", "tags", "domain")
REQUIRED_HEADINGS = ("## متى تستخدم هذه المهارة", "## الخطوات", "## مثال")


# ── التحليل والتحقق ───────────────────────────────────────────
def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """يفصل frontmatter عن الجسم. يعيد (meta, body) — meta فارغ إن غاب."""
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)$", content or "", re.DOTALL)
    if not m:
        return {}, content or ""
    meta: Dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k == "tags":
            v = [t.strip() for t in v.strip("[]").split(",") if t.strip()]
        meta[k] = v
    return meta, m.group(2)


def validate_skill(content: str) -> Tuple[Dict[str, Any], List[str]]:
    """يتحقق من الهيكل الصارم. يعيد (meta, أخطاء واضحة بالحقل الناقص)."""
    errors: List[str] = []
    meta, body = parse_frontmatter(content)
    if not meta:
        return {}, ["frontmatter مفقود — الملف يجب أن يبدأ بـ --- ثم الحقول ثم ---"]
    for f in REQUIRED_FM:
        if f not in meta or (isinstance(meta[f], str) and not meta[f]) \
           or (isinstance(meta[f], list) and not meta[f]):
            errors.append(f"حقل frontmatter ناقص: {f}")
    if meta.get("domain") and meta["domain"] not in DOMAINS:
        errors.append(f"domain غير صالح: '{meta['domain']}' — المسموح: {'|'.join(DOMAINS)}")
    if meta.get("version") and not str(meta["version"]).isdigit():
        errors.append("version يجب أن يكون رقماً")
    if not re.search(r"^# .+", body, re.MULTILINE):
        errors.append("العنوان الرئيسي مفقود: سطر يبدأ بـ '# اسم المهارة'")
    for h in REQUIRED_HEADINGS:
        if h not in body:
            errors.append(f"قسم مطلوب مفقود: '{h}'")
    return meta, errors


def _safe_skill_name(name: str) -> str:
    name = re.sub(r"[^\w؀-ۿ-]", "-", str(name or "").strip())
    return re.sub(r"-{2,}", "-", name).strip("-")[:60]


# ── العمليات ─────────────────────────────────────────────────
def list_user_skills() -> List[Dict[str, Any]]:
    """قائمة المهارات المثبتة من ~/.cobweaverclaw/skills/*/skill.json"""
    out = []
    if not SKILLS_DIR.exists():
        return out
    for d in sorted(SKILLS_DIR.iterdir()):
        meta_file = d / "skill.json"
        if not d.is_dir() or not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            meta["name"] = meta.get("name") or d.name
            out.append(meta)
        except Exception:
            continue
    return out


def _save(meta: Dict[str, Any], content: str) -> Tuple[Dict[str, Any], int]:
    name = _safe_skill_name(meta.get("name", ""))
    if not name:
        return {"success": False, "error": "اسم المهارة غير صالح"}, 400
    d = SKILLS_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")
    record = {
        "name": name,
        "version": str(meta.get("version", "1")),
        "description": str(meta.get("description", ""))[:200],
        "tags": meta.get("tags") if isinstance(meta.get("tags"), list)
                else [t.strip() for t in str(meta.get("tags", "")).split(",") if t.strip()],
        "domain": meta.get("domain", "general"),
        "added_at": int(time.time()),
        "added_date": datetime.date.today().isoformat(),
    }
    (d / "skill.json").write_text(json.dumps(record, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    logger.info("Skill saved: %s (v%s, %s)", name, record["version"], record["domain"])
    return {"success": True, "skill": record}, 200


def upload_skill(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """POST /api/skills/upload — {filename, content} — تحقق صارم قبل الحفظ."""
    data = data or {}
    filename = str(data.get("filename", ""))
    content = str(data.get("content", ""))
    if not filename.lower().endswith(".md"):
        return {"success": False, "error": "يُقبل ملف .md فقط"}, 400
    if not content.strip():
        return {"success": False, "error": "الملف فارغ"}, 400
    meta, errors = validate_skill(content)
    if errors:
        return {"success": False, "error": "هيكل SKILL.md غير صحيح",
                "missing": errors}, 400
    return _save(meta, content)


def create_skill(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """POST /api/skills/create — يولّد SKILL.md بالهيكل الصحيح تلقائياً."""
    data = data or {}
    name = _safe_skill_name(data.get("name", ""))
    desc = str(data.get("description", "")).strip()
    domain = str(data.get("domain", "general")).strip() or "general"
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    body = str(data.get("content", "")).strip()

    missing = []
    if not name:
        missing.append("الاسم")
    if not desc:
        missing.append("الوصف")
    if domain not in DOMAINS:
        missing.append(f"التوجه (المسموح: {'|'.join(DOMAINS)})")
    if missing:
        return {"success": False, "error": "حقول ناقصة: " + "، ".join(missing)}, 400

    # ابنِ الجسم بالهيكل الصارم — أكمل الأقسام الغائبة
    if not re.search(r"^# .+", body, re.MULTILINE):
        body = f"# {name}\n" + body
    for h in REQUIRED_HEADINGS:
        if h not in body:
            body += f"\n\n{h}\n-"
    content = ("---\n"
               f"name: {name}\n"
               "version: 1\n"
               f"description: {desc}\n"
               f"tags: [{', '.join(tags)}]\n"
               f"domain: {domain}\n"
               "---\n" + body.strip() + "\n")

    meta, errors = validate_skill(content)
    if errors:  # لا يفترض أن يحدث — الهيكل مولّد
        return {"success": False, "error": "فشل توليد الهيكل", "missing": errors}, 500
    return _save(meta, content)


def delete_skill(name: str) -> Tuple[Dict[str, Any], int]:
    """DELETE /api/skills/<name>"""
    safe = _safe_skill_name(name)
    d = SKILLS_DIR / safe
    if not safe or not d.is_dir() or not (d / "skill.json").exists():
        return {"success": False, "error": "المهارة غير موجودة"}, 404
    shutil.rmtree(d, ignore_errors=True)
    logger.info("Skill deleted: %s", safe)
    return {"success": True}, 200
