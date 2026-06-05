# Changelog

## [Unreleased]

### Added

- **"Cosmic Glass" UI 设计系统**
  - 玻璃拟态面板（backdrop-blur）、Indigo→Cyan 渐变色彩、极光动画欢迎页。
  - 卡片化设置页（hover 高亮、focus 发光环、修改指示点呼吸动画）。
  - 浮动图标 + 键盘快捷键提示欢迎页。
  - 影响文件: `frontend/src/index.css`, `frontend/src/pages/EditorPage.jsx`

- **跨平台全面适配 (Linux/Windows/macOS)**
  - 路径分隔符 `os.sep` 替代硬编码 `/`；venv `Scripts/python.exe` vs `bin/python3`。
  - 所有 `open()` 加 `encoding="utf-8"`；`sys.platform` 检测 GUI。
  - `subprocess` 加 `CREATE_NO_WINDOW`、超时、`os.pathsep`。
  - `os.makedirs(exist_ok=True)` 替代 `os.mkdir`。
  - 影响文件: 10+ 个 Python 文件

- **安全加固**
  - `api/execute.py`, `api/export.py` 添加路径穿越防护（`_resolve()`）。
  - TraceViewer 中 `marked()` 输出通过 `DOMPurify.sanitize()`（XSS）。
  - `export.py` 中 trace JSON 转义 `</`（XSS）。
  - 未知 settings key 返回 400 而非静默接受；损坏的 `settings.json` 回退默认值。
  - 影响文件: 8 个文件

- **Python 包导入规范化**
  - `core/execute.py`、`execute_util.py`、`arxiv_util.py` 裸导入 → `walkabout.core.xxx`。
  - PyInstaller 导入兼容性修复。
  - 影响文件: `walkabout/core/`, `walkabout/runner.py`

- **GitHub Release 自动打包**
  - `.github/workflows/release.yml`: tag push 触发 PyInstaller 构建。
  - Linux 和 Windows 单文件可执行包自动上传到 Release。
  - in-process trace 执行（PyInstaller 打包后无需子进程）。

- **双主题设计系统 — CSS 变量驱动的暗色/暖白双主题**
  - 完整的 CSS 自定义属性体系（颜色、阴影、间距、圆角、过渡）。
  - 暗色主题（深黑 `#191b1e`）和暖白亮色主题（米白 `#f3f2ee`）。
  - 工具栏 ☀/☾ 按钮一键切换，设置页 `appearance.theme` 修改即时生效。
  - `index.html` 内联脚本防闪烁（React 加载前就读 localStorage 设置主题）。
  - Monaco Editor 自动跟随系统主题（`vs-dark` ↔ `vs`）。
  - 影响文件: `frontend/src/index.css`, `frontend/src/theme.js`, `frontend/src/pages/EditorPage.jsx`, `frontend/src/pages/SettingsPage.jsx`, `frontend/src/components/Editor.jsx`, `frontend/index.html`

- **前端 UI 全面美化**
  - 全新设计系统：系统字体栈（SF Pro / Segoe UI / Roboto），无需外部字体 CDN。
  - 柔和色调、过渡动效、按钮按压反馈、Focus 环、自定义滚动条。
  - 欢迎页、进度条、Toast 通知、Markdown 渲染、环境变量面板全部统一风格。
  - Zen 模式退出按钮半透明悬浮。
  - 影响文件: `frontend/src/index.css`, `frontend/src/TraceViewer.jsx`

- **导出 HTML 隐藏 text() 调用代码行**
  - standalone viewer 的 `renderLines()` 中跳过以 `text(` 开头的代码行，仅保留渲染后的 Markdown 输出，界面更干净。
  - 影响文件: `walkabout/export.py`

- **内容导出模式(content-only)内联显示变量变化**
  - content-only 模式下，每一步的 env 变量变化以行内形式直接显示在渲染内容下方，无需单独的环境变量面板。
  - 新增 `.step-env` CSS 样式。
  - 影响文件: `walkabout/export.py`

