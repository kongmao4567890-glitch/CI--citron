#!/bin/bash
set -ex

# Citron 汉化补丁脚本
# 在 Clangtron 构建之前运行，启用翻译并替换翻译文件

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CITRON_DIR="${1:-./citron}"

echo "=== 应用汉化补丁 ==="
echo "Citron 源码目录: ${CITRON_DIR}"

# 1. 替换 zh_CN.ts 为完整汉化版
if [ -f "${SCRIPT_DIR}/translations/zh_CN.ts" ]; then
    echo "替换 zh_CN.ts..."
    cp "${SCRIPT_DIR}/translations/zh_CN.ts" "${CITRON_DIR}/dist/languages/zh_CN.ts"
    echo "zh_CN.ts 已替换 ($(wc -l < "${CITRON_DIR}/dist/languages/zh_CN.ts") 行)"
else
    echo "错误: translations/zh_CN.ts 不存在!"
    exit 1
fi

# 2. 在 build-clangtron-windows.sh 的 cmake 参数中添加 ENABLE_QT_TRANSLATION=ON
BUILD_SCRIPT="${CITRON_DIR}/build-clangtron-windows.sh"
if [ -f "${BUILD_SCRIPT}" ]; then
    echo "修改 build-clangtron-windows.sh 启用翻译..."
    # 在 _CMAKE_ARGS 数组中添加 ENABLE_QT_TRANSLATION=ON
    # 在 "-DCITRON_USE_PRECOMPILED_HEADERS=OFF" 行后插入
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

# 3. 确认补丁结果
echo "=== 补丁验证 ==="
grep "ENABLE_QT_TRANSLATION" "${BUILD_SCRIPT}" && echo "✓ 翻译已启用" || echo "✗ 翻译未启用"
head -5 "${CITRON_DIR}/dist/languages/zh_CN.ts"
echo "..."
grep -c '<message>' "${CITRON_DIR}/dist/languages/zh_CN.ts"
echo "条翻译消息"

echo "=== 汉化补丁完成 ==="
