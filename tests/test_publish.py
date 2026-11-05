"""Offline integration checks: all remotes here are temporary local Git repos."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import json

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("annjam_publish", ROOT / "tools/publish.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def git(directory, *arguments):
    return subprocess.run(
        ["git", "-C", str(directory), *arguments], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()


class PublisherTests(unittest.TestCase):
    def setUp(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="publish-test-", dir=build)
        self.base = Path(self.temporary.name).resolve()
        # Verify the absolute cleanup target before TemporaryDirectory removes it.
        self.assertTrue(self.base.is_relative_to(build.resolve()))
        self.addCleanup(self.temporary.cleanup)
        self.remote = self.base / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(self.remote)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.source = self.base / "source"
        self.source.mkdir()
        for relative, content in {
            "README.md": "Current project documentation\n",
            ".gitignore": "/build/\n/signing/\n/tools/deps/\n",
            "app/src/main/AndroidManifest.xml": "<manifest />\n",
            "app/src/main/assets/xposed_init": "test.Module\n",
            "tools/obsolete.py": "# previously published\n",
            "tools/deps/private.jar": "DO NOT UPLOAD",
            "tools/cache.p12": "DO NOT UPLOAD",
            "signing/local-test.p12": "DO NOT UPLOAD",
            "build/app.apk": "DO NOT UPLOAD",
            "original.xapk": "DO NOT UPLOAD",
        }.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def publish(self):
        return publisher.publish(self.source, str(self.remote), "Offline test",
                                 author_name="Publisher Test",
                                 author_email="test@example.invalid")

    def tree(self):
        return set(git(self.remote, "ls-tree", "-r", "--name-only", "main").splitlines())

    def test_existing_history_noop_and_managed_deletion(self):
        seed = self.base / "seed"
        subprocess.run(["git", "clone", str(self.remote), str(seed)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git(seed, "config", "user.name", "Seed Test")
        git(seed, "config", "user.email", "seed@example.invalid")
        (seed / "LICENSE").write_text("Existing repository-specific file\n")
        git(seed, "add", "LICENSE")
        git(seed, "commit", "-m", "Existing repository history")
        git(seed, "push", "origin", "main")
        ancestor = git(self.remote, "rev-parse", "main")

        first = self.publish()
        self.assertTrue(first["changed"])
        self.assertEqual(git(self.remote, "rev-parse", "main^"), ancestor)
        self.assertIn("LICENSE", self.tree())
        self.assertIn("tools/obsolete.py", self.tree())
        self.assertNotIn("tools/cache.p12", self.tree())
        self.assertNotIn("tools/deps/private.jar", self.tree())
        self.assertFalse(any(path.startswith(("signing/", "build/"))
                             or path.endswith(".xapk") for path in self.tree()))

        unchanged = self.publish()
        self.assertFalse(unchanged["changed"])
        self.assertEqual(git(self.remote, "rev-parse", "main"), first["commit"])

        (self.source / "tools/obsolete.py").unlink()
        (self.source / "README.md").write_text("Updated documentation\n")
        self.assertTrue(self.publish()["changed"])
        self.assertNotIn("tools/obsolete.py", self.tree())
        self.assertIn("LICENSE", self.tree())

    def test_empty_remote_and_offline_preview(self):
        before = set(self.source.iterdir())
        preview = publisher.publish(self.source, str(self.remote), "Preview", preview=True)
        self.assertTrue(preview["preview"])
        self.assertEqual(set(self.source.iterdir()), before)
        self.assertTrue(self.publish()["changed"])
        self.assertEqual(git(self.remote, "symbolic-ref", "--short", "HEAD"), "main")

    def test_path_validation(self):
        for path in ["../secret", "tools/../../secret", "C:/secret",
                     "tools\\..\\secret", "tools/deps/api.jar", "signing/key.p12",
                     "app/cache.p12", ".git/config", "build/app.apk"]:
            self.assertFalse(publisher.is_source_path(path), path)
        self.assertTrue(publisher.is_source_path("tools/publish.py"))

    def test_failed_push_resumes_existing_commit(self):
        failure = subprocess.CalledProcessError(1, ["git", "push"])
        with patch.object(publisher, "push_with_retry", side_effect=failure):
            with self.assertRaises(subprocess.CalledProcessError):
                self.publish()
        state_path = self.source / "build/last-publish.json"
        failed = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertTrue(failed["pending"])
        result = publisher.resume(self.source, "latest", str(self.remote))
        self.assertEqual(result["commit"], failed["commit"])
        self.assertFalse(result["pending"])
        self.assertEqual(git(self.remote, "rev-list", "--count", "main"), "1")


class RetryTests(unittest.TestCase):
    @staticmethod
    def response(code, error=""):
        return subprocess.CompletedProcess(["git", "push"], code, "", error)

    def test_transient_error_retries_same_push(self):
        with patch.object(publisher, "git", side_effect=[
                self.response(1, "remote: fatal error in commit_refs_rules"),
                self.response(0, "Everything up-to-date\n")]) as command:
            with patch.object(publisher.time, "sleep") as sleep:
                publisher.push_with_retry(Path("."), "main")
        self.assertEqual(command.call_count, 2)
        self.assertEqual(command.call_args_list[0], command.call_args_list[1])
        sleep.assert_called_once_with(5)

    def test_retries_are_bounded(self):
        with patch.object(publisher, "git",
                          return_value=self.response(1, "Internal Server Error")) as command:
            with patch.object(publisher.time, "sleep") as sleep:
                with self.assertRaises(subprocess.CalledProcessError):
                    publisher.push_with_retry(Path("."), "main")
        self.assertEqual(command.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 15])

    def test_permission_or_history_rejection_is_not_retried(self):
        for error in ["GH013: protected branch",
                      "non-fast-forward", "Authentication failed"]:
            with self.subTest(error=error):
                with patch.object(publisher, "git",
                                  return_value=self.response(1, error)) as command:
                    with patch.object(publisher.time, "sleep") as sleep:
                        with self.assertRaises(subprocess.CalledProcessError):
                            publisher.push_with_retry(Path("."), "main")
                self.assertEqual(command.call_count, 1)
                sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