- **导出默认改为完整模式（代码 + 渲染 + 环境面板）**
  - `ExportRequest.content_only` 默认值从 `True` 改为 `False`，保留源码和环境面板。
  - `export_and_save()` 调用 `export_note()` 时传递 `strip_source=True`，在完整模式下清理未引用的源码行。
  - 影响文件: `walkabout/api/export.py`

- **F4: 导出为独立 HTML — 不依赖 Python 后端的可分享 Walkthrough**
  - `walkabout/export.py`: 将 trace JSON 打包为自包含 HTML（嵌入 trace 数据 + 样式 + 渲染脚本，CDN 加载 highlight.js/marked/MathJax 实现语法高亮/Markdown/数学公式）。
  - `POST /api/export`: 后端 API 一键执行 note → 生成 HTML → 返回下载（`Content-Disposition: attachment`）。
  - 前端工具栏 ↓ Export 按钮：Run 之后一键下载独立 HTML，支持离线浏览。
  - standalone viewer 功能：步骤导航（←/→）、步过（Shift+←/→）、原始模式切换、文件选择、变量面板（可拖动）、行号跳转、Latex 公式渲染。
  - 影响文件: `walkabout/export.py`, `walkabout/api/export.py`, `walkabout/app.py`, `frontend/src/api.js`, `frontend/src/pages/EditorPage.jsx`, `frontend/src/index.css`

- **Zen 模式 — 隐藏侧边栏 + 工具栏，纯净编辑体验**
  - 工具栏 ⊞ 按钮切换 Zen 模式：隐藏 FileBrowser 侧边栏、工具栏、安装栏，仅保留编辑器/查看器区域。
  - 自动触发 Fullscreen API；ESC 或浮动按钮退出 Zen 模式。
  - 影响文件: `frontend/src/pages/EditorPage.jsx`, `frontend/src/index.css`

- **文件状态通过 URL 持久化 — 设置页返回不丢失**
  - EditorPage 挂载时从 `?file=xxx` 查询参数恢复已打开文件，`selectNote()` 自动更新 URL。
  - 从 SettingsPage 返回 `/` 后自动重开上次编辑的文件。
  - 影响文件: `frontend/src/pages/EditorPage.jsx`

- **NOTES 文件夹/子目录支持**
  - 后端 `write_note()`/`create_note()` 自动创建 `__init__.py` 使子目录可导入为 Python 包，支持路径式文件名（如 `tutorial/intro.py`）。
  - 前端 FileBrowser 文件夹分组：按路径前缀自动归类文件为可折叠文件夹，新增文件输入框提示 `filename.py or path/name.py`。
  - 影响文件: `walkabout/api/notes.py`, `frontend/src/components/FileBrowser.jsx`, `frontend/src/index.css`

- **Trace 持久化 — 重启后保留上次执行的 trace**
  - 后端 `read_note()` 返回 `trace_url` 字段：打开文件时检查 `~/.walkabout/traces/` 下是否有对应的 trace JSON，若存在则自动恢复。
  - 前端 EditorPage 根据返回的 `trace_url` 恢复状态，无需重新 Run 即可查看上次执行结果。
  - 影响文件: `walkabout/api/notes.py`, `frontend/src/pages/EditorPage.jsx`

- **Monaco Editor 本地打包替代 CDN 加载**
  - 将 `monaco-editor` 通过动态 `import()` 进行代码分割：主 chunk 保持 1.3MB 实现快速初始渲染，编辑器 chunk（~3.8MB）在打开文件时才按需加载。
  - 消除每次打开文件时从 CDN 下载 ~30MB 的延迟，同时支持离线编辑。
  - 影响文件: `frontend/src/components/Editor.jsx`, `frontend/package.json`, `frontend/vite.config.js`

- **变量面板移至右上角**
  - 将 TraceViewer 的 env 面板从默认左下角移至右上角，拖拽改用右边缘定位 `(rx, y)`。
  - 影响文件: `frontend/src/TraceViewer.jsx`, `frontend/src/index.css`

- **Demo 新增数学公式渲染测试**
  - `demo_walkthrough.py` 新增 `math_formulas()` 模块，测试 MathJax 渲染行内公式（$...$）和块级公式（$$...$$）。执行: 141 步 / 38 个渲染。
  - 影响文件: `walkabout/examples/demo_walkthrough.py`

