#!/usr/bin/env python3
"""Checks a maintainer application issue and posts the result as a comment.

Only the standard library is used. The issue body is treated as untrusted
input: it is parsed for a few fields and the URLs are matched against strict
patterns, so requests only ever go to api.github.com and gitlab.com.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UPSTREAM = "Bluenixx/vendor_lineage"
MAINT_FILE = os.environ.get("MAINTAINERS_PATH", "bluenixx.maintainers")
MARKER = "<!-- bluenixx-maintainer-check -->"

GH_RE = re.compile(r"^https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/(.+?))?/?$")
GL_RE = re.compile(r"^https?://gitlab\.com/([\w.-]+(?:/[\w.-]+)+?)(?:\.git)?(?:/-)?(?:/tree/(.+?))?/?$")
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
CODENAME_RE = re.compile(r"^[a-z0-9_]+$")

FIELDS = {
    "Maintainer name": "name",
    "Device codename": "codename",
    "Device tree": "device_tree",
    "Vendor tree": "vendor_tree",
    "Kernel tree": "kernel_tree",
    "Your vendor_lineage fork": "fork",
}


# ---------------------------------------------------------------- parsing

def parse_form(body):
    """Turn the issue-form markdown into {field_id: value}."""
    out = {}
    parts = re.split(r"^### +(.+?)\s*$", body or "", flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        key = FIELDS.get(parts[i].strip())
        if key:
            val = parts[i + 1].strip()
            out[key] = "" if val == "_No response_" else val
    return out


def parse_maintainers(text):
    entries = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            n, d = line.split(":", 1)
            entries.append((n.strip(), d.strip()))
    return entries


def find_assignment(text, var):
    m = re.search(r"^\s*" + re.escape(var) + r"\s*:?=\s*(\S+)\s*$", text, flags=re.M)
    return m.group(1) if m else None


# ---------------------------------------------------------------- http

def http(url, headers=None, method="GET", data=None):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # network trouble, treat as a miss
        return 0, str(e)


class Repo:
    def __init__(self, url, token=None):
        url = (url or "").strip()
        self.url = url
        self.token = token
        self.host = self.path = self.branch = None
        m = GH_RE.match(url)
        if m:
            self.host, self.path, self.branch = "github", f"{m.group(1)}/{m.group(2)}", m.group(3)
        else:
            m = GL_RE.match(url)
            if m:
                self.host, self.path, self.branch = "gitlab", m.group(1), m.group(2)
        self.meta = None

    @property
    def valid(self):
        return self.host is not None

    def _gh(self, path, raw=False):
        h = {"Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
             "User-Agent": "bluenixx-maintainer-apply"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return http("https://api.github.com" + path, h)

    def _gl(self, path):
        return http("https://gitlab.com/api/v4" + path, {"User-Agent": "bluenixx-maintainer-apply"})

    def load(self):
        """Fetch repo metadata. Returns True if the repo is reachable."""
        if not self.valid:
            return False
        if self.host == "github":
            st, body = self._gh(f"/repos/{self.path}")
        else:
            st, body = self._gl("/projects/" + urllib.parse.quote(self.path, safe=""))
        if st != 200:
            return False
        try:
            self.meta = json.loads(body)
        except ValueError:
            return False
        return True

    @property
    def ref(self):
        return self.branch or (self.meta or {}).get("default_branch") or "main"

    def file(self, path):
        ref = urllib.parse.quote(self.ref, safe="")
        if self.host == "github":
            st, body = self._gh(f"/repos/{self.path}/contents/{urllib.parse.quote(path)}?ref={ref}", raw=True)
        else:
            proj = urllib.parse.quote(self.path, safe="")
            st, body = self._gl(f"/projects/{proj}/repository/files/{urllib.parse.quote(path, safe='')}/raw?ref={ref}")
        return body if st == 200 else None


# ---------------------------------------------------------------- checks

def run_checks(f, token):
    """Returns a list of (status, title, detail). status: True, False or None (warning)."""
    res = []

    def add(ok, title, detail=""):
        res.append((ok, title, detail))

    name = f.get("name", "").strip()
    code = f.get("codename", "").strip()
    if code.startswith("bluenixx_"):
        code = code[len("bluenixx_"):]

    add(bool(NAME_RE.match(name)), "Maintainer name",
        "" if NAME_RE.match(name) else "Use only letters, numbers, `_`, `-` or `.`. No spaces or colons.")
    add(bool(CODENAME_RE.match(code)), "Device codename",
        "" if CODENAME_RE.match(code) else "Lowercase letters, numbers and `_` only.")
    if not (NAME_RE.match(name) and CODENAME_RE.match(code)):
        return res

    entry = f"{name}:bluenixx_{code}"

    # plain reachability for vendor and kernel
    for key, label in (("vendor_tree", "Vendor tree"), ("kernel_tree", "Kernel tree")):
        r = Repo(f.get(key), token)
        if not r.valid:
            add(False, label, "Not a valid GitHub or GitLab repository link.")
        elif not r.load():
            add(False, label, "Could not reach it. Make sure the repo is public.")
        else:
            add(True, label, f"`{r.path}` @ `{r.ref}`")

    # device tree + bluenixx_<codename>.mk
    dt = Repo(f.get("device_tree"), token)
    if not dt.valid:
        add(False, "Device tree", "Not a valid GitHub or GitLab repository link.")
    elif not dt.load():
        add(False, "Device tree", "Could not reach it. Make sure the repo is public.")
    else:
        add(True, "Device tree", f"`{dt.path}` @ `{dt.ref}`")
        mk_name = f"bluenixx_{code}.mk"
        mk = dt.file(mk_name)
        if mk is None:
            add(False, mk_name, f"Not found in the root of the device tree on `{dt.ref}`.")
        else:
            flag = find_assignment(mk, "BLUENIXX_MAINTAINER")
            if flag is None:
                add(False, f"{mk_name}: BLUENIXX_MAINTAINER",
                    f"Flag is missing. Add `BLUENIXX_MAINTAINER := {name}`.")
            elif flag != name:
                add(False, f"{mk_name}: BLUENIXX_MAINTAINER",
                    f"It says `{flag}` but the form says `{name}`. They have to match exactly.")
            else:
                add(True, f"{mk_name}: BLUENIXX_MAINTAINER", f"`{flag}`")
            prod = find_assignment(mk, "PRODUCT_NAME")
            if prod is None:
                add(None, f"{mk_name}: PRODUCT_NAME", "Not found, a reviewer will have a look.")
            elif prod != f"bluenixx_{code}":
                add(False, f"{mk_name}: PRODUCT_NAME",
                    f"It says `{prod}`, expected `bluenixx_{code}`.")
            else:
                add(True, f"{mk_name}: PRODUCT_NAME", f"`{prod}`")

    # fork of vendor_lineage + maintainers entry
    fk = Repo(f.get("fork"), token)
    if not (fk.valid and fk.host == "github"):
        add(False, "vendor_lineage fork", "Needs to be a GitHub link to your fork.")
    elif not fk.load():
        add(False, "vendor_lineage fork", "Could not reach it. Make sure the fork is public.")
    else:
        parent = (fk.meta.get("parent") or {}).get("full_name", "")
        if not fk.meta.get("fork") or parent.lower() != UPSTREAM.lower():
            add(False, "vendor_lineage fork", f"This is not a fork of `{UPSTREAM}`.")
        else:
            add(True, "vendor_lineage fork", f"`{fk.path}` @ `{fk.ref}`")
            txt = fk.file(MAINT_FILE)
            if txt is None:
                add(False, MAINT_FILE, f"Not found in the root of your fork on `{fk.ref}`.")
            elif (name, f"bluenixx_{code}") in parse_maintainers(txt):
                add(True, MAINT_FILE, f"Found `{entry}`")
            else:
                add(False, MAINT_FILE, f"Could not find a line that says exactly `{entry}`.")

    # is the device already taken upstream?
    up = Repo(f"https://github.com/{UPSTREAM}", token)
    if up.load():
        txt = up.file(MAINT_FILE)
        if txt:
            owners = [n for n, d in parse_maintainers(txt) if d == f"bluenixx_{code}" and n != name]
            if owners:
                add(None, "Device already has a maintainer",
                    f"`bluenixx_{code}` is listed under `{', '.join(owners)}` upstream. A reviewer will follow up.")
    return res


def render(results):
    bad = [r for r in results if r[0] is False]
    warn = [r for r in results if r[0] is None]
    lines = [MARKER, ""]
    if bad:
        lines.append(f"**{len(bad)} thing(s) need fixing before this can be reviewed.**")
    else:
        lines.append("**All checks passed.** A team member will review the trees next.")
    lines += ["", "| | Check | Details |", "|---|---|---|"]
    for ok, title, detail in results:
        mark = "pass" if ok else ("warn" if ok is None else "fail")
        lines.append(f"| {mark} | {title} | {detail} |")
    if bad:
        lines += ["", "Fix it, then edit this issue or comment `/recheck` to run the checks again."]
    elif warn:
        lines += ["", "Warnings don't block the application, they just need a human look."]
    return "\n".join(lines), bool(bad)


# ---------------------------------------------------------------- github io

def main():
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    number = os.environ["ISSUE_NUMBER"]

    def gh(method, path, data=None):
        h = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
             "User-Agent": "bluenixx-maintainer-apply"}
        st, body = http("https://api.github.com" + path, h, method, data)
        try:
            return st, json.loads(body) if body else None
        except ValueError:
            return st, None

    st, issue = gh("GET", f"/repos/{repo}/issues/{number}")
    if st != 200 or issue.get("state") != "open" or "pull_request" in issue:
        return 0
    if any(l["name"] in ("approved", "rejected") for l in issue.get("labels", [])):
        return 0

    form = parse_form(issue.get("body"))
    missing = [k for k in FIELDS.values() if not form.get(k)]
    if missing:
        results = [(False, "Form", "Missing fields: " + ", ".join(missing))]
    else:
        results = run_checks(form, token)
    text, failed = render(results)

    # one bot comment, edited in place
    st, comments = gh("GET", f"/repos/{repo}/issues/{number}/comments?per_page=100")
    existing = next((c for c in (comments or []) if MARKER in c.get("body", "")), None)
    if existing:
        gh("PATCH", f"/repos/{repo}/issues/comments/{existing['id']}", {"body": text})
    else:
        gh("POST", f"/repos/{repo}/issues/{number}/comments", {"body": text})

    # labels
    want, drop = ("needs-changes", "ready-for-review") if failed else ("ready-for-review", "needs-changes")
    colors = {"needs-changes": "d93f0b", "ready-for-review": "0e8a16",
              "maintainer-application": "5319e7", "approved": "0e8a16", "rejected": "b60205"}
    for lab, col in colors.items():
        gh("POST", f"/repos/{repo}/labels", {"name": lab, "color": col})  # 422 if it exists, fine
    gh("DELETE", f"/repos/{repo}/issues/{number}/labels/{drop}")
    gh("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": [want]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
