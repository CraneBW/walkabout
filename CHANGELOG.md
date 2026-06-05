# Changelog

## [Unreleased]

### Added

- **CI lint + test 流水线** (`7032ee7`)
  - `.github/workflows/ci.yml`: push/PR 触发 4 job — `python-lint` (ruff), `python-test` (pytest, 3.11+3.13), `frontend-lint` (eslint), `frontend-test` (vitest)
  - `pyproject.toml` 添加 ruff 配置 (E/F/W/I/B/SIM 规则)，所有错误已修复
  - `frontend/eslint.config.mjs` 添加 JSX 支持
  - `frontend/vite.config.js` 添加 vitest 配置 (jsdom 环境)
  - 影响文件: `.github/workflows/ci.yml`, `pyproject.toml`, `frontend/`

- **前端单元测试 (Vitest + jsdom)** (`1529ada`)
  - `theme.test.js`: 23 tests — 主题管理 + 持久化 + 路由导航回归
  - `utils.test.js`: 9 tests — getLast, navigateToUrl
  - `api.test.js`: 10 tests — axios mock 覆盖所有 API 函数
  - 共 42 个前端测试

- **Windows 兼容性全量测试 (pytest, 68 tests)** (`0c772bb`)
  - Runner venv/os.execv 跳过逻辑、config.py get_python_path 各平台回退
  - api/env.py venv 检测和 uv 路径、CREATE_NO_WINDOW 子进程标志
  - 显示检测 (Windows/macOS/Linux/Wayland)、WSL 检测
  - 路径遍历防护 (`_resolve()`)、跨驱动器边界、控制台编码 GBK 安全
  - PyInstaller sys.frozen/_MEIPASS、webbrowser 回退
  - 影响文件: `tests/test_windows_compat.py`

- **In-process 执行集成测试 (pytest, 24 tests)** (`864e10f`)
  - `_run_trace_inprocess` 完整流程：trace 创建、cwd/sys.path/WALKABOUT_HOME 恢复
  - 边界情况：缺失 cwd 创建、模块未找到、trace 父目录创建、下划线命名
  - 路径解析：core_dir 绝对路径、relative_to 大小写、MEIPASS 结构
  - Trace 内容：文件包含、步骤生成、@inspect 变量捕获
  - 影响文件: `tests/test_inprocess.py`

### Fixed

- **View 视图不渲染 — 裸导入模块双例问题** (`6d81c72`)
  - 用户代码 `from execute_util import text` 和引擎代码 `from walkabout.core.execute_util import pop_renderings` 解析为两个不同模块对象，`_current_renderings` 列表不同，导致 text() 写入一个列表，pop_renderings() 读取另一个空列表。
  - 修复: 在 `_run_trace_inprocess` 中注册 `sys.modules['execute_util']` = `sys.modules['walkabout.core.execute_util']`，确保裸导入和包导入共享同一模块对象。

- **Windows PyInstaller `import test` 失败 — stdlib test 包冲突** (`864e10f`)
  - Python stdlib 的 `test` 包被 PyInstaller 部分打包，FrozenImporter 在 sys.path 之前拦截 `import test`，导致用户的 test.py 笔记永远找不到。
  - 修复: `_run_trace_inprocess` 中用 `importlib.util.spec_from_file_location()` 从绝对文件路径直接加载笔记模块，注册到 sys.modules，绕过 PyInstaller import hook。

- **PyInstaller in-process core_dir 路径错误** (`f1f23da`)
  - `Path(__file__)` 在 `os.chdir()` 之后解析：PyInstaller 中 `__file__` 为相对路径，chdir 到 NOTES_DIR 后解析的 core_dir 指向 `<NOTES_DIR>/walkabout/core`（不存在）。
  - 修复: core_dir 在 `os.chdir()` 之前用 `.resolve()` 解析为绝对路径。

- **cwd 规范路径 + PyInstaller 诊断日志** (`afccd8b`)
  - cwd 用 `.resolve()` 解析为规范路径（防止 Windows 大小写/短名差异）
  - PyInstaller 模式下额外添加 `sys._MEIPASS` 到 sys.path
  - 异常时打印完整诊断信息（cwd, sys.path, 文件列表等）

- **工具栏主题切换回退 Bug (B7)** (`f11fb56`)
  - 工具栏 `toggleTheme()` 只更新 localStorage/DOM，不保存到 API。进入设置再返回时 EditorPage 重新挂载，从 API 拉取旧值覆盖用户选择。
  - 修复: `handleToggleTheme()` 增加 `axios.post('/api/config/set')`。

- **设置变更后编辑器不热更新 (B7)** (`51c9365`)
  - 修改 `editor.fontSize` 后需刷新页面才在 Monaco Editor 中生效。
  - 修复: Editor.jsx 接受 `settings` prop；EditorPage 通过 `window.postMessage` 监听 SettingsPage 的设置变更广播。
