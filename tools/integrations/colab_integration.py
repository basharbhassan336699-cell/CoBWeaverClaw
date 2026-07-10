"""
CoBWeaverClaw — Google Colab Integration
يتصل بـ Google Colab عبر Google Drive API وColab API
"""
from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Any
import requests
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("cobweaverclaw.colab")

DRIVE_API  = "https://www.googleapis.com/drive/v3"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
COLAB_API  = "https://colab.research.google.com/api"


class ColabIntegration(BaseIntegration):

    name        = "colab"
    description = "Google Colab — إنشاء وتشغيل notebooks، ربط Google Drive"
    ENV_CREDENTIALS = {"access_token": "GOOGLE_ACCESS_TOKEN"}

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
            "Content-Type":  "application/json",
        }

    def _drive_req(self, method: str, path: str, **kwargs) -> requests.Response:
        return requests.request(
            method, f"{DRIVE_API}{path}",
            headers=self._headers(), timeout=30, **kwargs
        )

    def test_connection(self) -> IntegrationResult:
        try:
            r = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers=self._headers(), timeout=8
            )
            if r.ok:
                u = r.json()
                return IntegrationResult(success=True,
                                          data={"email": u.get("email"),
                                                "name": u.get("name")},
                                          message=f"متصل كـ {u.get('email')}")
            return IntegrationResult(success=False,
                                      error=f"HTTP {r.status_code}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def execute(self, action: str, params: dict) -> IntegrationResult:
        actions = {
            "list_notebooks":    self._list_notebooks,
            "get_notebook":      self._get_notebook,
            "create_notebook":   self._create_notebook,
            "update_notebook":   self._update_notebook,
            "add_cell":          self._add_cell,
            "run_notebook":      self._run_notebook,
            "upload_to_drive":   self._upload_to_drive,
            "list_drive_files":  self._list_drive_files,
            "download_from_drive": self._download_from_drive,
            "share_notebook":    self._share_notebook,
        }
        fn = actions.get(action)
        if not fn:
            return IntegrationResult(success=False,
                                      error=f"action غير معروف: {action}. المتاح: {list(actions)}")
        return fn(params)

    def _list_notebooks(self, p: dict) -> IntegrationResult:
        r = self._drive_req("GET", "/files", params={
            "q": "mimeType='application/vnd.google.colaboratory'",
            "fields": "files(id,name,webViewLink,modifiedTime)",
            "pageSize": p.get("limit", 20),
        })
        if r.ok:
            files = r.json().get("files", [])
            return IntegrationResult(success=True, data=files,
                                      message=f"{len(files)} notebook")
        return IntegrationResult(success=False,
                                  error=f"HTTP {r.status_code}: {r.text[:200]}")

    def _get_notebook(self, p: dict) -> IntegrationResult:
        r = self._drive_req("GET", f"/files/{p['file_id']}/export",
                             params={"mimeType": "application/json"})
        if r.ok:
            return IntegrationResult(success=True, data=r.json())
        # fallback: تحميل عادي
        r2 = self._drive_req("GET", f"/files/{p['file_id']}",
                              params={"alt": "media"})
        return IntegrationResult(success=r2.ok,
                                  data=r2.json() if r2.ok else None,
                                  error=None if r2.ok else r2.text[:200])

    def _create_notebook(self, p: dict) -> IntegrationResult:
        """إنشاء notebook جديد في Colab"""
        cells = p.get("cells", [])
        nb_content = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.10.0"},
                "colab": {"provenance": []}
            },
            "cells": [
                {
                    "cell_type": cell.get("type", "code"),
                    "metadata": {},
                    "source": cell.get("source", ""),
                    "outputs": [],
                    "execution_count": None,
                }
                for cell in cells
            ] if cells else [
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": f"# {p.get('title', 'CoBWeaverClaw Notebook')}\n",
                    "outputs": [],
                    "execution_count": None,
                }
            ]
        }
        # رفع لـ Drive كـ Colab notebook
        metadata = {
            "name": p.get("title", "CoBWeaverClaw Notebook") + ".ipynb",
            "mimeType": "application/vnd.google.colaboratory",
            "parents": [p["folder_id"]] if p.get("folder_id") else [],
        }
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={"Authorization": f"Bearer {self.credentials.get('access_token', '')}"},
            files={
                "metadata": (None, json.dumps(metadata), "application/json"),
                "file": (None, json.dumps(nb_content), "application/json"),
            },
            timeout=30,
        )
        if r.ok:
            data = r.json()
            return IntegrationResult(success=True,
                                      data={"id": data["id"],
                                            "url": f"https://colab.research.google.com/drive/{data['id']}"},
                                      message=f"Notebook أُنشئ: {data['id']}")
        return IntegrationResult(success=False, error=r.text[:300])

    def _update_notebook(self, p: dict) -> IntegrationResult:
        """تحديث محتوى notebook"""
        r = self._drive_req("PATCH", f"/files/{p['file_id']}",
                             json={"name": p.get("title", "")})
        return IntegrationResult(success=r.ok,
                                  message="تم التحديث" if r.ok else "",
                                  error=None if r.ok else r.text[:200])

    def _add_cell(self, p: dict) -> IntegrationResult:
        """أضف خلية لـ notebook موجود"""
        # احصل على الـ notebook الحالي
        get_result = self._get_notebook({"file_id": p["file_id"]})
        if not get_result.success:
            return get_result
        nb = get_result.data
        new_cell = {
            "cell_type": p.get("cell_type", "code"),
            "metadata": {},
            "source": p["source"],
            "outputs": [],
            "execution_count": None,
        }
        if p.get("position") is not None:
            nb["cells"].insert(p["position"], new_cell)
        else:
            nb["cells"].append(new_cell)
        # رفع المحتوى المحدث
        r = requests.patch(
            f"https://www.googleapis.com/upload/drive/v3/files/{p['file_id']}?uploadType=media",
            headers={**self._headers(), "Content-Type": "application/json"},
            data=json.dumps(nb).encode(),
            timeout=30,
        )
        return IntegrationResult(success=r.ok,
                                  message="تمت إضافة الخلية" if r.ok else "",
                                  error=None if r.ok else r.text[:200])

    def _run_notebook(self, p: dict) -> IntegrationResult:
        """
        تشغيل notebook — يفتح رابط Colab للتشغيل اليدوي
        أو يستخدم Colab API إذا كان متاحاً
        """
        file_id  = p.get("file_id", "")
        colab_url = f"https://colab.research.google.com/drive/{file_id}"
        return IntegrationResult(
            success=True,
            data={"colab_url": colab_url, "file_id": file_id},
            message=f"افتح هذا الرابط لتشغيل الـ notebook: {colab_url}\n"
                    "ملاحظة: التشغيل التلقائي عبر API يحتاج Colab Pro"
        )

    def _upload_to_drive(self, p: dict) -> IntegrationResult:
        file_path = p.get("file_path", "")
        path      = Path(file_path)
        if not path.exists():
            return IntegrationResult(success=False,
                                      error=f"الملف غير موجود: {file_path}")
        import mimetypes
        mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        metadata = {
            "name": p.get("name", path.name),
            "parents": [p["folder_id"]] if p.get("folder_id") else [],
        }
        with open(path, "rb") as f:
            r = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token', '')}"},
                files={"metadata": (None, json.dumps(metadata), "application/json"),
                       "file":     (None, f, mime)},
                timeout=120,
            )
        return IntegrationResult(success=r.ok,
                                  data={"id": r.json().get("id"),
                                        "name": r.json().get("name")} if r.ok else None,
                                  error=None if r.ok else r.text[:200])

    def _list_drive_files(self, p: dict) -> IntegrationResult:
        query = p.get("query", "")
        if p.get("folder_id"):
            query = f"'{p['folder_id']}' in parents" + (f" and {query}" if query else "")
        r = self._drive_req("GET", "/files", params={
            "q": query or "trashed=false",
            "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink)",
            "pageSize": p.get("limit", 30),
        })
        if r.ok:
            return IntegrationResult(success=True,
                                      data=r.json().get("files", []))
        return IntegrationResult(success=False, error=r.text[:200])

    def _download_from_drive(self, p: dict) -> IntegrationResult:
        dest = p.get("dest", str(Path.home() / ".cobweaverclaw" / "downloads"))
        Path(dest).mkdir(parents=True, exist_ok=True)
        # احصل على اسم الملف
        meta_r = self._drive_req("GET", f"/files/{p['file_id']}",
                                  params={"fields": "name,mimeType"})
        if not meta_r.ok:
            return IntegrationResult(success=False, error="لم يُعثر على الملف")
        name      = meta_r.json()["name"]
        file_path = Path(dest) / name
        r = self._drive_req("GET", f"/files/{p['file_id']}",
                             params={"alt": "media"}, stream=True)
        if r.ok:
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return IntegrationResult(success=True,
                                      data={"path": str(file_path), "name": name},
                                      message=f"تم تحميل: {name}")
        return IntegrationResult(success=False, error=r.text[:200])

    def _share_notebook(self, p: dict) -> IntegrationResult:
        r = self._drive_req("POST",
                             f"/files/{p['file_id']}/permissions",
                             json={"role": p.get("role", "reader"),
                                   "type": p.get("type", "anyone")})
        return IntegrationResult(success=r.ok,
                                  message="تم المشاركة" if r.ok else "",
                                  error=None if r.ok else r.text[:200])
