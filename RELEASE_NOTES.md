ANN JAM Force JST v1.0.0

首个版本：让 ANN JAM 在手机使用 UTC+8 时，仍按日本时区 `Asia/Tokyo` 判断本地时间，解决节目入口因时区差异延迟开放的问题。

### 使用方法

1. 下载并安装附件 `ANNJAM-Timezone-1.0.0.apk`。
2. 在 LSPosed 中启用「ANN JAM 日本时区」。
3. 作用域只勾选 ANN JAM（`jp.annjam`）。
4. 手机保持日常使用的时区，强制停止 ANN JAM 后重新打开。

### 兼容与验证

- 最低 Android 8.0，需要支持传统 Xposed API 的 LSPosed 环境。
- 基于 ANN JAM 1.6.1 制作。
- 用户已反馈真机运行正常；设备和系统版本暂未记录。
- 14 项模拟器时区机制测试、APK 签名及对齐检查通过。

### 排查与恢复

未生效时先重启手机；仍有问题，请提供 Android、LSPosed、ANN JAM 版本，以及包含 `ANNJAM-TZ` 的 LSPosed 日志。

停用模块并强制停止、重新打开 ANN JAM，即可恢复原来的进程时区行为。

APK SHA256：

```text
b85b076595bdc74944b9f971cff59cf2b6d26b76b1de5f392cc0448813781f0e
```
