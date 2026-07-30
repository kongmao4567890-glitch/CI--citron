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
