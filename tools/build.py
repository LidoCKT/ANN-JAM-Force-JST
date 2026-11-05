"""Build with the Android SDK + JDK, without Gradle or application dependencies."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://api.xposed.info/de/robv/android/xposed/api/82/api-82.jar"
API_SHA256 = "f48c635f1c7469fdec0e00ad2ea0b7a6b2f5b55065784a35b7ca3a84615e8e25"


def run(*args: object) -> None:
    # Some Android SDK Windows binaries use narrow APIs for file arguments.
    # Relative ASCII paths also support a checkout inside a Chinese directory.
    command = [
        str(arg.relative_to(ROOT)) if isinstance(arg, Path) and arg.is_relative_to(ROOT)
        else str(arg) for arg in args
    ]
    print("Running", Path(command[0]).name, flush=True)
    subprocess.run(command, check=True, cwd=ROOT)


def find_java(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]))
    if shutil.which("javac"):
        candidates.append(Path(shutil.which("javac")).resolve().parents[1])
    profile = Path(os.environ.get("USERPROFILE", "C:/Users/Lido"))
    candidates.extend([
        Path("C:/Program Files/Android/Android Studio/jbr"),
        *sorted((profile / "AppData/Local/Google").glob(
            "AndroidStudio*/tmp/patch-update/jre"), reverse=True),
        *sorted(Path("C:/Program Files/Java").glob("jdk*"), reverse=True),
    ])
    for candidate in candidates:
        if (candidate / "bin/javac.exe").is_file():
            return candidate.resolve()
    raise RuntimeError("JDK not found; pass --java-home or set JAVA_HOME.")


def find_sdk(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else []
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(name):
            candidates.append(Path(os.environ[name]))
    profile = Path(os.environ.get("USERPROFILE", "C:/Users/Lido"))
    candidates.append(profile / "AppData/Local/Android/Sdk")
    for candidate in candidates:
        if (candidate / "build-tools").is_dir():
            return candidate.resolve()
    raise RuntimeError("Android SDK not found; pass --sdk or set ANDROID_HOME.")


def version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(item) for item in path.name.replace("android-", "").split(".")
                 if item.isdigit())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-home")
    parser.add_argument("--sdk")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--selftest", action="store_true",
                        help="Build isolated Android mechanism tests, not the module.")
    options = parser.parse_args()
    jdk = find_java(options.java_home)
    sdk = find_sdk(options.sdk)
    tools = max((p for p in (sdk / "build-tools").iterdir()
                 if (p / "aapt2.exe").is_file()), key=version_key)
    android_jar = max((p for p in (sdk / "platforms").iterdir()
                       if (p / "android.jar").is_file()), key=version_key) / "android.jar"
    java, javac, keytool = [jdk / f"bin/{name}.exe"
                            for name in ("java", "javac", "keytool")]
    api = ROOT / "tools/deps/xposed-api-82.jar"
    api.parent.mkdir(parents=True, exist_ok=True)
    if not api.exists():
        if options.offline:
            raise RuntimeError("Missing tools/deps/xposed-api-82.jar.")
        urllib.request.urlretrieve(API_URL, api)
    if hashlib.sha256(api.read_bytes()).hexdigest() != API_SHA256:
        raise RuntimeError("Xposed API SHA256 mismatch; refusing to compile.")

    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    main_source = ROOT / "app/src/main"
    # TemporaryDirectory is created only under this resolved build directory.
    with tempfile.TemporaryDirectory(prefix="compile-", dir=build) as temporary:
        work = Path(temporary)
        assert work.resolve().is_relative_to(build.resolve())
        resources = work / "resources.zip"
        unsigned = work / "unsigned.apk"
        classes = work / "classes"
        dex = work / "dex"
        classes.mkdir()
        dex.mkdir()
        run(tools / "aapt2.exe", "compile", "--dir", main_source / "res",
            "-o", resources)
        run(tools / "aapt2.exe", "link", "-I", android_jar,
            "--manifest", ROOT / "tests/AndroidManifest.xml" if options.selftest
            else main_source / "AndroidManifest.xml",
            "-A", main_source / "assets", "-o", unsigned, resources)
        if options.selftest:
            sources = [
                main_source / "java/io/github/annjam/timezone/TimezonePolicy.java",
                *sorted((ROOT / "tests/java").rglob("*.java")),
            ]
        else:
            sources = sorted((main_source / "java").rglob("*.java"))
        run(javac, "-encoding", "UTF-8", "--release", "8", "-Xlint:-options",
            "-classpath", os.pathsep.join(map(str, (android_jar, api))),
            "-d", classes, *sources)
        class_jar = work / "module-classes.jar"
        with zipfile.ZipFile(class_jar, "w") as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes).as_posix())
        run(java, "-cp", tools / "lib/d8.jar", "com.android.tools.r8.D8",
            "--release", "--min-api", "26", "--lib", android_jar,
            "--classpath", api, "--output", dex, class_jar)
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            archive.write(dex / "classes.dex", "classes.dex")
        aligned = work / "aligned.apk"
        run(tools / "zipalign.exe", "-f", "4", unsigned, aligned)

        signing = ROOT / "signing"
        signing.mkdir(exist_ok=True)
        keystore = signing / "local-test.p12"
        if not keystore.exists():
            run(keytool, "-genkeypair", "-keystore", keystore, "-storetype", "PKCS12",
                "-storepass", "android", "-keypass", "android", "-alias", "annjam-local",
                "-keyalg", "RSA", "-keysize", "3072", "-validity", "10000",
                "-dname", "CN=ANN JAM Timezone Local Test", "-noprompt")
        output = build / ("ANNJAM-Timezone-selftest.apk" if options.selftest
                          else "ANNJAM-Timezone-1.0.0.apk")
        run(java, "-jar", tools / "lib/apksigner.jar", "sign", "--ks", keystore,
            "--ks-key-alias", "annjam-local", "--ks-pass", "pass:android",
            "--key-pass", "pass:android", "--v4-signing-enabled", "false",
            "--out", output, aligned)
        run(java, "-jar", tools / "lib/apksigner.jar", "verify", "--verbose",
            "--print-certs", output)
        run(tools / "zipalign.exe", "-c", "4", output)
        with zipfile.ZipFile(output) as archive:
            if not options.selftest:
                assert archive.read("assets/xposed_init").strip() == (
                    b"io.github.annjam.timezone.TimezoneModule")
            assert archive.read("classes.dex").startswith(b"dex\n")
            assert not any(p.startswith("lib/") for p in archive.namelist())
            # API dependency must never be bundled into the module.
            assert not any("de/robv/android/xposed" in p for p in archive.namelist())
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        (build / f"{output.name}.sha256").write_text(
            f"{digest}  {output.name}\n", encoding="ascii")
        print(f"\nBuilt: {output}\nSHA256: {digest}")


if __name__ == "__main__":
    main()
