"""
CoBWeaverClaw — Integration Base
القاعدة التي ترث منها كل عمليات الاتصال بالمواقع والتطبيقات
"""
from __future__ import annotations
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("cobweaverclaw.integrations")

INTEGRATIONS_DIR = Path.home() / ".cobweaverclaw" / "integrations"


@dataclass
class IntegrationResult:
    success:  bool
    data:     Any           = None
    message:  str           = ""
    error:    Optional[str] = None
    metadata: dict          = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success":  self.success,
            "data":     self.data,
            "message":  self.message,
            "error":    self.error,
            "metadata": self.metadata,
        }


class BaseIntegration(ABC):
    """القاعدة لكل integration"""

    name:        str = ""
    description: str = ""

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or self._load_credentials()

    def _creds_path(self) -> Path:
        return INTEGRATIONS_DIR / f"{self.name}.json"

    def _load_credentials(self) -> dict:
        path = self._creds_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def save_credentials(self, creds: dict) -> None:
        INTEGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._creds_path().write_text(
            json.dumps(creds, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        self.credentials = creds
        logger.info("%s: credentials saved", self.name)

    def is_configured(self) -> bool:
        return bool(self.credentials)

    @abstractmethod
    def test_connection(self) -> IntegrationResult:
        """اختبر الاتصال وتحقق من صحة البيانات"""
        ...

    @abstractmethod
    def execute(self, action: str, params: dict) -> IntegrationResult:
        """نفّذ أمراً على الخدمة"""
        ...
