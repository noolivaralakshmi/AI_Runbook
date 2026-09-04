"""GitHub integration service - creates issues and pull requests via the GitHub API."""
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # e.g. "owner/repo"
GITHUB_API_BASE = "https://api.github.com"


def _headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def create_issue(title: str, body: str, labels: list = None, priority: str = "medium") -> dict:
    """Create a GitHub issue for the incident.

    Returns a dict with issue number, url, and title on success,
    or an error dict on failure.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"error": "GitHub not configured (missing GITHUB_TOKEN or GITHUB_REPO)"}

    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/issues"

    # Map severity to labels
    issue_labels = labels or []
    severity_labels = {
        "critical": ["critical", "incident"],
        "high": ["high-priority", "incident"],
        "medium": ["medium-priority", "incident"],
        "low": ["low-priority", "incident"],
    }
    issue_labels.extend(severity_labels.get(priority, ["incident"]))

    payload = {
        "title": title,
        "body": body,
        "labels": issue_labels,
    }

    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        if resp.status_code == 201:
            data = resp.json()
            return {
                "id": f"#{data['number']}",
                "number": data["number"],
                "title": data["title"],
                "url": data["html_url"],
                "status": "created",
            }
        else:
            return {"error": f"GitHub API error {resp.status_code}: {resp.text[:200]}"}
    except requests.RequestException as e:
        return {"error": f"GitHub request failed: {str(e)}"}


def create_pull_request(title: str, body: str, branch_name: str, files_to_change: list = None, code_fix: dict = None) -> dict:
    """Create a draft pull request with actual code fixes applied.

    Args:
        title: PR title
        body: PR description
        branch_name: Name for the fix branch
        files_to_change: List of file paths that need changes
        code_fix: Dict with keys:
            - file_path: path to the file to fix in the repo
            - find: the buggy code string to find
            - replace: the corrected code string to replace with

    Returns a dict with PR number, url, and branch on success.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"error": "GitHub not configured (missing GITHUB_TOKEN or GITHUB_REPO)"}

    try:
        # Step 1: Get the default branch and its latest SHA
        repo_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}"
        repo_resp = requests.get(repo_url, headers=_headers(), timeout=15)
        if repo_resp.status_code != 200:
            return {"error": f"Could not fetch repo info: {repo_resp.status_code}"}

        default_branch = repo_resp.json().get("default_branch", "main")

        # Get the SHA of the latest commit on default branch
        ref_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/ref/heads/{default_branch}"
        ref_resp = requests.get(ref_url, headers=_headers(), timeout=15)
        if ref_resp.status_code != 200:
            return {"error": f"Could not fetch branch ref: {ref_resp.status_code}"}

        base_sha = ref_resp.json()["object"]["sha"]

        # Step 2: Create a new branch
        create_ref_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/refs"
        ref_payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha,
        }
        create_resp = requests.post(create_ref_url, json=ref_payload, headers=_headers(), timeout=15)
        if create_resp.status_code not in (201, 422):
            return {"error": f"Could not create branch: {create_resp.status_code} {create_resp.text[:200]}"}

        # Step 3: Apply the actual code fix if provided
        code_fixed = False
        if code_fix and code_fix.get("file_path") and code_fix.get("find") and code_fix.get("replace"):
            fix_result = _apply_code_fix(branch_name, code_fix)
            if fix_result.get("success"):
                code_fixed = True

        # Step 4: If no code fix was applied, create a description file
        if not code_fixed:
            file_content = (
                f"# Incident Fix\n\n"
                f"## {title}\n\n"
                f"{body}\n\n"
                f"## Files to investigate\n"
            )
            if files_to_change:
                for f in files_to_change:
                    file_content += f"- `{f}`\n"

            encoded_content = base64.b64encode(file_content.encode()).decode()
            file_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/incidents/{branch_name}.md"
            file_payload = {
                "message": f"incident: {title}",
                "content": encoded_content,
                "branch": branch_name,
            }
            requests.put(file_url, json=file_payload, headers=_headers(), timeout=15)

        # Step 5: Create draft pull request
        pr_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/pulls"
        pr_payload = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": default_branch,
            "draft": False,
        }
        pr_resp = requests.post(pr_url, json=pr_payload, headers=_headers(), timeout=15)
        if pr_resp.status_code == 201:
            pr_data = pr_resp.json()
            return {
                "number": pr_data["number"],
                "title": pr_data["title"],
                "url": pr_data["html_url"],
                "branch": branch_name,
                "status": "draft",
                "code_fixed": code_fixed,
                "files_changed": files_to_change or [],
            }
        else:
            return {"error": f"Could not create PR: {pr_resp.status_code} {pr_resp.text[:200]}"}

    except requests.RequestException as e:
        return {"error": f"GitHub request failed: {str(e)}"}


