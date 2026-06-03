# Walkabout 基线任务文档

> 版本: 0.1.0 | 更新: 2026-06-03

## 已完成 (Completed)

- [x] **Git 化** — 项目托管为独立 git 仓库，含 `.gitignore`
- [x] **pip 安装** — `pyproject.toml` 配置完成，`pip install walkabout[gui]` 可安装
- [x] **独立桌面应用** — pywebview 原生窗口，不依赖外部浏览器；WSL/无 GUI 时自动回退浏览器
- [x] **VS Code 风格设置系统** — schema 驱动的设置引擎，JSON 默认值 + 用户 diff 存储；GUI 模式（分类搜索、toggle/select/text/number 控件）和 JSON 编辑器模式
- [x] **嵌入式回放** — Edit/View 同页面标签切换，不弹新窗口
- [x] **uv 环境管理** — 工具栏一键安装包，自动创建 `~/.walkabout/.venv`
- [x] **可配置 Python 解释器** — settings.json 中 `python.path` 或自动检测 workspace venv
- [x] **插件系统** — `WalkaboutPlugin` 基类 + `PluginManager` 自动发现，on_startup/on_pre_execute/on_post_execute 钩子
- [x] **Trace 持久化** — 重启后自动恢复上次执行的 trace（`read_note` 检查磁盘中已有 trace JSON）

---

## 已知问题 (Bugs)

### B1. get_stack() 在多层 wrapper 下可能丢帧
- **文件**: `walkabout/core/execute.py`
- **现象**: 通过 runner.py → execute() 调用时，`get_stack()` 的栈帧过滤逻辑依赖 `execute` 函数名查找，如果用户 walkthrough 中定义了同名 `execute()` 函数，栈帧会被错误跳过。
- **临时方案**: 按 `execute` 名查找分界点，大多数场景有效。
- **修复方向**: 改用文件路径过滤（跳过含 `walkabout/core` 的帧），而非函数名。

### B2. execute_util.py 的 arxiv_util 惰性导入不完整
- **文件**: `walkabout/core/execute_util.py`
- **现象**: `is_arxiv_link()` 在网络不可达时抛异常，且首次惰性导入有性能开销。
- **修复方向**: 给网络调用加 try/except + 超时（3秒）。

### B3. Monaco Editor CDN 依赖（已修复）
- **文件**: `frontend/src/components/Editor.jsx`
- **现象**（已修复）: `@monaco-editor/react` 默认从 CDN 加载 Monaco 本体（~30MB），离线环境无法编辑。
- **修复**: 安装 `monaco-editor` npm 包，通过 `loader.config({ monaco })` 使用本地 bundle。前端构建体积从 1.3MB 增至 ~5MB，但编辑器加载变为即时，消除网络依赖。

### B4. 子进程执行时 WALKABOUT_HOME 未显式传递给 runner
- **文件**: `walkabout/api/execute.py`
- **现象**: `os.environ.copy()` 继承当前环境但未显式设置 `WALKABOUT_HOME`，用户自定义路径可能在子进程中丢失。
- **修复方向**: 在子进程 env 中显式 `env["WALKABOUT_HOME"] = str(WALKABOUT_HOME)`。

### B5. 执行超时后子进程可能残留
- **文件**: `walkabout/api/execute.py`
- **现象**: `subprocess.run(timeout=60)` 超时抛异常后子进程未 kill，残留僵尸进程。
- **修复方向**: `TimeoutExpired` 处理中 `proc.kill()` + `proc.wait()`。

### B6. TraceViewer 构造函数中使用了 `BrowserRouter` 但已在上层路由中
- **文件**: `frontend/src/TraceViewer.jsx`（复制自 CS336 课件）
- **现象**: TraceViewer 内部使用 `useNavigate()` 依赖上层 `BrowserRouter`。如果作为独立组件导出到其他项目，缺少 Router 包裹会崩溃。
- **修复方向**: 将 URL 导航抽象为 props callback，移除对 react-router 的直接依赖。

