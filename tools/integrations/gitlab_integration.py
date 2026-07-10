"""
CoBWeaverClaw — GitLab Integration
يتصل بـ GitLab API — يدعم gitlab.com والـ self-hosted
"""
from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from urllib.parse import quote
import requests
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("cobweaverclaw.gitlab")


class GitLabIntegration(BaseIntegration):

    name        = "gitlab"
    description = "GitLab — مستودعات، Issues، CI/CD، MRs"

    def _base_url(self) -> str:
        return self.credentials.get("base_url", "https://gitlab.com").rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('token', '')}",
            "Content-Type":  "application/json",
        }

    def _req(self, method: str, path: str, **kwargs) -> requests.Response:
        return requests.request(
            method, f"{self._base_url()}/api/v4{path}",
            headers=self._headers(), timeout=15, **kwargs
        )

    def _encode(self, s: str) -> str:
        return quote(s, safe="")

    def test_connection(self) -> IntegrationResult:
        try:
            r = self._req("GET", "/user")
            if r.ok:
                u = r.json()
                return IntegrationResult(success=True,
                                          data={"username": u["username"],
                                                "name": u["name"]},
                                          message=f"متصل كـ @{u['username']}")
            return IntegrationResult(success=False,
                                      error=f"HTTP {r.status_code}: {r.json().get('message')}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def execute(self, action: str, params: dict) -> IntegrationResult:
        actions = {
            "list_projects":   self._list_projects,
            "get_project":     self._get_project,
            "create_project":  self._create_project,
            "clone_project":   self._clone_project,
            "list_files":      self._list_files,
            "get_file":        self._get_file,
            "create_file":     self._create_file,
            "update_file":     self._update_file,
            "list_issues":     self._list_issues,
            "create_issue":    self._create_issue,
            "list_mrs":        self._list_mrs,
            "create_mr":       self._create_mr,
            "list_branches":   self._list_branches,
            "create_branch":   self._create_branch,
            "list_pipelines":  self._list_pipelines,
            "run_pipeline":    self._run_pipeline,
            "get_commits":     self._get_commits,
        }
        fn = actions.get(action)
        if not fn:
            return IntegrationResult(success=False,
                                      error=f"action غير معروف: {action}")
        return fn(params)

    def _pid(self, p: dict) -> str:
        return self._encode(f"{p['namespace']}/{p['project']}"
                            if "namespace" in p else str(p["project_id"]))

    def _list_projects(self, p: dict) -> IntegrationResult:
        r = self._req("GET", "/projects",
                      params={"membership": True, "per_page": p.get("limit", 20),
                              "order_by": "last_activity_at"})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[{"id": x["id"], "name": x["name"],
                                             "path": x["path_with_namespace"],
                                             "url": x["web_url"]} for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))

    def _get_project(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}")
        return IntegrationResult(success=r.ok, data=r.json() if r.ok else None,
                                  error=None if r.ok else str(r.status_code))

    def _create_project(self, p: dict) -> IntegrationResult:
        r = self._req("POST", "/projects",
                      json={"name": p["name"], "description": p.get("description", ""),
                            "visibility": p.get("visibility", "private"),
                            "initialize_with_readme": True})
        return IntegrationResult(success=r.ok,
                                  data={"url": r.json().get("web_url")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _clone_project(self, p: dict) -> IntegrationResult:
        r   = self._req("GET", f"/projects/{self._pid(p)}")
        if not r.ok:
            return IntegrationResult(success=False, error="المشروع غير موجود")
        url  = r.json()["http_url_to_repo"]
        token = self.credentials.get("token", "")
        if token:
            url = url.replace("https://", f"https://oauth2:{token}@")
        dest = p.get("dest", str(Path.home() / ".cobweaverclaw" / "repos" / r.json()["name"]))
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", str(p.get("depth", 1)), url, dest],
                capture_output=True, text=True, timeout=120
            )
            return IntegrationResult(success=result.returncode == 0,
                                      data={"path": dest} if result.returncode == 0 else None,
                                      error=result.stderr[:300] if result.returncode != 0 else None)
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _list_files(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}/repository/tree",
                      params={"path": p.get("path", ""), "ref": p.get("branch", "main"),
                              "per_page": 100})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[{"name": x["name"], "type": x["type"],
                                             "path": x["path"]} for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))

    def _get_file(self, p: dict) -> IntegrationResult:
        import base64
        r = self._req("GET",
                      f"/projects/{self._pid(p)}/repository/files/{self._encode(p['path'])}",
                      params={"ref": p.get("branch", "main")})
        if r.ok:
            data    = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return IntegrationResult(success=True,
                                      data={"content": content,
                                            "last_commit_id": data.get("last_commit_id")})
        return IntegrationResult(success=False, error=str(r.status_code))

    def _create_file(self, p: dict) -> IntegrationResult:
        r = self._req("POST",
                      f"/projects/{self._pid(p)}/repository/files/{self._encode(p['path'])}",
                      json={"branch": p.get("branch", "main"),
                            "content": p["content"],
                            "commit_message": p.get("message", "إضافة ملف"),
                            "encoding": "text"})
        return IntegrationResult(success=r.ok,
                                  message="تم إنشاء الملف" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _update_file(self, p: dict) -> IntegrationResult:
        r = self._req("PUT",
                      f"/projects/{self._pid(p)}/repository/files/{self._encode(p['path'])}",
                      json={"branch": p.get("branch", "main"),
                            "content": p["content"],
                            "commit_message": p.get("message", "تحديث ملف"),
                            "encoding": "text"})
        return IntegrationResult(success=r.ok,
                                  message="تم التحديث" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _list_issues(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}/issues",
                      params={"state": p.get("state", "opened"),
                              "per_page": p.get("limit", 20)})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[{"iid": x["iid"], "title": x["title"],
                                             "state": x["state"]} for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))

    def _create_issue(self, p: dict) -> IntegrationResult:
        r = self._req("POST", f"/projects/{self._pid(p)}/issues",
                      json={"title": p["title"], "description": p.get("body", ""),
                            "labels": ",".join(p.get("labels", []))})
        return IntegrationResult(success=r.ok,
                                  data={"iid": r.json().get("iid")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _list_mrs(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}/merge_requests",
                      params={"state": p.get("state", "opened"),
                              "per_page": p.get("limit", 20)})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[{"iid": x["iid"], "title": x["title"],
                                             "state": x["state"],
                                             "source": x["source_branch"],
                                             "target": x["target_branch"]} for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))

    def _create_mr(self, p: dict) -> IntegrationResult:
        r = self._req("POST", f"/projects/{self._pid(p)}/merge_requests",
                      json={"title": p["title"], "description": p.get("body", ""),
                            "source_branch": p["source"], "target_branch": p.get("target", "main")})
        return IntegrationResult(success=r.ok,
                                  data={"iid": r.json().get("iid"),
                                        "url": r.json().get("web_url")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _list_branches(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}/repository/branches")
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[x["name"] for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))

    def _create_branch(self, p: dict) -> IntegrationResult:
        r = self._req("POST", f"/projects/{self._pid(p)}/repository/branches",
                      json={"branch": p["branch"], "ref": p.get("from", "main")})
        return IntegrationResult(success=r.ok,
                                  message=f"فرع '{p['branch']}' أُنشئ" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _list_pipelines(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}/pipelines",
                      params={"per_page": p.get("limit", 10)})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[{"id": x["id"], "status": x["status"],
                                             "ref": x["ref"],
                                             "created_at": x["created_at"]} for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))

    def _run_pipeline(self, p: dict) -> IntegrationResult:
        r = self._req("POST", f"/projects/{self._pid(p)}/pipeline",
                      json={"ref": p.get("branch", "main"),
                            "variables": [{"key": k, "value": v}
                                          for k, v in p.get("variables", {}).items()]})
        return IntegrationResult(success=r.ok,
                                  data={"id": r.json().get("id"),
                                        "status": r.json().get("status")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _get_commits(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/projects/{self._pid(p)}/repository/commits",
                      params={"per_page": p.get("limit", 10),
                              "ref_name": p.get("branch", "main")})
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[{"id": x["short_id"], "title": x["title"],
                                             "author": x["author_name"],
                                             "date": x["created_at"]} for x in r.json()])
        return IntegrationResult(success=False, error=str(r.status_code))
