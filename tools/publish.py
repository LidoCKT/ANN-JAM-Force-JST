"""Publish a curated source snapshot, preserving the repository's history."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/LidoCKT/ANN-JAM-Force-JST.git"
MANIFEST = ".annjam-publish-manifest.json"
SOURCE_DIRECTORIES = {"app", "tests", "tools"}
SOURCE_FILES = {
    ".gitignore", "README.md", "VALIDATION.md", "RELEASE_NOTES.md",
    "PUBLISH.md", "build.ps1", "publish.ps1",
}
EXCLUDED_DIRECTORIES = {".git", "__pycache__", "build", "signing", "deps"}
EXCLUDED_SUFFIXES = {".apk", ".xapk", ".p12", ".pfx", ".jks", ".keystore", ".pyc"}


def is_source_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    if path.is_absolute() or "\\" in relative or ":" in relative:
        return False
    if any(part in {".", ".."} | EXCLUDED_DIRECTORIES for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return relative in SOURCE_FILES or (
        len(path.parts) > 1 and path.parts[0] in SOURCE_DIRECTORIES)


def source_files(root: Path) -> list[str]:
    result = []
    for name in sorted(SOURCE_FILES):
        if (root / name).is_file():
            result.append(name)
    for directory in sorted(SOURCE_DIRECTORIES):
        for path in sorted((root / directory).rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_file() and is_source_path(relative):
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise RuntimeError(f"Refusing source symlink: {relative}")
                result.append(relative)
    return sorted(result)


def git(directory: Path, *arguments: str, capture: bool = False,
        check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(directory), *arguments], check=check,
        text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def checked_path(checkout: Path, relative: str) -> Path:
    path = checkout / relative
    if not path.resolve().is_relative_to(checkout.resolve()):
        raise RuntimeError(f"Path escapes checkout: {relative}")
    probe = path
    while probe != checkout:
        if probe.is_symlink():
            raise RuntimeError(f"Refusing checkout symlink: {relative}")
        probe = probe.parent
    return path


def publish(root: Path, repository: str, message: str, preview: bool = False,
            author_name: str | None = None, author_email: str | None = None) -> dict:
    root = root.resolve()
    files = source_files(root)
    required = {"README.md", ".gitignore", "app/src/main/AndroidManifest.xml",
                "app/src/main/assets/xposed_init"}
    if not required.issubset(files):
        raise RuntimeError("Incomplete source snapshot; refusing to publish.")
    print(f"Target: {repository}\nSource files: {len(files)}", flush=True)
    if preview:
        print("\n".join(files))
        return {"preview": True, "files": files}

    build = root / "build"
    build.mkdir(exist_ok=True)
    # A new clone avoids merging against an unrelated local Git repository.
    # Retain it for inspection/retry if authentication or push fails.
    checkout = Path(tempfile.mkdtemp(prefix="github-publish-", dir=build))
    if not checkout.resolve().is_relative_to(build.resolve()):
        raise RuntimeError("Checkout is outside the build directory.")
    print(f"Checkout: {checkout}", flush=True)
    try:
        subprocess.run(["git", "clone", "--single-branch", "--",
                        repository, str(checkout)], check=True)
        head = git(checkout, "rev-parse", "--verify", "HEAD",
                   capture=True, check=False)
        if head.returncode != 0:
            git(checkout, "symbolic-ref", "HEAD", "refs/heads/main")
        branch = git(checkout, "symbolic-ref", "--short", "HEAD",
                     capture=True).stdout.strip()

        manifest_path = checked_path(checkout, MANIFEST)
        previous = []
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(previous, list) or not all(
                    isinstance(item, str) and is_source_path(item) for item in previous):
                raise RuntimeError("Invalid source manifest in the remote repository.")

        # Only remove files recorded by an earlier run of this script.
        # Repository-specific files such as LICENSE and .github are preserved.
        for relative in set(previous) - set(files):
            path = checked_path(checkout, relative)
            if path.exists():
                if not path.is_file():
                    raise RuntimeError(f"Expected managed file: {relative}")
                path.unlink()
        for relative in files:
            source = root / relative
            if source.is_symlink() or not source.resolve().is_relative_to(root):
                raise RuntimeError(f"Refusing source symlink: {relative}")
            destination = checked_path(checkout, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        manifest_path.write_text(
            json.dumps(files, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Configure only this disposable clone, leaving global settings alone.
        for key, explicit, fallback in (
                ("user.name", author_name, "LidoCKT"),
                ("user.email", author_email, "LidoCKT@users.noreply.github.com")):
            configured = git(checkout, "config", "--get", key,
                             capture=True, check=False).stdout.strip()
            git(checkout, "config", key, explicit or configured or fallback)

        managed = sorted(set(previous) | set(files) | {MANIFEST})
        git(checkout, "add", "-A", "--", *managed)
        changed = git(checkout, "diff", "--cached", "--quiet", check=False)
        if changed.returncode == 0:
            print("Source is already up to date; no commit or push needed.")
            return {"changed": False, "checkout": str(checkout), "branch": branch}
        if changed.returncode != 1:
            raise RuntimeError("Could not inspect staged changes.")
        git(checkout, "diff", "--cached", "--stat")
        git(checkout, "commit", "-m", message)
        # Normal fast-forward push: concurrent remote updates are never forced.
        git(checkout, "push", "--set-upstream", "origin",
            f"HEAD:refs/heads/{branch}")
        commit = git(checkout, "rev-parse", "HEAD", capture=True).stdout.strip()
        result = {"changed": True, "checkout": str(checkout),
                  "branch": branch, "commit": commit}
        (build / "last-publish.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Published {commit} to {branch}", flush=True)
        return result
    except Exception:
        print(f"Publishing stopped. Checkout retained at: {checkout}", flush=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", default="Update ANN JAM Force JST")
    parser.add_argument("--preview", action="store_true",
                        help="List source files only; no network or Git writes.")
    parser.add_argument("--author-name")
    parser.add_argument("--author-email")
    options = parser.parse_args()
    publish(ROOT, REPOSITORY, options.message, options.preview,
            options.author_name, options.author_email)


if __name__ == "__main__":
    main()