### B7. 设置变更后编辑器/查看器不会热更新
- **文件**: 前端 `EditorPage.jsx`, `Editor.jsx`
- **现象**: 修改 `editor.fontSize` 或 `editor.theme` 后需刷新页面才生效。
- **修复方向**: SettingsPage 通过 `window.postMessage` 通知 EditorPage 重新读取配置，或使用 React Context 全局共享设置状态。

### B8. pywebview 在 WSL2 中不可用
- **文件**: `walkabout/webview.py`, `walkabout/__main__.py`
- **现象**: WSL2 无原生 GUI（无 X Server 时），pywebview 导入成功但 `webview.start()` 崩溃。
- **当前方案**: try/except 回退到系统浏览器。`open_window()` 不再内嵌 uvicorn 服务，避免与 `__main__.py` 的服务器线程冲突。
- **修复方向**: 检测 `$DISPLAY` 环境变量，在无 GUI 时打印明确提示并自动降级到浏览器模式，同时提供 `--no-gui` CLI flag。

### B9. 列表推导式中 @inspect 变量定位失败
- **文件**: `walkabout/core/execute.py`
- **现象**: 对列表推导式的结果变量使用 `@inspect`（如 `squares = [x*x for x in range(5)]  # @inspect squares`），local_trace_func 被列表推导的内部作用域触发多次，每次 `squares` 在 locals 中不可见，产生多个 `WARNING: variable squares not found in locals` 噪音。
- **根因**: 列表推导式创建了隐式函数作用域，`local_trace_func` 在该作用域内无法访问外层函数的 `squares` 变量，直到推导完成后才可见。
- **修复方向**: 检测列表/集合/字典推导式的代码行，在推导式作用域内跳过变量捕获，直到推导完成后再捕获一次。

### B10. TraceViewer "No trace path provided"（已修复）
- **文件**: `frontend/src/pages/EditorPage.jsx`, `frontend/src/TraceViewer.jsx`
- **现象**: 点击 Run 后回放面板显示 "No trace path provided"，无法查看执行结果。
- **根因**: EditorPage 将 `trace_url` 保存在 React state 中，但 TraceViewer 从 URL query params (`?trace=...`) 读取路径。两者之间无连接，URL 从未被更新。
- **修复**: EditorPage 导入 `useNavigate`，执行成功后调用 `navigate('?trace=' + encodeURIComponent(trace_url))`；切换/删除文件时清除 URL params。

### B11. qtpy 无后端导致原生窗口崩溃（已修复）
- **文件**: `walkabout/webview.py`
- **现象**: pywebview 的 `import webview` 内部触发 `qtpy.QtBindingsNotFoundError`，该异常非 `ImportError`，未被 `except ImportError` 捕获，导致 GUI 初始化失败。
- **根因**: `qtpy` 已安装但 PyQt5/PySide6 未安装，pywebview 通过 qtpy 检测 Qt 时抛出绑定错误。
- **修复**: 将 `except ImportError` 扩大为 `except Exception`，捕获所有初始化异常后自动回退到浏览器模式。

---

## 未来工作 (Future Work)

### F1. 多标签文件编辑
- 当前只支持单选文件。需 tab-based 多文件编辑。
- 前端重构 FileBrowser + Editor 状态为多实例，类似 VS Code 标签页。
- 预计: 3 天。

### F2. 实时协作
- WebSocket 实现多人同时编辑同一 walkthrough。
- 依赖 F1，需引入 CRDT (Yjs)。
- 预计: 2 周。

### F3. 版本历史 (Git 集成)
- 后端管理 git 快照，前端展示 diff，允许回退到历史版本。
- 预计: 1 周。

### F4. 导出为静态 HTML
- 将 trace JSON + viewer 前端打包为自包含 `.html`，直接分享（类似 Jupyter nbconvert）。
- 预计: 3 天。

### F5. 编辑器内联变量显示
- 利用 Monaco Decorations API，在编辑器行尾显示当前步骤的变量值（类似 VS Code Debugger inline values）。
- 预计: 5 天。

### F6. 自定义渲染器插件 API
- 当前 Rendering 固定为 text/image/link。需开放注册: `@register_renderer("vega")`, `@register_renderer("mermaid")`。
- 预计: 1 周。

