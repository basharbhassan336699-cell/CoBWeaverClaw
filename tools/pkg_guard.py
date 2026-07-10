"""
حارس تثبيت الحِزم — لا يُشغّل pip إلا بموافقة صريحة من المستخدم.

عند حاجة أداة لحزمة غير مثبّتة، تُسجَّل الحزمة كـ«معلّقة» وتُعرَض رسالة
في المحادثة تشرح ما سيُثبَّت. لا يجري أي تثبيت حتى يوافق المستخدم بأمر
/install (أو يرفض بـ /install-no).
"""
from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
from typing import Dict, List, Optional

logger = logging.getLogger("cobweaverclaw.pkg_guard")

# الحِزم المعلّقة بانتظار موافقة المستخدم: {pip_name: import_name}
_PENDING: Dict[str, str] = {}


def available(import_name: str) -> bool:
    """هل الحزمة قابلة للاستيراد الآن؟ (بلا استيراد فعلي)."""
    try:
        return importlib.util.find_spec(import_name) is not None
    except Exception:
        return False


def remember(import_name: str, pip_name: str) -> None:
    """يسجّل حزمة مطلوبة كمعلّقة بانتظار الموافقة."""
    _PENDING[pip_name] = import_name


def pending() -> List[str]:
    """أسماء الحِزم المعلّقة (pip)."""
    return list(_PENDING.keys())


def consent_message() -> str:
    """رسالة تُعرَض للمستخدم تشرح ما سيُثبَّت وكيف يوافق."""
    if not _PENDING:
        return ""
    pkgs = "، ".join(f"`{p}`" for p in _PENDING)
    cmd = "pip install " + " ".join(_PENDING.keys())
    extra = ""
    if "browser-use" in _PENDING:
        extra = ("\nⓘ وضع المتصفح يحتاج أيضاً متصفّح Chromium — بعد الموافقة "
                 "شغّل يدوياً: `playwright install chromium` (حجم كبير).")
    return (f"🔧 لإتمام هذا الطلب أحتاج تثبيت: {pkgs}\n"
            f"سيُشغَّل: `{cmd}`\n"
            f"للموافقة أرسل: `/install`\n"
            f"للرفض أرسل: `/install-no`{extra}")


def approve() -> str:
    """يُثبّت الحِزم المعلّقة فعلياً (بعد موافقة المستخدم)."""
    if not _PENDING:
        return "لا توجد حِزم معلّقة للتثبيت."
    installed, failed = [], []
    for pip_name, import_name in list(_PENDING.items()):
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", pip_name, "-q"],
                           check=True, timeout=600)
            if available(import_name):
                installed.append(pip_name)
                _PENDING.pop(pip_name, None)
            else:
                failed.append(f"{pip_name} (لم يُستورَد بعد التثبيت)")
        except subprocess.TimeoutExpired:
            failed.append(f"{pip_name} (انتهت المهلة)")
        except Exception as e:
            failed.append(f"{pip_name}: {str(e)[:100]}")
    parts = []
    if installed:
        parts.append("✅ تم تثبيت: " + "، ".join(installed) + " — أعد إرسال طلبك.")
    if failed:
        parts.append("❌ فشل: " + "؛ ".join(failed))
    return "\n".join(parts) or "لم يحدث تغيير."


def decline() -> str:
    """يُلغي الحِزم المعلّقة دون تثبيت."""
    if not _PENDING:
        return "لا توجد حِزم معلّقة."
    pkgs = "، ".join(_PENDING.keys())
    _PENDING.clear()
    return f"🚫 أُلغي التثبيت. لن أُثبّت: {pkgs}"


# أوامر الموافقة/الرفض المقبولة
_APPROVE = ("/install", "/install-yes", "/install_yes")
_DECLINE = ("/install-no", "/install_no", "/cancel-install", "/install-cancel")


def handle_command(message: str) -> Optional[str]:
    """يعالج أمر الموافقة/الرفض. يعيد نصّ الردّ، أو None إن لم يكن أمر تثبيت."""
    cmd = (message or "").strip().lower()
    if cmd in _APPROVE:
        return approve()
    if cmd in _DECLINE:
        return decline()
    return None
