# 🍋 The Official Citron Neo CI

[![GitHub Downloads](https://camo.githubusercontent.com/f7d99771b8c7be2c26f2ae567342d0f6224a81daf7362bad19031525d68ecbd8/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f646f776e6c6f6164732f636974726f6e2d6e656f2f43492f746f74616c3f6c6f676f3d676974687562266c6162656c3d476974487562253230446f776e6c6f616473)](https://github.com/citron-neo/CI/releases/latest) [![Build Citron Neo (Nightly)](https://github.com/citron-neo/CI/actions/workflows/build_nightly.yml/badge.svg)](https://github.com/citron-neo/CI/actions/workflows/build_nightly.yml) [![Build Citron Neo (Stable)](https://github.com/citron-neo/CI/actions/workflows/build_stable.yml/badge.svg)](https://github.com/citron-neo/CI/actions/workflows/build_stable.yml)

---

This repository makes Nightly builds for **x86_64** (Standard), **x86_64_v3** (CPU's that are from 2013+) & **aarch64** on Linux, and also Windows, Android & macOS builds! These builds are all produced @ 12 AM UTC every single day.

Would you like to submit a compatibility report for the emulator? You can do so here:

- [Submit Compatibility Report](https://github.com/citron-neo/Citron-Compatability)

---

Direct links for other information you may need can also be found below:

- [Latest Commits Can Be Found Here](https://github.com/citron-neo/emulator/commits/main)

- [Latest Android Nightly Release](https://github.com/citron-neo/CI/releases/tag/nightly-android)

- [Latest Linux Nightly Release](https://github.com/citron-neo/CI/releases/tag/nightly-linux)

- [Latest Windows Nightly Release](https://github.com/citron-neo/CI/releases/tag/nightly-windows)

- [Latest macOS Nightly Release](https://github.com/citron-neo/CI/releases/tag/nightly-macos)

---

# 🇨🇳 Citron 汉化版 (Windows)

除上游构建外，本仓库还产出一个 **Windows 简体中文版**：

- **下载**：[Latest Windows 汉化版 Release](../../releases/tag/nightly-windows-zh)
- **工作流**：[`build-windows-zh.yml`](.github/workflows/build-windows-zh.yml) —
  可手动触发 (`workflow_dispatch`)，推送到 `claude/**` 分支时自动触发，每天 00:30 UTC 定时构建。

## 与上游的差异

| 功能 | 说明 |
| --- | --- |
| 完整汉化 | Qt 前端全部 2258 条可翻译字符串均已汉化，构建时强制校验，漏翻即构建失败 |
| 默认中文 | 首次启动即为简体中文；仍可在「设置 → 界面」改回其他语言 |
| 金手指管理器 | `工具 → 金手指管理器`：逐条勾选金手指、搜索、按来源分组、全选/全不选/反选，游戏运行中即时生效 |
| 金手指总开关 | `设置 → 系统 → 启用金手指`：暂停全部金手指而不丢失已勾选的项目 |

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `translations/zh_CN.ts` | 翻译源文件（唯一真实来源） |
| `translations/zh_CN.qm` | 预编译的翻译，`lrelease` 不可用时作为兜底 |
| `patches/src/citron/` | 新增的模拟器源码（金手指管理器对话框） |
| `tools/patch_citron.py` | 对上游源码打补丁：嵌入翻译、默认中文、装配金手指管理器 |
| `tools/verify_translation.py` | 汉化覆盖率校验（CI 门禁） |
| `patch-translation.sh` | 兼容入口，转发到 `tools/patch_citron.py` |

## 本地使用

```bash
git clone https://github.com/citron-neo/emulator.git citron
./patch-translation.sh ./citron          # 打补丁
python3 tools/verify_translation.py ./citron   # 校验汉化完整性
```

上游新增字符串后刷新翻译：

```bash
python3 tools/verify_translation.py ./citron --write
# 在 translations/zh_CN.ts 中补全新出现的 <translation type="unfinished"> 条目
python3 tools/verify_translation.py ./citron --strict-refresh
```

> 补丁脚本的每一处修改都锚定在上游源码的精确片段上。上游改动导致锚点失效时脚本会直接报错退出，
> 而不会静默跳过 —— 静默跳过会产出一个"看起来构建成功、实际是英文"的包。


---

# READ THIS IF YOU HAVE ISSUES

If you are on wayland (specially GNOME wayland) and get freezes or crashes, you are likely affected by an issue that affects all Qt6 apps.

To fix it simply set the env variable `QT_QPA_PLATFORM=xcb`

**Also, are you looking for AppImages of other emulators? Check:** [AnyLinux-AppImages](https://pkgforge-dev.github.io/Anylinux-AppImages/)

---

AppImage made using [sharun](https://github.com/VHSgunzo/sharun), which makes it extremely easy to turn any binary into a portable package without using containers or similar tricks.

**These AppImages bundle everything and should work on any Linux distro, even on musl based ones.**

A `tar.zst` portable archive of the same build is also published alongside the AppImage on each Linux release, for users who prefer an install-free tarball over the AppImage format.

These AppImages work without fuse2 as it can use fuse3 instead, it can also work without fuse at all thanks to the [uruntime](https://github.com/VHSgunzo/uruntime)


---

Thank-you for being apart of & using Citron Neo, we value all members of the community whom help shape the emulator into what it is today!

- The Citron Neo Team
