# 发布到 LidoCKT/ANN-JAM-Force-JST

## 一条命令提交源码

本机已安装 Git 和 Git Credential Manager。首次使用先在自己的终端登录：

```powershell
git credential-manager github login --username LidoCKT --browser
```

然后在项目文件夹中运行：

```powershell
.\publish.ps1 -Message 'Release ANN JAM Force JST v1.0.0'
```

以后每次改好源码，再运行 `.\publish.ps1` 即可提交并推送。没有变更时不会创建新提交。

可先检查将上传的文件，预览不会联网：

```powershell
.\publish.ps1 -Preview
```

脚本每次在 `build/github-publish-*` 中克隆远程默认分支，再同步源码、提交和正常推送。远程仓库为空时使用 `main`。仓库已有历史会保留，脚本不会强制推送。远程若有分支保护、权限不足或并发更新，Git 会报告错误，克隆目录会保留。

签名私钥、APK、XAPK 和构建缓存不进入源码提交。APK 继续通过下面的 Release 流程上传，这个脚本只提交源码。

提交身份优先使用当前 Git 配置；没有配置时默认使用 `LidoCKT` 和 `LidoCKT@users.noreply.github.com`。可通过 `-AuthorName`、`-AuthorEmail` 覆盖；只写入本次克隆的配置，不修改全局设置。

提交工具的本地测试：

```powershell
python -m unittest discover -s .\tests -p test_publish.py -v
```

测试只使用 `build/` 下的临时本地 Git 仓库，不连接 GitHub。已验证空仓库首次发布、保留历史和仓库其他文件、无变更跳过提交、删除之前管理的源码文件，以及排除签名和构建产物。

## 网页上传

如果使用 `ANN-JAM-Force-JST-v1.0.0-publish.zip`：解压后，`repository/` 中的内容用于上传源码，`release-assets/` 中的文件用于 Release 附件，发布说明在 `RELEASE_NOTES.md`。

## 上传源码

1. 解压 `ANNJAM-Timezone-1.0.0-source.zip`，进入其中的 `annjam-timezone` 文件夹。
2. 打开 GitHub 仓库 `https://github.com/LidoCKT/ANN-JAM-Force-JST`。
3. 点击 **Add file → Upload files**。如果仓库为空，点击 **uploading an existing file**。
4. 把解压文件夹里面的内容上传到仓库根目录，包括 `app/`、`tests/`、`tools/`、`.gitignore`、`README.md`、`build.ps1` 等。不要只上传 ZIP 文件。
5. 提交说明填写 `Initial release: ANN JAM Force JST v1.0.0`，完成提交。若仓库要求通过分支和 PR 合并，请按页面提示操作。

准备的源码 ZIP 已排除签名目录、原始 ANN JAM XAPK、编译依赖缓存和构建产物。维护者本机的签名私钥应自行保存，用于今后签名更新。

## 发布安装包

1. 在仓库的 **Releases** 中选择 **Create a new release**。
2. 创建标签 **`v1.0.0`**，目标选择刚上传源码的分支。
3. 标题填写 **`ANN JAM Force JST v1.0.0`**。
4. 描述粘贴 `RELEASE_NOTES.md` 的内容。
5. 将以下两个文件拖入附件区域：
   - `ANNJAM-Timezone-1.0.0.apk`
   - `ANNJAM-Timezone-1.0.0.apk.sha256`
6. 检查附件上传完成后，点击 **Publish release**。

上传的 APK 应保持为已经测试通过的原文件。本次只更新文档，不重新编译或更换签名。

GitHub 操作参考：

- https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
