# Changelog

## [Unreleased]

### Added

- **Trace 持久化 — 重启后保留上次执行的 trace**
  - 后端 `read_note()` 返回 `trace_url` 字段：打开文件时检查 `~/.walkabout/traces/` 下是否有对应的 trace JSON，若存在则自动恢复。
  - 前端 EditorPage 根据返回的 `trace_url` 恢复状态，无需重新 Run 即可查看上次执行结果。
  - 影响文件: `walkabout/api/notes.py`, `frontend/src/pages/EditorPage.jsx`

- **Monaco Editor 本地打包替代 CDN 加载**
  - 将 `monaco-editor` npm 包直接打包进前端构建产物，消除每次打开文件时从 CDN 下载 ~30MB 的延迟。
  - 前端构建体积从 1.3MB 增至 ~5MB（含 code splitting 的 worker 文件），但编辑器的加载变为即时。
  - 影响文件: `frontend/src/components/Editor.jsx`, `frontend/package.json`

### Fixed

- **点击 Run 后 TraceViewer 显示 "No trace path provided"**
  - EditorPage 执行 `executeNote()` 后得到 `trace_url` 但只保存在 React state 中，TraceViewer 从 URL query params 读取 `trace` 参数，两者未连接。
  - 修复: EditorPage 导入 `useNavigate`，执行成功后调用 `navigate('?trace=...')` 更新 URL；切换/删除文件时清除 URL params。
  - 影响文件: `frontend/src/pages/EditorPage.jsx`

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
  - 涵盖: Markdown 渲染、变量追踪 (`@inspect`)、字符串/集合操作、`@stepover`、嵌套函数调用、shell 命令、链接引用、条件分支、循环、边界情况（大整数、浮点精度、嵌套 dict、列表推导式等）。
  - 也可作为回归测试用例。执行: 135 步 / 32 个渲染。
