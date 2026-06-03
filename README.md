# Walkabout

交互式代码讲解编辑器 — 写 Python 脚本，逐行回放。**独立桌面应用，不依赖外部浏览器。**

## 快速开始

```bash
# 从源码安装
git clone <repo>
cd walkabout
pip install -e ".[gui]"

# 启动（原生窗口，无外部浏览器）
walkabout

# 或开发模式（Vite热重载 + 浏览器）
cd frontend && npm install && npm run dev
PYTHONPATH=$PWD python3 -m walkabout
```

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

## 依赖

| 必需 | 可选 |
|------|------|
| `fastapi`, `uvicorn` | `torch` (tensor 类型支持) |
| `requests` | `sympy` (符号类型支持) |
| | `pywebview` (原生窗口) |

## 开发

```bash
git clone <repo> && cd walkabout
pip install -e ".[dev]"       # 安装所有可选依赖
cd frontend && npm install    # 安装前端依赖
```

## 许可

MIT
