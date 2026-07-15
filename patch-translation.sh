#!/bin/bash
set -ex

# Citron 汉化补丁脚本 v2
# 在 Clangtron 构建之前运行：
#   1. 替换翻译文件为完整汉化版
#   2. 启用翻译编译 (ENABLE_QT_TRANSLATION=ON)
#   3. 修改默认语言为中文 (zh_CN)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CITRON_DIR="${1:-./citron}"

echo "=== 应用汉化补丁 v2 ==="
echo "Citron 源码目录: ${CITRON_DIR}"

# -------------------------------------------------------
# 1. 替换 zh_CN.ts 为完整汉化版
# -------------------------------------------------------
if [ -f "${SCRIPT_DIR}/translations/zh_CN.ts" ]; then
    echo "替换 zh_CN.ts..."
    cp "${SCRIPT_DIR}/translations/zh_CN.ts" "${CITRON_DIR}/dist/languages/zh_CN.ts"
    echo "zh_CN.ts 已替换 ($(wc -l < "${CITRON_DIR}/dist/languages/zh_CN.ts") 行)"
else
    echo "错误: translations/zh_CN.ts 不存在!"
    exit 1
fi

# -------------------------------------------------------
# 2. 在 build-clangtron-windows.sh 中启用翻译编译
# -------------------------------------------------------
BUILD_SCRIPT="${CITRON_DIR}/build-clangtron-windows.sh"
if [ -f "${BUILD_SCRIPT}" ]; then
    echo "修改 build-clangtron-windows.sh 启用翻译..."
    if ! grep -q "ENABLE_QT_TRANSLATION" "${BUILD_SCRIPT}"; then
        sed -i 's/"-DCITRON_USE_PRECOMPILED_HEADERS=OFF"/"-DCITRON_USE_PRECOMPILED_HEADERS=OFF" "-DENABLE_QT_TRANSLATION=ON"/' "${BUILD_SCRIPT}"
        echo "已添加 -DENABLE_QT_TRANSLATION=ON"
    else
        echo "ENABLE_QT_TRANSLATION 已存在，跳过"
    fi
else
    echo "错误: build-clangtron-windows.sh 不存在!"
    exit 1
fi

# -------------------------------------------------------
# 3. 修改 main.cpp: 默认语言改为 zh_CN
# -------------------------------------------------------
MAIN_CPP="${CITRON_DIR}/src/citron/main.cpp"
if [ -f "${MAIN_CPP}" ]; then
    echo "修改 main.cpp 默认语言为 zh_CN..."

    # 3a. 修改 LoadTranslation(): 空语言时默认 zh_CN 而非系统 locale
    # 原代码:
    #   if (UISettings::values.language.GetValue().empty()) {
    #       // If the selected language is empty, use system locale
    #       loaded = translator.load(QLocale(), {}, {}, QStringLiteral(":/languages/"));
    #   }
    # 改为:
    #   if (UISettings::values.language.GetValue().empty()) {
    #       // Default to Chinese (Simplified)
    #       UISettings::values.language = std::string("zh_CN");
    #       loaded = translator.load(QStringLiteral("zh_CN"), QStringLiteral(":/languages/"));
    #   }
    sed -i 's|// If the selected language is empty, use system locale|// Default to Chinese (Simplified)|' "${MAIN_CPP}"
    sed -i 's|loaded = translator.load(QLocale(), {}, {}, QStringLiteral(":/languages/"));|UISettings::values.language = std::string("zh_CN"); loaded = translator.load(QStringLiteral("zh_CN"), QStringLiteral(":/languages/"));|' "${MAIN_CPP}"

    # 3b. 修改加载失败时的回退语言: en -> zh_CN
    # 原代码: UISettings::values.language = std::string("en");
    # 改为:   UISettings::values.language = std::string("zh_CN");
    #         loaded = translator.load(QStringLiteral("zh_CN"), QStringLiteral(":/languages/"));
    #         if (loaded) { qApp->installTranslator(&translator); }
    sed -i '/UISettings::values.language = std::string("en");/{
        s|UISettings::values.language = std::string("en");|UISettings::values.language = std::string("zh_CN"); loaded = translator.load(QStringLiteral("zh_CN"), QStringLiteral(":/languages/")); if (loaded) { qApp->installTranslator(\&translator); }|
    }' "${MAIN_CPP}"

    # 3c. 修改 OnLanguageChanged: "en" 检查改为也处理 zh_CN
    # 原代码: if (UISettings::values.language.GetValue() != std::string("en")) {
    # 这里不改逻辑，只是确保 zh_CN 也能正确移除翻译器
    # 实际上原逻辑已经正确处理了所有非 "en" 的情况

    echo "main.cpp 已修改"
else
    echo "错误: main.cpp 不存在!"
    exit 1
fi

# -------------------------------------------------------
# 4. 验证补丁结果
# -------------------------------------------------------
echo "=== 补丁验证 ==="
echo "--- 翻译编译 ---"
grep "ENABLE_QT_TRANSLATION" "${BUILD_SCRIPT}" && echo "✓ 翻译已启用" || echo "✗ 翻译未启用"

echo "--- 默认语言 ---"
grep -n "zh_CN" "${MAIN_CPP}" | head -5

echo "--- 翻译文件 ---"
grep -c '<message>' "${CITRON_DIR}/dist/languages/zh_CN.ts"
echo "条翻译消息"

echo "=== 汉化补丁 v2 完成 ==="
