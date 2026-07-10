"""
CoBWeaverClaw — Canva Integration
يتصل بـ Canva Connect API لإنشاء وتعديل التصاميم
"""
from __future__ import annotations
import logging
import requests
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("cobweaverclaw.canva")

CANVA_API = "https://api.canva.com/rest/v1"


class CanvaIntegration(BaseIntegration):

    name        = "canva"
    description = "Canva — إنشاء تصاميم، تصدير، إدارة assets"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('access_token', '')}",
            "Content-Type":  "application/json",
        }

    def _req(self, method: str, path: str, **kwargs) -> requests.Response:
        return requests.request(
            method, f"{CANVA_API}{path}",
            headers=self._headers(), timeout=30, **kwargs
        )

    def test_connection(self) -> IntegrationResult:
        try:
            r = self._req("GET", "/users/me")
            if r.ok:
                u = r.json()
                return IntegrationResult(success=True,
                                          data=u,
                                          message=f"متصل بـ Canva")
            return IntegrationResult(success=False,
                                      error=f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def execute(self, action: str, params: dict) -> IntegrationResult:
        actions = {
            "list_designs":    self._list_designs,
            "get_design":      self._get_design,
            "create_design":   self._create_design,
            "export_design":   self._export_design,
            "list_assets":     self._list_assets,
            "upload_asset":    self._upload_asset,
            "list_folders":    self._list_folders,
            "create_folder":   self._create_folder,
            "list_templates":  self._list_templates,
            "autofill_design": self._autofill_design,
        }
        fn = actions.get(action)
        if not fn:
            return IntegrationResult(success=False,
                                      error=f"action غير معروف: {action}. المتاح: {list(actions)}")
        return fn(params)

    def _list_designs(self, p: dict) -> IntegrationResult:
        params = {"limit": p.get("limit", 20)}
        if p.get("query"):
            params["query"] = p["query"]
        if p.get("type"):
            params["type"] = p["type"]
        r = self._req("GET", "/designs", params=params)
        if r.ok:
            data = r.json()
            designs = [{"id": x["id"], "title": x.get("title", ""),
                        "url": x.get("urls", {}).get("edit_url", ""),
                        "thumbnail": x.get("thumbnail", {}).get("url", ""),
                        "created_at": x.get("created_at")}
                       for x in data.get("items", [])]
            return IntegrationResult(success=True, data=designs,
                                      message=f"{len(designs)} تصميم")
        return IntegrationResult(success=False, error=f"HTTP {r.status_code}: {r.text[:200]}")

    def _get_design(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/designs/{p['design_id']}")
        return IntegrationResult(success=r.ok, data=r.json() if r.ok else None,
                                  error=None if r.ok else r.text[:200])

    def _create_design(self, p: dict) -> IntegrationResult:
        body: dict = {}
        if p.get("design_type"):
            body["design_type"] = {"type": p["design_type"]}
        elif p.get("width") and p.get("height"):
            body["design_type"] = {
                "type": "custom",
                "width": p["width"],
                "height": p["height"],
                "units": p.get("units", "px")
            }
        if p.get("title"):
            body["title"] = p["title"]
        r = self._req("POST", "/designs", json=body)
        if r.ok:
            data = r.json().get("design", {})
            return IntegrationResult(success=True,
                                      data={"id": data.get("id"),
                                            "url": data.get("urls", {}).get("edit_url", "")},
                                      message=f"تصميم أُنشئ: {data.get('id')}")
        return IntegrationResult(success=False, error=r.text[:200])

    def _export_design(self, p: dict) -> IntegrationResult:
        # ابدأ job التصدير
        r = self._req("POST", "/exports",
                      json={"design_id": p["design_id"],
                            "format": {
                                "type": p.get("format", "pdf"),
                                **({} if p.get("format", "pdf") == "pdf"
                                   else {"quality": p.get("quality", "regular")})
                            }})
        if not r.ok:
            return IntegrationResult(success=False, error=r.text[:200])
        job_id = r.json().get("job", {}).get("id")
        # انتظر اكتمال التصدير
        import time
        for _ in range(30):
            time.sleep(2)
            status_r = self._req("GET", f"/exports/{job_id}")
            if status_r.ok:
                job = status_r.json().get("job", {})
                if job.get("status") == "success":
                    urls = [u["url"] for u in job.get("urls", [])]
                    return IntegrationResult(success=True, data={"urls": urls},
                                              message=f"تم التصدير: {len(urls)} ملف")
                elif job.get("status") == "failed":
                    return IntegrationResult(success=False, error="فشل التصدير")
        return IntegrationResult(success=False, error="انتهت مهلة التصدير")

    def _list_assets(self, p: dict) -> IntegrationResult:
        r = self._req("GET", "/assets",
                      params={"limit": p.get("limit", 20),
                              "type": p.get("type", "")})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=r.json().get("items", []))
        return IntegrationResult(success=False, error=r.text[:200])

    def _upload_asset(self, p: dict) -> IntegrationResult:
        import base64
        file_path = p.get("file_path", "")
        if not file_path:
            return IntegrationResult(success=False, error="file_path مطلوب")
        from pathlib import Path as P
        path = P(file_path)
        if not path.exists():
            return IntegrationResult(success=False, error=f"الملف غير موجود: {file_path}")
        with open(path, "rb") as f:
            data = f.read()
        r = requests.post(
            f"{CANVA_API}/assets/upload",
            headers={**self._headers(),
                     "Content-Type": "application/octet-stream",
                     "Asset-Name": p.get("name", path.name)},
            data=data, timeout=60
        )
        return IntegrationResult(success=r.ok,
                                  data=r.json() if r.ok else None,
                                  error=None if r.ok else r.text[:200])

    def _list_folders(self, p: dict) -> IntegrationResult:
        r = self._req("GET", "/folders",
                      params={"limit": p.get("limit", 20)})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=r.json().get("items", []))
        return IntegrationResult(success=False, error=r.text[:200])

    def _create_folder(self, p: dict) -> IntegrationResult:
        r = self._req("POST", "/folders",
                      json={"name": p["name"],
                            "parent_folder_id": p.get("parent_id", "root")})
        return IntegrationResult(success=r.ok,
                                  data=r.json() if r.ok else None,
                                  error=None if r.ok else r.text[:200])

    def _list_templates(self, p: dict) -> IntegrationResult:
        params = {"limit": p.get("limit", 20)}
        if p.get("query"):
            params["query"] = p["query"]
        r = self._req("GET", "/design-templates", params=params)
        if r.ok:
            return IntegrationResult(success=True,
                                      data=r.json().get("items", []))
        return IntegrationResult(success=False, error=r.text[:200])

    def _autofill_design(self, p: dict) -> IntegrationResult:
        r = self._req("POST", "/autofills",
                      json={"brand_template_id": p["template_id"],
                            "title": p.get("title", ""),
                            "data": p.get("data", {})})
        if r.ok:
            job_id = r.json().get("job", {}).get("id")
            import time
            for _ in range(30):
                time.sleep(2)
                s = self._req("GET", f"/autofills/{job_id}")
                if s.ok:
                    job = s.json().get("job", {})
                    if job.get("status") == "success":
                        design = job.get("result", {}).get("design", {})
                        return IntegrationResult(success=True,
                                                  data={"id": design.get("id"),
                                                        "url": design.get("urls", {}).get("edit_url")},
                                                  message="تم autofill")
                    elif job.get("status") == "failed":
                        return IntegrationResult(success=False, error="فشل autofill")
        return IntegrationResult(success=False, error=r.text[:200])