### F7. IPython 内核集成
- 替换子进程模式，用 jupyter_client 连接 IPython 内核。
- 优势: 真正的持久状态、DataFrame 富输出、与 Jupyter 生态兼容。
- 预计: 2 周。

### F8. 大型 trace 分页加载
- 超过 10K 步的 trace 需虚拟滚动 + 按需加载（当前可见区域 ± 50 步）。
- 预计: 1 周。

### F9. Python 智能提示
- 集成 Pyright/Jedi language server 提供自动补全、类型提示、跳转到定义。
- 预计: 2 周。

### F10. 触摸设备支持
- 响应式布局 + 触摸友好的导航按钮。
- 预计: 1 周。

### F11. 测试套件
- 后端: pytest (`tests/api/`)
- 前端: Vitest + React Testing Library (`frontend/src/__tests__/`)
- E2E: Playwright (编辑→执行→回放完整链路)
- 预计: 2 周。

### F12. CI/CD
- GitHub Actions: lint (ruff + eslint) → test (pytest + vitest) → build → publish PyPI
- 预计: 3 天。

### F13. CLI 模式
- `walkabout run my_script.py` — 命令行直接执行 walkthrough 并输出 trace JSON（无需 GUI）。
- `walkabout export my_script.py -o output.html` — 命令行导出静态 HTML。
- 预计: 2 天。

### F14. Walkthrough 模板市场
- 社区共享 walkthrough 模板，一键克隆到本地工作空间。
- 预计: 1 周。

---

## 架构债务 (Tech Debt)

### T1. execute.py 与 runner.py 调用链耦合
- 两者通过 `get_stack()` 的栈帧结构隐式耦合，任一方的调用层级变化都会导致栈帧过滤失效。
- 建议: 将执行引擎抽象为 `Engine` 类，runner 通过明确定义的接口（如 `Engine.run(module_name) -> Trace`）调用。

### T2. TraceViewer 代码与上游分裂
- 从 CS336 课件复制后独立演进，与原始上游无共享机制。
- 建议: 将 TraceViewer 抽取为独立 npm 包，walkabout 通过依赖引入。

### T3. 前端 API 层无请求管理
- `api.js` 无错误重试、请求去重、响应缓存。
- 建议: 引入 `@tanstack/react-query` 或封装 `useSWR`。

### T4. 设置 schema 与前端控件绑定
- 当前 SettingsPage 中控件类型 (toggle/select/text) 硬编码对应 schema 的 `type` 字段。
- 新类型（color、keybinding、array）需同时改 schema 和 React 渲染逻辑。
- 建议: 将控件渲染抽象为 `renderControl(type, schema, value, onChange)` 工厂函数。

### T5. pywebview 与 uvicorn 线程竞争（部分修复）
- **已修复**: `open_window()` 不再启动第二个 uvicorn 服务（#6ae2f2c），`__main__.py` 中使用预创建 SO_REUSEADDR socket 消除 TIME-WAIT 导致的端口冲突（#8c4f3b1）。
- **遗留**: 窗口关闭时 daemon 线程被强制终止，无优雅关闭。
- **建议**: 使用 `signal` 或 `atexit` 注册清理逻辑，或改用 `multiprocessing` 进程隔离。

### T6. 前端构建产物包含在 Python 包中增大体积
- `frontend/dist/` ~1.3MB JS + ~10KB CSS 被打包进 wheel。
- 当前可接受，但如果 Monaco 本体也打包进 dist 会膨胀到 ~30MB。
- 建议: 发布时可选是否含前端（`walkabout-core` vs `walkabout`），或首次启动时自动下载前端。

---

## 文档待补充

- [ ] 用户手册 — 完整教程（README.md 基础版已就绪，需补充）  
- [ ] 插件开发指南 — 如何写一个 Walkabout 插件（含示例项目）  
- [ ] 渲染器文档 — `text()/image()/link()/system_text()` 完整 API 参考  
- [ ] 部署指南 — 服务器模式、Docker、反向代理  
- [ ] 贡献指南 — `CONTRIBUTING.md`