### Fixed

- **全面代码审查修复（两轮，40+ 个问题）**
  - 安全: XSS x2（DOMPurify + `</script>` 转义）、路径穿越 x2。
  - 崩溃: 缺 `import sys`、`settings.json` 损坏防护、单步 trace 除零。
  - 跨平台: `os.sep`、`os.makedirs`、`CREATE_NO_WINDOW`、`is_gui_available()` macOS/Wayland。
  - 代码质量: `link()` style 死代码、重复 import、插件异常日志、Toast 定时器清理、文件描述符关闭。
  - 配置: 未知 key 校验、`python`/`python3` fallback、arXiv HTTPS。
  - CI: 提交 `package-lock.json`（`npm ci` 需要）。
  - 影响文件: 24 个文件

- **pywebview GUI 黑屏 — localStorage 异常导致 React 渲染崩溃**
  - `theme.js` 中 `getCurrentTheme()` 在 pywebview 的 WebKitGTK/JavaScriptCore 引擎中抛出未捕获异常，传播到 React 渲染周期导致整个应用崩溃（仅显示 CSS 背景色）。
  - 修复: 给 `theme.js` 所有浏览器 API 调用加 try/catch 防御；移除 Google Fonts CDN（外部资源可能阻塞 WebKitGTK 渲染）；`__main__.py` 用 TCP connect 轮询替代盲等 sleep 确保服务器就绪后再打开窗口；`app.py` 静态资源添加 `Cache-Control: no-cache`。
  - 影响文件: `frontend/src/theme.js`, `frontend/index.html`, `walkabout/__main__.py`, `walkabout/app.py`

- **架构债务化解 — execute.py 栈帧过滤修复 + 子进程管理 + 重复代码消除**
  - `get_stack()` 改用文件路径匹配替代函数名字符串匹配，不受用户定义的 `execute()` 函数干扰（T1/B1）。
  - `link()` 中 arXiv 调用加 try/except + 10s 超时；XML 解析 None-safe（B2）。
  - 提取共享 `_run_trace_subprocess()` 消除 api/execute.py 和 api/export.py ~40 行重复代码；显式设置 WALKABOUT_HOME（B4）；Popen + communicate 替代 subprocess.run 确保超时后 kill 子进程（B5）。
  - 清理 execute.py 中死掉的 stdout/stderr buffer 捕获代码。
  - 影响文件: `walkabout/core/execute.py`, `walkabout/core/execute_util.py`, `walkabout/core/arxiv_util.py`, `walkabout/core/file_util.py`, `walkabout/api/__init__.py`, `walkabout/api/execute.py`, `walkabout/api/export.py`

- **_ensure_package_init 递归到根目录导致 PermissionError**
  - `reversed(path.parents)` 遍历到文件系统 `/`，试图创建 `/__init__.py` 时报权限错误。
  - 修复: 添加 `NOTES_DIR` 边界检查，仅处理 NOTES_DIR 下的子目录。
  - 影响文件: `walkabout/api/notes.py`

- **MathJax 公式在 TraceViewer 中不渲染**
  - MathJax CDN 异步加载，动态渲染的 TraceViewer 内容 MathJax 无感知。`MathJax.typeset()` 调用时序不可靠。
  - 修复: 在 `index.html` 中添加 `MutationObserver` 监听 `#root` 的 DOM 变化自动触发 `typesetPromise()`；附加 30 秒轮询兜底。
  - 影响文件: `frontend/index.html`

- **Monaco Editor 静态导入导致白屏**
  - 上一轮修复中将 `monaco-editor` 静态打包进主 chunk（5MB），阻塞初始渲染。
  - 修复: 改用 `Promise.all([import('monaco-editor'), import('@monaco-editor/react')])` 动态加载，Vite 自动代码分割，主 chunk 回到 1.3MB。
  - 影响文件: `frontend/src/components/Editor.jsx`