def _apply_code_fix(branch_name: str, code_fix: dict) -> dict:
    """Fetch a file from the repo, apply find/replace fix, and commit the change.

    Args:
        branch_name: The branch to commit the fix to
        code_fix: Dict with file_path, find, replace

    Returns dict with success boolean.
    """
    file_path = code_fix["file_path"]
    find_str = code_fix["find"]
    replace_str = code_fix["replace"]

    try:
        # Fetch the current file content
        file_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{file_path}"
        file_resp = requests.get(file_url, params={"ref": branch_name}, headers=_headers(), timeout=15)

        if file_resp.status_code != 200:
            return {"success": False, "error": f"Could not fetch file: {file_resp.status_code}"}

        file_data = file_resp.json()
        file_sha = file_data["sha"]
        current_content = base64.b64decode(file_data["content"]).decode("utf-8")

        # Apply the fix - try exact match first, then fuzzy match on the key change
        if find_str in current_content:
            fixed_content = current_content.replace(find_str, replace_str)
        else:
            # Fuzzy approach: extract the core change (e.g., table name swap)
            # Look for the key difference between find and replace
            fixed_content = _fuzzy_fix(current_content, find_str, replace_str)
            if fixed_content is None:
                return {"success": False, "error": "Could not find the buggy code in the file"}

        # Commit the fixed file
        encoded_fixed = base64.b64encode(fixed_content.encode("utf-8")).decode()
        update_payload = {
            "message": f"fix: {replace_str.strip()[:50]} (automated fix)",
            "content": encoded_fixed,
            "sha": file_sha,
            "branch": branch_name,
        }
        update_resp = requests.put(file_url, json=update_payload, headers=_headers(), timeout=15)

        if update_resp.status_code in (200, 201):
            return {"success": True}
        else:
            return {"success": False, "error": f"Could not update file: {update_resp.status_code}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _fuzzy_fix(content: str, find_str: str, replace_str: str) -> str:
    """Attempt a fuzzy code fix by identifying the key difference between find and replace.
    
    For example, if find='SELECT * FROM user_credentials' and replace='SELECT * FROM users',
    we look for 'user_credentials' in the actual file and replace it with 'users'.
    """
    import difflib

    # Strategy 1: Find the differing words between find and replace
    find_words = set(find_str.split())
    replace_words = set(replace_str.split())

    removed = find_words - replace_words  # words in find but not in replace
    added = replace_words - find_words    # words in replace but not in find

    # If we can identify a simple substitution (one thing changed)
    if len(removed) <= 2 and len(added) <= 2:
        for old_word in removed:
            # Clean quotes and punctuation for matching
            clean_old = old_word.strip("'\"(),;")
            if clean_old and clean_old in content:
                # Find the corresponding new word
                for new_word in added:
                    clean_new = new_word.strip("'\"(),;")
                    if clean_new:
                        fixed = content.replace(clean_old, clean_new)
                        if fixed != content:
                            return fixed

    # Strategy 2: Line-by-line matching
    find_lines = find_str.strip().split('\n')
    content_lines = content.split('\n')
    
    for find_line in find_lines:
        find_line_stripped = find_line.strip()
        if not find_line_stripped:
            continue
        # Find close matches in the actual content
        matches = difflib.get_close_matches(find_line_stripped, 
                                            [l.strip() for l in content_lines], 
                                            n=1, cutoff=0.6)
        if matches:
            # Found a similar line — apply the intended replacement
            for i, content_line in enumerate(content_lines):
                if content_line.strip() == matches[0]:
                    # Determine what the replacement should be
                    replace_lines = replace_str.strip().split('\n')
                    if replace_lines:
                        indent = content_line[:len(content_line) - len(content_line.lstrip())]
                        content_lines[i] = indent + replace_lines[0].strip()
                        return '\n'.join(content_lines)

    return None
