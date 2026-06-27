"""
Account Manager — حفظ واستعادة بيانات الحساب + النسخ الاحتياطي.
يضمن عدم فقدان البيانات ويتيح النقل لجهاز آخر.
"""
import os
import json
import tarfile
import shutil
import secrets
from pathlib import Path
from datetime import datetime


class AccountManager:
    """
    يدير حساب المستخدم:
    - account_id ثابت لا يتغيّر (يُسترجع في كل مرة)
    - نسخة احتياطية كاملة قابلة للنقل
    - استعادة على جهاز جديد
    """

    def __init__(self, config_dir: str = None):
        self.config_dir   = Path(config_dir or os.path.expanduser("~/.cobweaverclaw"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.account_file = self.config_dir / "account.json"

    def get_or_create_account(self) -> dict:
        """يُعيد بيانات الحساب أو ينشئ حساباً جديداً ثابتاً."""
        if self.account_file.exists():
            try:
                return json.loads(self.account_file.read_text())
            except Exception:
                pass
        return self._create_account()

    def _create_account(self) -> dict:
        """ينشئ حساباً جديداً بـ account_id ثابت."""
        account = {
            "account_id":  "cbw_" + secrets.token_hex(8),
            "created_at":  datetime.now().isoformat(),
            "device_name": os.uname().nodename if hasattr(os, "uname") else "unknown",
        }
        self.account_file.write_text(json.dumps(account, indent=2, ensure_ascii=False))
        try:
            os.chmod(self.account_file, 0o600)
        except Exception:
            pass
        return account

    def get_account_id(self) -> str:
        """يُرجع account_id الثابت (لا يتغيّر أبداً)."""
        return self.get_or_create_account()["account_id"]

    def create_backup(self, output_path: str = None) -> str:
        """
        ينشئ نسخة احتياطية كاملة (config + account + memory + token).
        يُرجع مسار ملف النسخة (.tar.gz) قابل للنقل لجهاز آخر.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path is None:
            output_path = str(self.config_dir / f"cbw_backup_{timestamp}.tar.gz")

        # الملفات التي تُحفظ في النسخة (كلها في المجلد الآمن)
        items_to_backup = [
            "account.json",
            "gateway_token",
            "memory.db",
            "devices.db",
            "config.yaml",
            ".env",
        ]

        with tarfile.open(output_path, "w:gz") as tar:
            for item in items_to_backup:
                p = self.config_dir / item
                if p.exists():
                    tar.add(p, arcname=f"cobweaverclaw/{item}")
            # احتياط: config.yaml أو .env في مجلد العمل (نسخ قديمة)
            for legacy in ["config.yaml", ".env"]:
                lp = Path(legacy)
                if lp.exists() and not (self.config_dir / legacy).exists():
                    tar.add(lp, arcname=f"cobweaverclaw/{legacy}")

        try:
            os.chmod(output_path, 0o600)
        except Exception:
            pass
        return output_path

    def restore_backup(self, backup_path: str) -> dict:
        """
        يستعيد نسخة احتياطية على الجهاز الحالي.
        يُرجع ملخّص ما تمّت استعادته.
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"ملف النسخة غير موجود: {backup_path}")

        restored = []
        with tarfile.open(backup_path, "r:gz") as tar:
            for member in tar.getmembers():
                # أمان: تجاهل المسارات الخطرة (path traversal)
                if member.name.startswith("/") or ".." in member.name:
                    continue
                if not member.isfile():
                    continue
                # اسم الملف داخل النسخة دائماً تحت cobweaverclaw/
                name = member.name.split("cobweaverclaw/", 1)[-1]
                if not name:
                    continue

                # اقرأ المحتوى من النسخة مباشرة (بدون مجلد مؤقت)
                src = tar.extractfile(member)
                if src is None:
                    continue
                content = src.read()

                # كل الملفات تُستعاد للمجلد الآمن ~/.cobweaverclaw
                if name == "config.yaml":
                    dest = self.config_dir / "config.yaml"
                    restored.append("config.yaml")
                elif name == ".env":
                    dest = self.config_dir / ".env"
                    restored.append(".env (المفاتيح)")
                else:
                    dest = self.config_dir / name
                    restored.append(name)

                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
                try:
                    os.chmod(dest, 0o600)
                except Exception:
                    pass

        return {"restored": restored, "account_id": self.get_account_id()}
