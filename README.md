# ANN JAM Force JST

让 ANN JAM 单独使用日本时区的 LSPosed 模块。

[下载 APK](https://github.com/LidoCKT/ANN-JAM-Force-JST/releases/latest) · [反馈问题](https://github.com/LidoCKT/ANN-JAM-Force-JST/issues)

针对 `jp.annjam` 的 LSPosed 模块。目标是在手机维持 UTC+8 的同时，让 ANN JAM 使用 `Asia/Tokyo`（UTC+9），修正节目入口延迟开放的问题。

针对 ANN JAM 1.6.1（`jp.annjam`）制作。2026-11-05，用户已反馈插件在真机上运行正常；设备型号、Android 和 LSPosed 版本暂未记录。其他设备或应用版本仍需验证。

## 安装和验证

1. 从 [Releases](https://github.com/LidoCKT/ANN-JAM-Force-JST/releases) 下载并安装 `ANNJAM-Timezone-1.0.0.apk`。
2. 在 LSPosed 管理器中启用 **ANN JAM 日本时区**。
3. 作用域只勾选 **ANN JAM**（`jp.annjam`）。无需勾选系统框架或模块自身。
4. 手机系统保持 UTC+8，在系统设置中**强制停止 ANN JAM**，然后重新打开。如果未注入，重启手机再试。
5. 在节目按日本时间已经开始的情况下，检查入口能否及时开放。
6. 在 LSPosed 日志中搜索 `ANNJAM-TZ`，正常启动日志应包含：

```text
ANNJAM-TZ Application.attach process=jp.annjam java=Asia/Tokyo offsetMillis=32400000 libcTZ=Asia/Tokyo environmentOK=true
```

上述日志确认 Java 默认时区和进程的原生环境变量，不能单独证明 Flutter 实际计算结果或入口修复成功。出现 `FAILED` 时请提供对应日志，以及 Android、LSPosed 和 ANN JAM 版本。

恢复原状：停用模块，强制停止 ANN JAM 并重新打开。模块没有配置数据，无需清除 ANN JAM 数据。

## 维护者提交源码

首次在终端登录 GitHub：

```powershell
git credential-manager github login --username LidoCKT --browser
```

之后在项目目录运行 `.\publish.ps1`，即可自动同步源码、提交并推送到本项目仓库。`.\publish.ps1 -Preview` 可离线预览文件清单。详细行为和网页发布 APK 的步骤见 [PUBLISH.md](PUBLISH.md)。

## 实现

- 使用传统 Xposed API 82，面向支持该 API 的 LSPosed；最低 Android 8.0（API 26）。
- 在 `handleLoadPackage` 中严格检查包名，针对该应用的每个已加载进程分别生效，不在 zygote 中设置时区。
- 启动时用 `android.system.Os.setenv("TZ", "Asia/Tokyo", true)` 设置实际 libc 环境。不是仅修改 Java 系统属性。
- Android 8.0 起，bionic `localtime_r()` 会刷新时区。Dart 在 Android 上通过该函数读取本地时区偏移和名称，因此先尝试这条无需 Native Hook 的路径。
- 同时设置 Java 和 ICU 默认时区，并 Hook 默认时区读写、`ZoneId.systemDefault()`，防止 Java 端缓存重置后回到系统时区。
- Hook `Os.setenv` / `Os.unsetenv` 中涉及 `TZ` 的调用，保持进程内设置。直接从其他原生库调用 `setenv` 不经过这些 Java Hook；若目标应用有这样的行为，需要继续分析。
- `Application.attach` 前再次应用设置，尽量早于 Flutter 引擎和应用插件初始化。
- 不修改 Unix 时间戳、系统时钟或系统时区，不需要模块自身申请联网权限。

本模块会让 ANN JAM 进程内所有使用默认时区的功能按东京时间工作，包括第三方 SDK。未改动应用安装包，也不处理账户订阅或地区限制。若未来版本更换时区实现或提前创建 Flutter 引擎，需要重新验证。

技术依据：

- Android Os.setenv：https://developer.android.com/reference/android/system/Os
- Android O bionic TZ 优先于系统时区：https://android.googlesource.com/platform/bionic/+/ea87716696bf635706b6f3fa56b8a145add83aff/libc/tzcode/localtime.c
- bionic localtime_r 自动刷新：https://github.com/aosp-mirror/platform_bionic/blob/master/libc/tzcode/localtime.c
- Dart Android 本地时间路径：https://github.com/dart-lang/sdk/blob/main/runtime/vm/os_android.cc
- Xposed 加载入口：https://api.xposed.info/reference/de/robv/android/xposed/IXposedHookLoadPackage.html

这些是方案依据，尚未证明安装包内所带 Dart 引擎与当前上游源码逐字一致。

## 构建

需要 Windows、Python 3.10+、JDK 17+、Android SDK（platforms、build-tools 34+）。

```powershell
.\build.ps1 -JavaHome 'C:\path\to\jdk' -AndroidSdk 'C:\path\to\Android\Sdk'
```

脚本会尝试发现本机 JDK 和 SDK；支持 `JAVA_HOME`、`ANDROID_HOME`、`ANDROID_SDK_ROOT`。

不依赖 Gradle。唯一额外编译依赖为官方 Xposed API 82，放在 `tools/deps/xposed-api-82.jar`，固定 SHA256：

```text
f48c635f1c7469fdec0e00ad2ea0b7a6b2f5b55065784a35b7ca3a84615e8e25
```

首次构建缺失时下载；已有依赖时可使用 `.\build.ps1 -Offline`。Xposed API 仅用于编译，不打包进 APK。

当前 APK 使用首次构建时生成的自签名证书。维护者请保存本地的 `signing/local-test.p12`，后续构建使用同一签名，以便用户覆盖安装更新。源码包不包含该私钥，新克隆的项目首次构建会生成独立签名。签名目录已加入 `.gitignore`。

构建过程自动检查 APK 签名、zip 对齐、DEX 和 Xposed 入口，并输出 SHA256 文件。

## 已完成的验证

2026-11-05，在 Android API 36.1 x86_64 模拟器中：

- 模块 APK 安装成功，说明页面冷启动成功。
- 14 项机制自测通过，包括包名隔离、Java / ICU / ZoneId 默认时区、可变时区对象隔离、重复设置、跨午夜日期，以及真实时钟保持不变。
- 用进程实际 `TZ` 值启动的原生 `date` 子进程，将 `2026-11-05T15:30:00Z` 转为 `2026-11-06T00:30:00 +0900`。
- APK v2 / v3 签名和 zip 对齐检查通过。

自测调用正式代码中的 `TimezonePolicy`，没有使用 LSPosed。原生测试是子进程检查，不能替代目标应用中的运行测试。模拟器以只读、无快照保存模式运行。

另外，用户已反馈插件在真机上运行正常；该反馈没有附带逐项日志或设备环境信息。

复现机制自测：

```powershell
python .\tools\build.py --offline --selftest
adb -s YOUR_TEST_DEVICE install -r .\build\ANNJAM-Timezone-selftest.apk
adb -s YOUR_TEST_DEVICE shell am instrument -w io.github.annjam.timezone.selftest/io.github.annjam.timezone.SelfTestInstrumentation
```

`ANNJAM-Timezone-selftest.apk` 是开发验证工具，日常只需安装正式模块 APK。
