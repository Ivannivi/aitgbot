import hashlib
import os
import sys
import httpx

BUILD_DATE = None
BUILD_COMMIT = None
BUILD_REPO = None


def get_executable_path() -> str:
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)


def get_sha256() -> str:
    exe_path = get_executable_path()
    if not os.path.exists(exe_path):
        return "unknown"
    sha256 = hashlib.sha256()
    with open(exe_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_for_updates() -> dict:
    if not BUILD_REPO:
        return {"available": False, "error": "No repository configured"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"https://api.github.com/repos/{BUILD_REPO}/commits/HEAD",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if response.status_code != 200:
                return {"available": False, "error": "Could not fetch latest commit"}
            data = response.json()
            latest = data.get("sha", "")[:7]

            if latest and BUILD_COMMIT and latest != BUILD_COMMIT:
                return {
                    "available": True,
                    "current": BUILD_COMMIT,
                    "latest": latest,
                    "url": f"https://github.com/{BUILD_REPO}/releases/tag/latest"
                }
            return {"available": False, "current": BUILD_COMMIT, "latest": latest}
    except Exception as e:
        return {"available": False, "error": str(e)}


def print_version_info():
    print("aitgbot")
    print("-" * 40)

    if BUILD_COMMIT:
        print(f"Commit:     {BUILD_COMMIT}")
    else:
        print("Commit:     dev (local build)")

    if BUILD_DATE:
        print(f"Built:      {BUILD_DATE}")

    if BUILD_REPO:
        print(f"Repository: https://github.com/{BUILD_REPO}")

    print(f"SHA256:     {get_sha256()}")

    if BUILD_REPO:
        print("\nChecking for updates...")
        update = check_for_updates()
        if update.get("error"):
            print(f"  Could not check: {update['error']}")
        elif update.get("available"):
            print(f"  Update available: {update['current']} -> {update['latest']}")
            print(f"  Download: {update['url']}")
        else:
            print("  You are running the latest version.")
