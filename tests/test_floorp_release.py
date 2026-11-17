"""Release planning and verified-download tests; no live API calls or publishing."""

import copy
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from scripts import floorp_release


UPSTREAM = {
    "tag_name": "v12.21.2",
    "draft": False,
    "prerelease": False,
    "assets": [{
        "name": "floorp-windows-x86_64.installer.exe",
        "digest": "sha256:" + "a" * 64,
    }],
}
URL = "https://github.com/Floorp-Projects/Floorp/releases/download/v12.21.2/floorp-windows-x86_64.installer.exe"


def published_release():
    return {
        "tag_name": "floorpy-v12.21.2",
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": name, "state": "uploaded", "size": 100}
            for name in floorp_release.RELEASE_FILES
        ],
    }


class ReleasePlanTests(unittest.TestCase):
    def test_first_build_publishes_the_detected_version(self):
        plan = floorp_release.plan_release(UPSTREAM, publish=True)
        self.assertEqual(plan["should_build"], "true")
        self.assertEqual(plan["publish"], "true")
        self.assertEqual(plan["release_tag"], "floorpy-v12.21.2")
        self.assertEqual(plan["installer_url"], URL)
        self.assertNotIn("/latest/", plan["installer_url"])

    def test_published_version_is_skipped(self):
        plan = floorp_release.plan_release(UPSTREAM, published_release(), publish=True)
        self.assertEqual(plan["should_build"], "false")

    def test_new_upstream_version_is_built(self):
        upstream = copy.deepcopy(UPSTREAM)
        upstream["tag_name"] = "v12.22.0"
        plan = floorp_release.plan_release(upstream, published_release(), publish=True)
        self.assertEqual(plan["should_build"], "true")
        self.assertEqual(plan["release_tag"], "floorpy-v12.22.0")
        self.assertIn("/v12.22.0/", plan["installer_url"])

    def test_draft_or_partial_upload_is_retried(self):
        for mode in ("draft", "missing", "empty", "pending"):
            with self.subTest(mode=mode):
                release = published_release()
                if mode == "draft":
                    release["draft"] = True
                elif mode == "missing":
                    release["assets"].pop()
                elif mode == "empty":
                    release["assets"][0]["size"] = 0
                else:
                    release["assets"][0]["state"] = "new"
                self.assertEqual(
                    floorp_release.plan_release(UPSTREAM, release, publish=True)["should_build"], "true"
                )

    def test_preview_builds_never_publish_or_skip_existing_versions(self):
        plan = floorp_release.plan_release(UPSTREAM, published_release(), publish=False)
        self.assertEqual(plan["should_build"], "true")
        self.assertEqual(plan["publish"], "false")

    def test_unsupported_upstream_release_fails(self):
        for field, value in (
            ("tag_name", "v12.21.2\npublish=true"),
            ("prerelease", True),
            ("draft", True),
            ("assets", []),
            ("assets", [{"name": "floorp-stub.installer.exe", "digest": "sha256:" + "a" * 64}]),
            ("assets", [{"name": "floorp-windows-x86_64.installer.exe", "digest": None}]),
        ):
            with self.subTest(field=field, value=value):
                upstream = copy.deepcopy(UPSTREAM)
                upstream[field] = value
                with self.assertRaises(ValueError):
                    floorp_release.plan_release(upstream, publish=True)

    def test_legacy_installer_is_supported(self):
        upstream = copy.deepcopy(UPSTREAM)
        upstream["assets"][0]["name"] = "floorp-win64.installer.exe"
        plan = floorp_release.plan_release(upstream)
        self.assertTrue(plan["installer_url"].endswith("/floorp-win64.installer.exe"))

    def test_lookup_checks_the_exact_versioned_release(self):
        with patch.object(floorp_release, "github_json", side_effect=[UPSTREAM, None]) as request:
            plan = floorp_release.resolve_plan("example/floorpy", publish=True, token="test-token")
        self.assertEqual(plan["should_build"], "true")
        self.assertEqual(request.call_args.args[0], "repos/example/floorpy/releases/tags/floorpy-v12.21.2")
        self.assertTrue(request.call_args.kwargs["allow_missing"])

    def test_only_a_missing_release_is_treated_as_unpublished(self):
        for status in (404, 403, 500):
            with self.subTest(status=status):
                error = urllib.error.HTTPError("https://api.github.com/test", status, "test", {}, None)
                with patch.object(floorp_release.urllib.request, "urlopen", side_effect=error):
                    if status == 404:
                        self.assertIsNone(floorp_release.github_json("test", allow_missing=True))
                    else:
                        with self.assertRaises(urllib.error.HTTPError):
                            floorp_release.github_json("test", allow_missing=True)


class BrowserPreparationTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="floorpy-release-test-")).resolve()
        self.temp_parent = Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.remove_workspace)

    def remove_workspace(self):
        self.assertEqual(self.workspace.parent, self.temp_parent)
        self.assertTrue(self.workspace.name.startswith("floorpy-release-test-"))
        shutil.rmtree(self.workspace)

    def test_verified_payload_is_prepared_for_local_build(self):
        payload = b"test installer bytes"

        def extract(command, check):
            extracted = Path(next(value[2:] for value in command if value.startswith("-o")))
            core = extracted / "core"
            core.mkdir(parents=True)
            (core / "floorp.exe").write_bytes(b"test browser")

        with patch.object(floorp_release.urllib.request, "urlopen", return_value=io.BytesIO(payload)) as download:
            with patch.object(floorp_release.subprocess, "run", side_effect=extract):
                destination = floorp_release.prepare_browser(
                    self.workspace, URL, hashlib.sha256(payload).hexdigest()
                )
        self.assertEqual(download.call_args.args[0].full_url, URL)
        self.assertEqual((destination / "floorp.exe").read_bytes(), b"test browser")

    def test_checksum_mismatch_never_extracts_or_installs(self):
        with patch.object(floorp_release.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")):
            with patch.object(floorp_release.subprocess, "run") as extract:
                with self.assertRaisesRegex(ValueError, "SHA-256 verification failed"):
                    floorp_release.prepare_browser(self.workspace, URL, "a" * 64)
        extract.assert_not_called()
        self.assertFalse((self.workspace / "floorp").exists())

    def test_failed_extraction_never_installs(self):
        payload = b"test installer bytes"
        with patch.object(floorp_release.urllib.request, "urlopen", return_value=io.BytesIO(payload)):
            with patch.object(floorp_release.subprocess, "run", side_effect=subprocess.CalledProcessError(2, "7za64.exe")):
                with self.assertRaises(subprocess.CalledProcessError):
                    floorp_release.prepare_browser(self.workspace, URL, hashlib.sha256(payload).hexdigest())
        self.assertFalse((self.workspace / "floorp").exists())

    def test_existing_browser_is_preserved(self):
        browser = self.workspace / "floorp"
        browser.mkdir()
        (browser / "keep.txt").write_text("preserve")
        with patch.object(floorp_release.urllib.request, "urlopen") as download:
            with self.assertRaisesRegex(ValueError, "clean checkout"):
                floorp_release.prepare_browser(self.workspace, URL, "a" * 64)
        download.assert_not_called()
        self.assertEqual((browser / "keep.txt").read_text(), "preserve")

    def test_unpinned_download_url_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "version-specific"):
            floorp_release.prepare_browser(self.workspace, URL.replace("/v12.21.2/", "/latest/"), "a" * 64)


if __name__ == "__main__":
    unittest.main()
