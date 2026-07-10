"""
CoBWeaverClaw — GitHub Integration
يتصل بـ GitHub API ويعمل على المستودعات بدقة كاملة
"""
from __future__ import annotations
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import requests
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("cobweaverclaw.github")

GITHUB_API = "https://api.github.com"


class GitHubIntegration(BaseIntegration):

    name        = "github"
    description = "GitHub — إدارة المستودعات والكود والـ Issues والـ PRs"
    ENV_CREDENTIALS = {"token": "GITHUB_TOKEN"}

    def _headers(self) -> dict:
        token = self.credentials.get("token") or os.environ.get("GITHUB_TOKEN", "")
        return {
            "Authorization": f"Bearer {token}",
            "Accept":        "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def test_connection(self) -> IntegrationResult:
        try:
            r = requests.get(f"{GITHUB_API}/user", headers=self._headers(), timeout=8)
            if r.status_code == 200:
                user = r.json()
                return IntegrationResult(
                    success=True,
                    data={"login": user["login"], "name": user.get("name"),
                          "public_repos": user.get("public_repos")},
                    message=f"متصل كـ @{user['login']}"
                )
            return IntegrationResult(success=False,
                                     error=f"HTTP {r.status_code}: {r.json().get('message')}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def execute(self, action: str, params: dict) -> IntegrationResult:
        actions = {
            "get_user":          self._get_user,
            "list_repos":        self._list_repos,
            "get_repo":          self._get_repo,
            "create_repo":       self._create_repo,
            "clone_repo":        self._clone_repo,
            "list_files":        self._list_files,
            "get_file":          self._get_file,
            "create_file":       self._create_file,
            "update_file":       self._update_file,
            "delete_file":       self._delete_file,
            "list_issues":       self._list_issues,
            "create_issue":      self._create_issue,
            "close_issue":       self._close_issue,
            "list_prs":          self._list_prs,
            "create_pr":         self._create_pr,
            "merge_pr":          self._merge_pr,
            "list_branches":     self._list_branches,
            "create_branch":     self._create_branch,
            "commit_push":       self._commit_push,
            "search_code":       self._search_code,
            "get_commits":       self._get_commits,
            "create_release":    self._create_release,
            "run_workflow":      self._run_workflow,
            "get_workflow_runs": self._get_workflow_runs,
        }
        fn = actions.get(action)
        if not fn:
            return IntegrationResult(success=False,
                                     error=f"action غير معروف: {action}. المتاح: {list(actions)}")
        return fn(params)

    def _req(self, method: str, path: str, **kwargs) -> requests.Response:
        return requests.request(
            method, f"{GITHUB_API}{path}",
            headers=self._headers(), timeout=15, **kwargs
        )

    def _get_user(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/users/{p.get('username', '')}" if p.get("username") else "/user")
        return IntegrationResult(success=r.status_code == 200,
                                  data=r.json() if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _list_repos(self, p: dict) -> IntegrationResult:
        owner = p.get("owner", "")
        path  = f"/users/{owner}/repos" if owner else "/user/repos"
        r     = self._req("GET", path, params={
            "sort": p.get("sort", "updated"),
            "per_page": p.get("limit", 30),
            "type": p.get("type", "all"),
        })
        if r.ok:
            repos = [{"name": x["name"], "full_name": x["full_name"],
                      "description": x.get("description"), "private": x["private"],
                      "stars": x["stargazers_count"], "language": x.get("language"),
                      "url": x["html_url"]} for x in r.json()]
            return IntegrationResult(success=True, data=repos,
                                      message=f"{len(repos)} مستودع")
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _get_repo(self, p: dict) -> IntegrationResult:
        r = self._req("GET", f"/repos/{p['owner']}/{p['repo']}")
        return IntegrationResult(success=r.ok, data=r.json() if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _create_repo(self, p: dict) -> IntegrationResult:
        r = self._req("POST", "/user/repos", json={
            "name":        p["name"],
            "description": p.get("description", ""),
            "private":     p.get("private", False),
            "auto_init":   p.get("auto_init", True),
        })
        return IntegrationResult(success=r.ok,
                                  data={"url": r.json().get("html_url")} if r.ok else None,
                                  message=f"مستودع '{p['name']}' أُنشئ" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _clone_repo(self, p: dict) -> IntegrationResult:
        url     = p.get("url") or f"https://github.com/{p['owner']}/{p['repo']}.git"
        dest    = p.get("dest", str(Path.home() / ".cobweaverclaw" / "repos" / p.get("repo", "repo")))
        token   = self.credentials.get("token", "")
        if token:
            url = url.replace("https://", f"https://{token}@")
        try:
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", "--depth", str(p.get("depth", 1)), url, dest],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                return IntegrationResult(success=True,
                                          data={"path": dest},
                                          message=f"تم clone في {dest}")
            return IntegrationResult(success=False, error=result.stderr[:500])
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _list_files(self, p: dict) -> IntegrationResult:
        path = p.get("path", "")
        r    = self._req("GET",
                         f"/repos/{p['owner']}/{p['repo']}/contents/{path}",
                         params={"ref": p.get("branch", "main")})
        if r.ok:
            items = [{"name": x["name"], "type": x["type"],
                      "path": x["path"], "size": x.get("size")}
                     for x in r.json()]
            return IntegrationResult(success=True, data=items)
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _get_file(self, p: dict) -> IntegrationResult:
        import base64
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/contents/{p['path']}",
                      params={"ref": p.get("branch", "main")})
        if r.ok:
            data    = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return IntegrationResult(success=True,
                                      data={"content": content, "sha": data["sha"],
                                            "size": data["size"]})
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _create_file(self, p: dict) -> IntegrationResult:
        import base64
        r = self._req("PUT",
                      f"/repos/{p['owner']}/{p['repo']}/contents/{p['path']}",
                      json={"message": p.get("message", "إضافة ملف"),
                            "content": base64.b64encode(
                                p["content"].encode()).decode(),
                            "branch":  p.get("branch", "main")})
        return IntegrationResult(success=r.ok,
                                  message="تم إنشاء الملف" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _update_file(self, p: dict) -> IntegrationResult:
        import base64
        r = self._req("PUT",
                      f"/repos/{p['owner']}/{p['repo']}/contents/{p['path']}",
                      json={"message": p.get("message", "تحديث ملف"),
                            "content": base64.b64encode(
                                p["content"].encode()).decode(),
                            "sha":     p["sha"],
                            "branch":  p.get("branch", "main")})
        return IntegrationResult(success=r.ok,
                                  message="تم تحديث الملف" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _delete_file(self, p: dict) -> IntegrationResult:
        r = self._req("DELETE",
                      f"/repos/{p['owner']}/{p['repo']}/contents/{p['path']}",
                      json={"message": p.get("message", "حذف ملف"),
                            "sha":     p["sha"],
                            "branch":  p.get("branch", "main")})
        return IntegrationResult(success=r.ok,
                                  message="تم الحذف" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _list_issues(self, p: dict) -> IntegrationResult:
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/issues",
                      params={"state": p.get("state", "open"),
                              "per_page": p.get("limit", 20)})
        if r.ok:
            issues = [{"number": x["number"], "title": x["title"],
                       "state": x["state"], "labels": [l["name"] for l in x["labels"]],
                       "created_at": x["created_at"]} for x in r.json()]
            return IntegrationResult(success=True, data=issues)
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _create_issue(self, p: dict) -> IntegrationResult:
        r = self._req("POST",
                      f"/repos/{p['owner']}/{p['repo']}/issues",
                      json={"title":  p["title"],
                            "body":   p.get("body", ""),
                            "labels": p.get("labels", [])})
        return IntegrationResult(success=r.ok,
                                  data={"number": r.json().get("number"),
                                        "url": r.json().get("html_url")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _close_issue(self, p: dict) -> IntegrationResult:
        r = self._req("PATCH",
                      f"/repos/{p['owner']}/{p['repo']}/issues/{p['number']}",
                      json={"state": "closed"})
        return IntegrationResult(success=r.ok,
                                  message=f"Issue #{p['number']} أُغلق" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _list_prs(self, p: dict) -> IntegrationResult:
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/pulls",
                      params={"state": p.get("state", "open"),
                              "per_page": p.get("limit", 20)})
        if r.ok:
            prs = [{"number": x["number"], "title": x["title"],
                    "state": x["state"], "head": x["head"]["ref"],
                    "base": x["base"]["ref"]} for x in r.json()]
            return IntegrationResult(success=True, data=prs)
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _create_pr(self, p: dict) -> IntegrationResult:
        r = self._req("POST",
                      f"/repos/{p['owner']}/{p['repo']}/pulls",
                      json={"title": p["title"], "body": p.get("body", ""),
                            "head":  p["head"], "base": p.get("base", "main")})
        return IntegrationResult(success=r.ok,
                                  data={"number": r.json().get("number"),
                                        "url": r.json().get("html_url")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _merge_pr(self, p: dict) -> IntegrationResult:
        r = self._req("PUT",
                      f"/repos/{p['owner']}/{p['repo']}/pulls/{p['number']}/merge",
                      json={"merge_method": p.get("method", "squash"),
                            "commit_title": p.get("title", "")})
        return IntegrationResult(success=r.ok,
                                  message="تم الدمج" if r.ok else "",
                                  error=None if r.ok else r.json().get("message"))

    def _list_branches(self, p: dict) -> IntegrationResult:
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/branches")
        if r.ok:
            return IntegrationResult(success=True,
                                      data=[x["name"] for x in r.json()])
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _create_branch(self, p: dict) -> IntegrationResult:
        # احصل على SHA للـ base
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/git/ref/heads/{p.get('from', 'main')}")
        if not r.ok:
            return IntegrationResult(success=False, error=r.json().get("message"))
        sha = r.json()["object"]["sha"]
        r2  = self._req("POST",
                        f"/repos/{p['owner']}/{p['repo']}/git/refs",
                        json={"ref": f"refs/heads/{p['branch']}", "sha": sha})
        return IntegrationResult(success=r2.ok,
                                  message=f"فرع '{p['branch']}' أُنشئ" if r2.ok else "",
                                  error=None if r2.ok else r2.json().get("message"))

    def _commit_push(self, p: dict) -> IntegrationResult:
        """commit وpush ملفات من مسار محلي"""
        repo_path = p.get("repo_path", "")
        if not repo_path or not Path(repo_path).exists():
            return IntegrationResult(success=False,
                                      error=f"مسار المستودع غير موجود: {repo_path}")
        try:
            cmds = [
                ["git", "-C", repo_path, "add", p.get("files", ".") if isinstance(p.get("files"), str) else " ".join(p.get("files", ["."]))],
                ["git", "-C", repo_path, "commit", "-m", p.get("message", "تحديث")],
                ["git", "-C", repo_path, "push"],
            ]
            for cmd in cmds:
                result = subprocess.run(cmd, capture_output=True,
                                        text=True, timeout=60)
                if result.returncode != 0 and "nothing to commit" not in result.stdout:
                    return IntegrationResult(success=False, error=result.stderr[:300])
            return IntegrationResult(success=True, message="تم push التغييرات")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _search_code(self, p: dict) -> IntegrationResult:
        query = p["query"]
        if p.get("repo"):
            query += f" repo:{p['repo']}"
        r = self._req("GET", "/search/code",
                      params={"q": query, "per_page": p.get("limit", 10)})
        if r.ok:
            items = [{"path": x["path"], "repo": x["repository"]["full_name"],
                      "url": x["html_url"]} for x in r.json().get("items", [])]
            return IntegrationResult(success=True, data=items,
                                      message=f"{r.json().get('total_count', 0)} نتيجة")
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _get_commits(self, p: dict) -> IntegrationResult:
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/commits",
                      params={"per_page": p.get("limit", 10),
                              "sha": p.get("branch", "main")})
        if r.ok:
            commits = [{"sha": x["sha"][:7], "message": x["commit"]["message"][:80],
                        "author": x["commit"]["author"]["name"],
                        "date": x["commit"]["author"]["date"]} for x in r.json()]
            return IntegrationResult(success=True, data=commits)
        return IntegrationResult(success=False, error=r.json().get("message"))

    def _create_release(self, p: dict) -> IntegrationResult:
        r = self._req("POST",
                      f"/repos/{p['owner']}/{p['repo']}/releases",
                      json={"tag_name": p["tag"], "name": p.get("name", p["tag"]),
                            "body": p.get("body", ""),
                            "draft": p.get("draft", False),
                            "prerelease": p.get("prerelease", False)})
        return IntegrationResult(success=r.ok,
                                  data={"url": r.json().get("html_url")} if r.ok else None,
                                  error=None if r.ok else r.json().get("message"))

    def _run_workflow(self, p: dict) -> IntegrationResult:
        r = self._req("POST",
                      f"/repos/{p['owner']}/{p['repo']}/actions/workflows/{p['workflow_id']}/dispatches",
                      json={"ref": p.get("branch", "main"),
                            "inputs": p.get("inputs", {})})
        return IntegrationResult(success=r.status_code == 204,
                                  message="Workflow بدأ" if r.status_code == 204 else "",
                                  error=None if r.status_code == 204 else str(r.status_code))

    def _get_workflow_runs(self, p: dict) -> IntegrationResult:
        r = self._req("GET",
                      f"/repos/{p['owner']}/{p['repo']}/actions/runs",
                      params={"per_page": p.get("limit", 10)})
        if r.ok:
            runs = [{"id": x["id"], "name": x["name"], "status": x["status"],
                     "conclusion": x.get("conclusion"), "created_at": x["created_at"]}
                    for x in r.json().get("workflow_runs", [])]
            return IntegrationResult(success=True, data=runs)
        return IntegrationResult(success=False, error=r.json().get("message"))
