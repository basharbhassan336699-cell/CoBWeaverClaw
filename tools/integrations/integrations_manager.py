"""
CoBWeaverClaw — Integrations Manager
نقطة التحكم الموحدة لكل عمليات الاتصال
"""
from __future__ import annotations
import json
import logging
from typing import Any
from .base import IntegrationResult, INTEGRATIONS_DIR
from .github_integration import GitHubIntegration
from .gitlab_integration import GitLabIntegration
from .canva_integration  import CanvaIntegration
from .colab_integration  import ColabIntegration

logger = logging.getLogger("cobweaverclaw.integrations_manager")

AVAILABLE = {
    "github": GitHubIntegration,
    "gitlab": GitLabIntegration,
    "canva":  CanvaIntegration,
    "colab":  ColabIntegration,
}

# Schema للوكيل
INTEGRATIONS_TOOL_SCHEMA = {
    "name": "integrations",
    "description": (
        "اتصل بمواقع وتطبيقات خارجية ونفّذ عمليات حقيقية:\n"
        "- github: مستودعات، ملفات، Issues، PRs، Branches، Actions\n"
        "- gitlab: مشاريع، MRs، CI/CD Pipelines\n"
        "- canva: إنشاء تصاميم، تصدير، assets\n"
        "- colab: notebooks، Google Drive\n"
        "استخدم هذه الأداة عند أي طلب يذكر هذه الخدمات."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "enum": list(AVAILABLE.keys()),
                "description": "الخدمة المطلوبة"
            },
            "action": {
                "type": "string",
                "description": "العملية المطلوبة (تختلف حسب الخدمة)"
            },
            "params": {
                "type": "object",
                "description": "معاملات العملية"
            },
            "save_credentials": {
                "type": "object",
                "description": "بيانات الاتصال لحفظها (token, api_key, ...)"
            },
            "test_connection": {
                "type": "boolean",
                "description": "اختبر الاتصال فقط بدون تنفيذ عملية",
                "default": False
            }
        },
        "required": ["service"]
    }
}


def execute_integration(args: dict[str, Any]) -> dict:
    service    = args.get("service", "")
    action     = args.get("action", "")
    params     = args.get("params", {})
    save_creds = args.get("save_credentials")
    test_only  = args.get("test_connection", False)

    cls = AVAILABLE.get(service)
    if not cls:
        return {"success": False,
                "error": f"خدمة غير معروفة: {service}. المتاح: {list(AVAILABLE)}"}

    integration = cls()

    # حفظ بيانات الاتصال إذا أُرسلت
    if save_creds:
        integration.save_credentials(save_creds)

    # اختبار الاتصال
    if test_only or not action:
        result = integration.test_connection()
        return result.to_dict()

    # تحقق من وجود بيانات اتصال
    if not integration.is_configured():
        return {
            "success": False,
            "error": (
                f"{service}: لا توجد بيانات اتصال محفوظة.\n"
                f"أرسل save_credentials مع token/api_key أولاً."
            )
        }

    result = integration.execute(action, params)
    return result.to_dict()


def list_integrations() -> dict:
    """قائمة الخدمات وحالة اتصالها"""
    status = {}
    for name, cls in AVAILABLE.items():
        integration = cls()
        status[name] = {
            "description": integration.description,
            "configured":  integration.is_configured(),
        }
    return status
