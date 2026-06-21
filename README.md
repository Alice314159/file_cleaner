# 🧹 File Cleaner

跨平台项目目录清理工具，支持 Windows 和 macOS。  
A cross-platform project directory cleanup tool for Windows & macOS.

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 📂 路径下拉历史 | 最多保存15条最近路径，重启后自动恢复 |
| 🔁 递归遍历 | 遍历所有子文件夹，跳过已匹配的子树 |
| ☑ 勾选清理 | 扫描后可逐项勾选，再批量移到系统回收站 |
| ➕ 自定义规则 | 运行时添加/删除文件夹名、文件后缀、完整文件名清理目标，立即生效 |
| 📊 结果摘要 | 展示扫描数量、已选数量、预计释放大小、单项大小和修改时间 |
| 🔎 快速筛选 | Clean Targets 支持搜索、全选/全不选和风险等级提示 |
| 🚧 扫描控制 | 支持排除路径/glob 规则和最大扫描深度 |
| 🔁 规则导入导出 | Clean Targets、排除规则和扫描深度可导出/导入 JSON |
| 💾 配置持久化 | 规则和路径历史保存在 `~/.file_cleaner_config.json` |

**默认清理目标：**
- 文件夹：`__pycache__` / `.pytest_cache` / `.mypy_cache` / `.ruff_cache` / `.egg-info`
- 文件扩展名：`.pyc` / `.pyo`
- 完整文件名：`.DS_Store` / `Thumbs.db`

---

## 🚀 直接运行（开发模式）

```bash
# 安装依赖（仅需 Python 标准库，无额外依赖）
python3 cleaner_app.py
```

---

## 📦 打包为可执行文件

### macOS

```bash
chmod +x build.sh
./build.sh
```

产物：
- `dist/FileCleaner.app`  — 拖入 `/Applications` 即可使用
- 可选：生成 DMG 安装盘：
  ```bash
  hdiutil create -volname FileCleaner -srcfolder dist/FileCleaner.app \
    -ov -format UDZO dist/FileCleaner.dmg
  ```

### Windows

双击 `build.bat` 或在 CMD 中运行：

```bat
build.bat
```

产物：
- `dist\FileCleaner.exe`  — 单文件，双击即用

**可选：生成安装包（需要 [NSIS](https://nsis.sourceforge.io)）**

```bat
makensis installer.nsi
```

产物：`FileCleaner_Setup_1.0.0.exe`

---

## 🏗 项目结构

```
file_cleaner/
├── main.py             # 新入口
├── cleaner_app.py      # 兼容入口，转发到 main.py
├── file_cleaner.spec   # PyInstaller 打包配置
├── build.sh            # macOS 一键构建脚本
├── build.bat           # Windows 一键构建脚本
├── installer.nsi       # NSIS Windows 安装包脚本
├── config/             # 默认配置、配置读写和规范化
├── core/               # 扫描、匹配、删除和数据模型
├── workers/            # 后台扫描/删除 worker
├── ui/                 # Tk UI 主窗口、面板、弹窗、控件
├── services/           # 导入导出、路径历史等服务
├── utils/              # 格式化、日志、文件工具
└── README.md
```

---

## 🎨 添加图标（可选）

1. 准备 `512×512` PNG
2. **macOS**：转为 `.icns`
   ```bash
   mkdir icon.iconset
   sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
   iconutil -c icns icon.iconset -o assets/icon.icns
   ```
3. **Windows**：转为 `.ico`（可用 ImageMagick）
   ```bash
   magick convert icon.png -resize 256x256 assets/icon.ico
   ```
4. 取消注释 `file_cleaner.spec` 中的 `icon=` 行

---

## ⚙️ 配置文件位置

| 平台 | 路径 |
|------|------|
| macOS / Linux | `~/.file_cleaner_config.json` |
| Windows | `C:\Users\<你的用户名>\.file_cleaner_config.json` |

如需重置所有设置，删除该文件即可。

Clean Targets 使用可读写 JSON 结构。内置项 `builtin: true` 只能禁用，不能删除；自定义项 `builtin: false` 可以删除。

```json
{
  "targets": [
    {
      "id": "pycache",
      "type": "folder",
      "pattern": "__pycache__",
      "enabled": true,
      "builtin": true,
      "match_mode": "exact"
    },
    {
      "id": "custom_folder_turbo",
      "type": "folder",
      "pattern": ".turbo",
      "enabled": true,
      "builtin": false,
      "match_mode": "exact"
    }
  ]
}
```

---

## 📋 依赖

- Python 3.8+
- 仅使用标准库（`tkinter` / `pathlib` / `threading` / `shutil` / `subprocess` / `fnmatch` / `json`）
- 打包工具：`pyinstaller`（仅构建时需要）
- Windows 安装包：NSIS（可选）
