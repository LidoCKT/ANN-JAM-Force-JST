# Validation — 2026-11-05

## Built module

- File: `build/ANNJAM-Timezone-1.0.0.apk`
- Package: `io.github.annjam.timezone`
- Target app: `jp.annjam`
- Minimum SDK: 26; target SDK: 35; compile SDK: 36
- Signature schemes: v2 and v3 verified by Android SDK apksigner
- Zip alignment: verified by Android SDK zipalign
- SHA256: `b85b076595bdc74944b9f971cff59cf2b6d26b76b1de5f392cc0448813781f0e`

## Android runtime

Existing API 36.1 x86_64 Google Play AVD, launched headlessly with
`-read-only -no-snapshot`. No physical Android device was connected.

Module APK:

```text
Performing Streamed Install
Success
Status: ok
LaunchState: COLD
Activity: io.github.annjam.timezone/.MainActivity
TotalTime: 2963
```

Isolated mechanism instrumentation using the production `TimezonePolicy`:

```text
PASS exact package
PASS reject other apps
PASS UTC+8 baseline
PASS real clock unchanged
PASS native TZ environment
PASS Java default
PASS Java offset
PASS ZoneId default
PASS cross midnight
PASS Calendar local date
PASS ICU default cache
PASS mutable instance isolation
PASS idempotent apply
PASS bionic child date
native date: 2026-11-06T00:30:00 +0900
```

The native date test explicitly copies `Os.getenv("TZ")` into a child process.
It establishes bionic's timezone interpretation in that child. It is not an
in-process Flutter test.

## User-device feedback — 2026-11-05

The user reported: “我已经测试插件正常运行了” (“I have tested the module;
it works normally”). This confirms user-reported operation on a physical device.
No device model, Android version, LSPosed version, or per-hook logs were provided.
The supplied target APK used during development was ANN JAM 1.6.1.

This feedback is separate from the automated emulator mechanism checks above.
Other device and app-version combinations remain unverified.
