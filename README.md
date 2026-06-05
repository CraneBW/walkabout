# Walkabout

交互式代码讲解编辑器 — 写 Python 脚本，逐行回放。**独立桌面应用，不依赖外部浏览器。**

## 快速下载

从 [GitHub Releases](https://github.com/CraneBW/walkabout/releases) 下载单文件可执行包：

| 平台 | 文件 | 系统依赖 |
|------|------|---------|
| **Windows** | `walkabout.exe` | 无（Edge WebView2 内置） |
| **Linux** | `walkabout-linux` | `webkit2gtk-4.1`, `gtk3` |

```bash
# Linux
chmod +x walkabout-linux && ./walkabout-linux

# Windows — 双击 walkabout.exe 即可运行
```

## 系统依赖（源码安装）

pywebview 在不同平台上需要不同的系统库来嵌入 Web 渲染引擎：

### Arch Linux

```bash
sudo pacman -S webkit2gtk python-gobject gtk3
```

> **使用 Conda 环境的用户**：如果遇到 `GLIBCXX_3.4.30 not found` 错误，更新 conda 环境的 libstdc++：`conda install -c conda-forge libstdcxx-ng --update-deps`，或手动替换为系统版本 `cp /usr/lib/libstdc++.so.6 $(python -c "import sys; print(sys.executable)")/../lib/libstdc++.so.6`。

### Ubuntu / Debian

```bash
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libgirepository1.0-dev
```

### Fedora

```bash
sudo dnf install webkit2gtk4.1-devel gtk3-devel gobject-introspection-devel
```

### macOS

无需额外系统依赖（使用系统 WKWebView）。

### Windows

无需额外系统依赖（使用系统 Edge WebView2）。

## 快速开始

```bash
# 克隆仓库
git clone git@github.com:CraneBW/walkabout.git
cd walkabout

# 安装 Python 依赖（含 GUI）
uv pip install -e ".[gui]"
uv pip install pywebview PyGObject   # Linux 额外需要

# 构建前端
cd frontend && npm install && npm run build && cd ..

# 启动（原生窗口，无外部浏览器）
walkabout

# 或开发模式（Vite 热重载 + 浏览器）
cd frontend && npm run dev &
PYTHONPATH=$PWD python3 -m walkabout
```

> **Python 3.9 用户**：Walkabout 支持 Python 3.9+，但推荐 3.11+ 以获得最佳 pywebview 兼容性。

## 架构

```
┌─────────────────────────────────────────────────────────┐
│              独立桌面窗口 (pywebview)                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │              React SPA 前端                        │  │
│  │  ┌──────────┬────────────────┬──────────────────┐ │  │
│  │  │FileBrowser│ Monaco Editor  │ TraceViewer      │ │  │
│  │  │(文件列表) │ (代码编辑)      │ (逐行回放)       │ │  │
│  │  └──────────┴────────────────┴──────────────────┘ │  │
│  │  ⚙ Settings (GUI + JSON)  📦 uv 包管理           │  │
│  └───────────────────────────────────────────────────┘  │
│                         │ HTTP                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │              FastAPI 后端                          │  │
│  │  /api/notes  /api/execute  /api/env  /api/config  │  │
│  │                    │                               │  │
│  │          execute.py 引擎 (sys.settrace)            │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│  ~/.walkabout/          │ 子进程                        │
│  ├── notes/*.py         执行 walkthrough 脚本           │
│  ├── traces/*.json                                      │
│  ├── settings.json                                      │
│  └── .venv/            uv 管理的 Python 环境            │
└─────────────────────────────────────────────────────────┘
```

## 编写 Walkthrough

```python
# 在 Walkabout 编辑器中编写
from execute_util import text, image, link

def main():
    text("## 我的演示")
    name = "World"  # @inspect name
    text(f"Hello {name}!")

    # 运行 shell 命令
    system_text(["python", "--version"])

    # 嵌入图片
    image("figures/architecture.png", width=600)
```

### 标注语法

| 语法 | 用途 |
|------|------|
| `# @inspect x` | 暴露变量值到回放面板 |
| `# @stepover` | 跳过该行函数内部细节 |
| `text("md")` | 渲染 Markdown 富文本 |
| `image(url, width)` | 嵌入图片（本地/远程） |
| `link(url)` | 引用链接（arXiv自动解析） |
| `system_text(["cmd"])` | 运行 shell 命令并显示输出 |

## 设置 (⚙)

点击工具栏 `⚙` 进入设置页，支持 **GUI 模式**和 **JSON 模式**自由切换。

### GUI 模式

按分类浏览、搜索、修改设置，修改项有蓝色圆点标记：

| 分类 | 设置项 |
|------|--------|
| **Python** | `python.path` 解释器路径, `python.timeout` 超时(秒), `python.args` 额外参数 |
| **Editor** | `editor.fontSize` 字号, `editor.theme` 主题(vs/vs-dark/hc-black/hc-light), `editor.wordWrap` 自动换行, `editor.minimap` 缩略图, `editor.tabSize` 缩进空格 |
| **Appearance** | `appearance.theme` 应用主题(dark/light/system), `appearance.locale` 语言(en/zh-CN) |
| **Execution** | `execution.autoSave` 运行前自动保存, `execution.clearOutput` 运行前清输出, `execution.animate` 动画过渡 |
| **Window** | `window.width` 窗口宽度, `window.height` 窗口高度, `window.port` 服务端口 |

> **端口配置**：默认端口 8000，如需更改请在 `~/.walkabout/settings.json` 中设置 `"window": { "port": 8001 }`。服务器使用 `SO_REUSEADDR` 选项，可以快速重启而不受 TIME-WAIT 状态影响。

### JSON 模式

直接编辑 `~/.walkabout/settings.json`，只存储与默认值不同的项：

```json
{
  "python": { "path": "/usr/bin/python3.12" },
  "editor": { "fontSize": 16, "theme": "vs-dark" },
  "execution": { "autoSave": false }
}
```

`↺ Reset` 一键恢复所有默认值。

## 环境管理

工具栏 `📦` → 输入包名 → 自动 `uv pip install`。首次安装时自动创建 `~/.walkabout/.venv`，执行 walkthrough 时自动使用该 venv 的 Python。

## 插件系统

```python
# ~/.walkabout/plugins/my_plugin/__init__.py
from walkabout.plugins.base import WalkaboutPlugin

class MyPlugin(WalkaboutPlugin):
    name = "my-plugin"
    version = "0.1.0"

    def on_startup(self, app):
        """注册 FastAPI 路由、添加中间件"""
        pass

    def on_pre_execute(self, module_name, code):
        """执行前修改代码"""
        return "import numpy as np\n" + code

    def on_post_execute(self, module_name, trace):
        """执行后修改 trace（添加渲染内容）"""
        return trace

    def get_frontend_components(self):
        """向前端注入 UI 组件"""
        return []
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notes` | 列出所有笔记 |
| GET | `/api/notes/{path}` | 读取笔记内容 |
| PUT | `/api/notes/{path}` | 保存笔记 |
| POST | `/api/notes` | 创建笔记 |
| DELETE | `/api/notes/{path}` | 删除笔记 |
| POST | `/api/execute` | 执行 walkthrough 生成 trace |
| GET | `/api/env` | 查看 Python 环境信息 |
| POST | `/api/env/install` | 安装 Python 包 |
| GET | `/api/config` | 读取所有设置 |
| GET | `/api/config/schema` | 获取设置 schema |
| POST | `/api/config/set` | 修改单个设置 |
| POST | `/api/config/reset` | 恢复默认设置 |
| GET | `/api/export` | 导出已有 trace 为独立 HTML |
| POST | `/api/export` | 执行 note 并导出为独立 HTML 下载 |
| GET | `/api/export/preview/{path}` | 预览已导出的 HTML |
| POST | `/api/export/save` | 执行 note 并保存 HTML 到导出目录（支持 `strip_source`、`content_only` 选项） |

## 导出 (Export)

Walkthrough 可导出为 **独立 HTML** 文件，无需 Python 后端即可在浏览器中逐帧回放：

- **完整模式**（默认）：显示源代码（高亮）、渲染内容、环境变量面板
- **内容模式**（`content_only=True`）：仅显示渲染内容和变量变化，隐藏源码
- **text() 隐藏**：`text(...)` 调用行自动隐藏，仅显示渲染后的 Markdown 输出

```bash
# 通过 API 导出（POST /api/export/save）
# 设置中可指定 export.directory 保存路径
```

## 依赖

| 必需 | 可选 |
|------|------|
| `fastapi`, `uvicorn` | `torch` (tensor 类型支持) |
| `requests` | `sympy` (符号类型支持) |
| | `pywebview` (原生窗口) |

## 测试

```bash
# Python 后端测试（167 tests + 68 Windows 兼容 + 24 in-process 集成）
pytest tests/ -v

# 前端测试（42 tests, Vitest + jsdom）
cd frontend && npx vitest run

# Lint
ruff check .                    # Python
cd frontend && npx eslint src/  # JavaScript/JSX
```

CI 流水线（`.github/workflows/ci.yml`）在每次 push/PR 时自动执行 `ruff` + `pytest` + `eslint` + `vitest`。

## 开发

```bash
git clone <repo> && cd walkabout
pip install -e ".[dev]"       # 安装所有可选依赖
cd frontend && npm install    # 安装前端依赖
```

## Claude Code 集成

本项目自带 `.claude/` 配置，克隆后在 Claude Code 中打开即可使用以下能力：

### Skills

| Skill | 触发方式 | 说明 |
|-------|---------|------|
| `create-walkthrough` | `/create-walkthrough <主题>` | 在 `~/.walkabout/notes/` 创建 walkthrough `.py` 脚本 |
| `walkabout-dev` | `/walkabout-dev` | 一键检测环境、构建前端、启动开发模式 |

### Hooks

| Hook | 事件 | 说明 |
|------|------|------|
| 语法检查 | `PostToolUse` (Write/Edit) | 保存 `.py` 脚本后自动 `py_compile` 检查语法 |
| 环境提醒 | `SessionStart` | 进入项目时提示 Walkabout 启动方式 |

### MCP

推荐配合以下 MCP 服务器使用：

| MCP Server | 用途 |
|------------|------|
| **MCPVault** (`@anthropic/mcpvault`) | 在 Obsidian vault 中管理 `.walkabout` 笔记，双向链接 walkthrough 脚本 |
| **Filesystem** (`@anthropic/mcp-filesystem`) | 让 Claude 直接读写 `~/.walkabout/notes/` 和 `~/.walkabout/traces/` |

在 `~/.claude/settings.json` 或项目 `.claude/settings.json` 中配置：

```json
{
  "enabledMcpjsonServers": ["mcpvault", "filesystem"]
}
```

### Plugin

Walkabout 有自己的插件系统（`~/.walkabout/plugins/`），Claude 可以帮你创建插件：

```
/plugin:create <插件名>  # 创建插件骨架
```

## 许可

MIT
