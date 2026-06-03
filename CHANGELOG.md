# Changelog

## [Unreleased]

### Added

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
