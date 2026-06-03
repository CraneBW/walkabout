# Walkabout 基线任务文档

## 已知问题 (Bugs)

### B1. get_stack() 在多层 wrapper 下可能丢帧
- **文件**: `walkabout/core/execute.py`
- **现象**: 通过 runner.py → execute() 调用时，`get_stack()` 的栈帧过滤逻辑依赖 `execute` 函数名查找，如果调用链中出现同名的非引擎函数（如用户在 walkthrough 中定义了 `execute()` 函数），会导致栈帧被错误跳过。
- **临时方案**: 当前按 `execute` 名查找分界点，对大多数场景有效。
- **正确修复**: 改用文件路径过滤（如跳过所有含 `walkabout/core` 的帧），而非函数名。

### B2. execute_util.py 的 arxiv_util 惰性导入不完整
- **文件**: `walkabout/core/execute_util.py`
- **现象**: 如果用户代码在 `text()` 或 `image()` 之前调用 `link()` 且传入了 arXiv URL，惰性导入会成功，但 `is_arxiv_link()` 在网络不可达时会抛异常。
- **修复**: 给 `arxiv_util.is_arxiv_link()` 加 try/except + 超时。

### B3. 前端 TraceViewer asset 路径硬编码
- **文件**: `frontend/src/TraceViewer.jsx`
- **现象**: 构建产物中资源路径仍然依赖 `/spring2025-lectures/` 的部分逻辑（通过 vite base 配置覆盖）。如果用户自定义 base path，需要重新构建。
- **修复**: 将 base path 改为可配置的运行时变量。

### B4. Monaco Editor CDN 依赖
- **文件**: `frontend/src/components/Editor.jsx`
- **现象**: `@monaco-editor/react` 默认从 CDN 加载 Monaco 本体（~30MB），离线环境无法使用编辑器。
- **修复**: 配置 `@monaco-editor/react` 使用本地打包版本，或切换到 CodeMirror（更轻量，约 500KB）。

### B5. 子进程执行时 WALKABOUT_HOME 路径未传递给 runner
- **文件**: `walkabout/api/execute.py`
- **现象**: 如果用户通过 `WALKABOUT_HOME` 环境变量自定义工作空间，`runner.py` 不会继承该变量（`os.environ.copy()` 已做，但未显式设置）。
- **修复**: 在子进程 env 中显式设置 `WALKABOUT_HOME`。

### B6. 执行超时后子进程可能未清理
- **文件**: `walkabout/api/execute.py`
- **现象**: `subprocess.run(timeout=60)` 超时后会抛异常，但子进程可能未退出，残留僵尸进程。
- **修复**: 在 `TimeoutExpired` 处理中调用 `proc.kill()` + `proc.wait()`。

---

## 未来工作 (Future Work)

### F1. 多窗口 / 多文件编辑
- 当前只支持单选文件编辑。需要支持 tab-based 多文件编辑，允许用户同时打开多个 walkthrough 脚本。
- 预计工时: 2-3 天（前端重构 FileBrowser + Editor 状态为多实例）。

### F2. 实时协作
- 通过 WebSocket 实现多人同时编辑同一个 walkthrough。
- 依赖: F1 完成后进行，需要引入 CRDT (Yjs) 或 Operational Transform。
- 预计工时: 1-2 周。

### F3. 版本历史 / 撤销
- 集成 git 或本地版本快照，允许回退 walkthrough 脚本到历史版本。
- Python 后端管理 git 操作，前端展示 diff。
- 预计工时: 1 周。

### F4. 导出为静态 HTML
- 将 trace JSON + viewer 前端打包成一个自包含的 `.html` 文件，可直接分享。
- 类似 Jupyter nbconvert 的 "Download as HTML"。
- 预计工时: 2-3 天。

### F5. 可视化执行进度
- 在编辑器中内联显示每一步的变量值（类似 VS Code Debugger 的 inline values）。
- 需要 Monaco Editor 的 Decorations API。
- 预计工时: 3-5 天。

### F6. 自定义渲染器插件 API
- 当前 `Rendering` 类型固定为 text/image/link。需要插件 API 让用户注册自定义渲染器。
- 例如: `@register_renderer("vega")` 支持 Vega-Lite 图表、`@register_renderer("mermaid")` 支持流程图。
- 预计工时: 1 周。

### F7. IPython 内核集成
- 替换当前的子进程执行模式，改用 IPython 内核（通过 jupyter_client）。
- 优势: 真正的持久状态、富输出（DataFrame 表格、交互图表）、与现有 Jupyter 生态兼容。
- 预计工时: 1-2 周。

### F8. 性能优化：大型 trace 的分页加载
- 当前 viewer 一次性加载整个 trace JSON。对于超过 10K 步的 trace 会卡顿。
- 需要实现虚拟滚动 + 分步加载（只加载当前可见区域 ± 50 步的 trace 段）。
- 预计工时: 1 周。

### F9. Python 包自动补全 / 智能提示
- Monaco Editor 默认只有 Python 语法高亮，没有自动补全。
- 需要集成 Pyright 或 Jedi language server 提供智能提示。
- 预计工时: 1-2 周。

### F10. 移动端 / 平板支持
- 前端目前未适配触摸操作。需要响应式布局 + 触摸友好的导航按钮。
- 预计工时: 1 周。

### F11. 测试套件
- 当前零测试。需要:
  - 后端: pytest 覆盖所有 API 端点 (`test_api/`)
  - 前端: Vitest + React Testing Library (`frontend/src/__tests__/`)
  - E2E: Playwright 测试编辑→执行→回放完整链路
- 预计工时: 1-2 周（持续进行）。

### F12. CI/CD
- GitHub Actions: lint (ruff + eslint)、test (pytest + vitest)、build + publish to PyPI。
- 预计工时: 2-3 天。

---

## 架构债务 (Tech Debt)

### T1. execute.py 与 runner.py 的调用链耦合
- `runner.py` 必须通过 `execute.py` 的 `get_stack()` 理解调用栈结构。两者紧密耦合。
- 建议: 将执行引擎抽象为 `Engine` 类，`runner.py` 通过明确定义的接口调用。

### T2. 前后端 TraceViewer 代码重复
- `TraceViewer.jsx` 从 CS336 课件复制后做了最小修改，与原始上游无共享机制。
- 建议: 将 TraceViewer 抽取为独立的 npm 包，walkabout 和 CS336 课件都依赖该包。

### T3. 前端 API 调用无请求去重 / 重试 / 缓存
- `api.js` 中的 Axios 调用没有错误重试、请求去重或响应缓存。
- 建议: 引入 `@tanstack/react-query` 或简单的请求管理器。

---

## 文档待补充

- [ ] 用户手册 (README.md 中补充完整教程)
- [ ] 插件开发指南 (如何写一个 Walkabout 插件)
- [ ] 渲染器文档 (text/image/link 的完整 API 参考)
- [ ] 部署指南 (服务器模式、Docker、反向代理)
- [ ] 贡献指南 (CONTRIBUTING.md)
