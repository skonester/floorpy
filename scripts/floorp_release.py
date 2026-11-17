"""Resolve upstream releases and prepare a verified browser payload for CI."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.request


UPSTREAM = "Floorp-Projects/Floorp"
INSTALLERS = ("floorp-windows-x86_64.installer.exe", "floorp-win64.installer.exe")
RELEASE_FILES = {"floorpy.exe", "floorpy.exe.sha256", "readme.md", "LICENSE.md"}
VERSION_TAG = r"v?\d+(?:\.\d+){1,3}"
INSTALLER_URL = (
    rf"https://github\.com/{UPSTREAM}/releases/download/{VERSION_TAG}/"
    r"floorp-(?:windows-x86_64|win64)\.installer\.exe"
)


def github_json(path, token="", allow_missing=False):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FloorpyReleaseWorkflow",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if allow_missing and error.code == 404:
            return None
        raise


def plan_release(upstream, existing=None, publish=False):
    tag = upstream["tag_name"]
    if upstream.get("draft") or upstream.get("prerelease") or not re.fullmatch(VERSION_TAG, tag):
        raise ValueError(f"Expected a stable Floorp version tag, got {tag!r}")

    assets = {asset["name"]: asset for asset in upstream["assets"]}
    installer = next((assets[name] for name in INSTALLERS if name in assets), None)
    if installer is None:
        raise ValueError("The Floorp release has no Windows x64 offline installer")
    digest = installer.get("digest", "") or ""
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError("The Floorp installer has no valid SHA-256 release digest")

    release_tag = f"floorpy-v{tag.removeprefix('v')}"
    complete = False
    if existing and existing.get("tag_name") == release_tag:
        uploaded = {
            asset["name"] for asset in existing.get("assets", [])
            if asset.get("state") == "uploaded" and asset.get("size", 0) > 0
        }
        complete = (
            not existing.get("draft") and not existing.get("prerelease")
            and RELEASE_FILES <= uploaded
        )

    return {
        "floorp_tag": tag,
        "release_tag": release_tag,
        "installer_url": f"https://github.com/{UPSTREAM}/releases/download/{tag}/{installer['name']}",
        "installer_sha256": digest.split(":", 1)[1].lower(),
        "should_build": str(not publish or not complete).lower(),
        "publish": str(publish).lower(),
    }


def resolve_plan(repository, publish=False, token=""):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected a GitHub owner/repository name")
    upstream = github_json(f"repos/{UPSTREAM}/releases/latest", token)
    plan = plan_release(upstream, publish=publish)
    if publish:
        existing = github_json(
            f"repos/{repository}/releases/tags/{plan['release_tag']}", token, allow_missing=True
        )
        plan = plan_release(upstream, existing, publish=True)
    return plan


def prepare_browser(workspace, installer_url, expected_sha256):
    if not re.fullmatch(INSTALLER_URL, installer_url):
        raise ValueError("Expected a version-specific official Floorp installer URL")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("Expected the installer's SHA-256 digest")

    workspace = Path(workspace).resolve()
    destination = workspace / "floorp"
    if destination.exists():
        raise ValueError("CI browser preparation requires a clean checkout without floorp/")
    build_dir = workspace / ".build"
    build_dir.mkdir(exist_ok=True)
    if build_dir.resolve().parent != workspace:
        raise ValueError("The build directory escaped the workspace")
    staging = Path(tempfile.mkdtemp(prefix="floorp-release-", dir=build_dir)).resolve()
    installer = staging / "floorp-installer.exe"
    digest = hashlib.sha256()
    request = urllib.request.Request(installer_url, headers={"User-Agent": "FloorpyReleaseWorkflow"})
    with urllib.request.urlopen(request, timeout=60) as response, installer.open("wb") as output:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != expected_sha256.lower():
        raise ValueError("Floorp installer SHA-256 verification failed; refusing to extract it")

    extracted = staging / "extracted"
    subprocess.run(
        [str(workspace / "7za64.exe"), "x", str(installer), f"-o{extracted}", "-y", r"-ir!core\*"],
        check=True,
    )
    core = extracted / "core"
    if not (core / "floorp.exe").is_file():
        raise ValueError("The verified installer did not contain core/floorp.exe")
    # Verify both resolved directory paths before moving the extracted browser.
    if (core.resolve().parent != extracted.resolve()
            or not core.resolve().is_relative_to(workspace)
            or destination.resolve().parent != workspace):
        raise ValueError("Browser paths escaped the build workspace")
    core.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "prepare"))
    args = parser.parse_args()
    if args.command == "prepare":
        destination = prepare_browser(
            Path.cwd(), os.environ["FLOORP_INSTALLER_URL"], os.environ["FLOORP_INSTALLER_SHA256"]
        )
        print(f"Verified Floorp payload prepared in {destination}")
        return

    plan = resolve_plan(
        os.environ["GITHUB_REPOSITORY"],
        publish=os.environ.get("FLOORPY_PUBLISH", "false").lower() == "true",
        token=os.environ.get("GITHUB_TOKEN", ""),
    )
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            for key, value in plan.items():
                output.write(f"{key}={value}\n")
    status = "Build required" if plan["should_build"] == "true" else "Already published; build skipped"
    summary = f"{status}: Floorp {plan['floorp_tag']} / Floorpy {plan['release_tag']}\n"
    print(summary, end="")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
            output.write(summary)


if __name__ == "__main__":
    main()