- **点击 Run 后 TraceViewer 显示 "No trace path provided"**
  - EditorPage 执行 `executeNote()` 后得到 `trace_url` 但只保存在 React state 中，TraceViewer 从 URL query params 读取 `trace` 参数，两者未连接。
  - 修复: EditorPage 导入 `useNavigate`，执行成功后调用 `navigate('?trace=...')` 更新 URL；切换/删除文件时清除 URL params。
  - 影响文件: `frontend/src/pages/EditorPage.jsx`

- **设置界面无法退出（无关闭按钮/ESC 快捷键）**
  - SettingsPage 缺乏导航回 EditorPage 的机制，只能通过浏览器后退按钮。
  - 修复: 导入 `useNavigate`，添加 ESC 键全局监听和 "← Back" 按钮。
  - 影响文件: `frontend/src/pages/SettingsPage.jsx`

- **pywebview 在无 Qt 后端时打印 `[pywebview] QT cannot be loaded` 噪声**
  - pywebview 内部通过 qtpy 检测 Qt 绑定，未安装时输出红色错误信息到 stderr，破坏终端使用体验。
  - 修复: 在 `import webview` 期间将 `sys.stderr` 重定向到 `/dev/null`，无论成功与否恢复。
  - 影响文件: `walkabout/webview.py`

- **qtpy 安装但无 Qt 后端导致 pywebview 崩溃**
  - `pywebview` 内部导入 `qtpy`，`qtpy` 找不到 PyQt5/PySide6 时抛出 `QtBindingsNotFoundError`（非 `ImportError`），原 `except ImportError` 无法捕获，导致原生窗口初始化失败。
  - 修复: 将 pywebview 块的 `except ImportError` 扩大为 `except Exception`，使其正常回退到浏览器模式。
  - 影响文件: `walkabout/webview.py`

- **list_notes() 中 os.walk 遍历无关目录**
  - `os.walk(NOTES_DIR)` 递归进入 `__pycache__`、`.venv` 等目录，随 notes 目录增长性能会越来越差。
  - 修复: 在 `os.walk` 中通过修改 `dirs[:]` 跳过常见非源码目录。
  - 影响文件: `walkabout/api/notes.py`

- **端口冲突导致 `[Errno 98] address already in use`**
  - `webview.py`: 移除 `open_window()` 中内嵌的 uvicorn 服务启动逻辑（#2a0f28e），避免与 `__main__.py` 的服务器线程争夺端口。
  - `__main__.py`: 预创建 TCP socket 并设置 `SO_REUSEADDR` 选项（#168f965），消除 TIME-WAIT 状态导致的端口绑定失败。重构服务器启动流程，统一由 `_run_server()` 管理，消除重复的 `uvicorn.run()` 调用。
  - 影响文件: `walkabout/__main__.py`, `walkabout/webview.py`

- **runner.py 路径解析错误**
  - `core_dir` 错误地指向项目根目录而非 `walkabout/core/`（#342ea13），导致 `execute_util`/`file_util` 导入失败。
  - 修复: 使用 `os.path.join(runner_dir, 'core')` 精确指向引擎目录。

- **execute.py `__future__` import 位置错误**
  - `from __future__ import annotations` 放在文件中部而非顶部（#95cfdaa），在 Python 3.9 中引发 `SyntaxError`。
  - 修复: 移至文件第一行。

- **Conda 环境 libstdc++/libgcc_s 版本过旧**
  - 将 `libstdc++.so.6` 从 6.0.29 更新至系统版本 6.0.35，解决 `GLIBCXX_3.4.30 not found` 导致 GTK 原生窗口加载失败的问题。
  - 同步更新 `libgcc_s.so.1` 以匹配系统 GCC 版本，消除 `GCC_12.0.0 not found` 错误。

### Added

- **功能演示脚本** (`walkabout/examples/demo_walkthrough.py`)
  - 涵盖: Markdown 渲染、变量追踪 (`@inspect`)、字符串/集合操作、`@stepover`、嵌套函数调用、shell 命令、链接引用、条件分支、循环、边界情况（大整数、浮点精度、嵌套 dict、列表推导式等）、MathJax 数学公式渲染。
  - 也可作为回归测试用例。执行: 141 步 / 38 个渲染。
