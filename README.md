<p align="center">
  <h1 align="center">Walkabout</h1>
  <p align="center"><em>把代码变成课件。一行一行讲给别人听。</em></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python">
  <img src="https://img.shields.io/badge/tests-250+-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey" alt="Platform">
</p>

---

## 为什么写这个项目

斯坦福 [CS336](https://cs336.stanford.edu/) 课上，老师的课件是**可交互的**——代码嵌入在幻灯片里，可以逐行执行、查看变量、渲染 Markdown 输出。不是静态的 PPT，不是 Jupyter Notebook，而是一种全新的"可回放代码讲解"形式。

我想把这个体验变成一个人人都能用的工具。

于是有了 **Walkabout**：一个独立桌面应用，写 Python 脚本，加上简单标注，就能生成可交互的课件。导出成 HTML，分享给任何人——对方不需要装 Python，浏览器打开就能逐行回放。

---

## 下载

从 [Releases](https://github.com/CraneBW/walkabout/releases) 下载单文件可执行包，无需安装 Python：

| 平台 | 文件 | 系统要求 |
|------|------|---------|
| **Windows** | `walkabout.exe` | Windows 10+（Edge WebView2 内置） |
| **Linux** | `walkabout-linux` | 需安装 `webkit2gtk-4.1` + `gtk3` |

```bash
# Linux
chmod +x walkabout-linux && ./walkabout-linux

# Windows — 双击 walkabout.exe
```

Linux 系统库安装：

| 发行版 | 命令 |
|--------|------|
| Arch | `sudo pacman -S webkit2gtk gtk3` |
| Ubuntu/Debian | `sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev` |
| Fedora | `sudo dnf install webkit2gtk4.1-devel gtk3-devel` |

macOS 和 Windows 无需额外系统依赖。

---

## 快速体验

5 分钟上手：

```bash
git clone https://github.com/CraneBW/walkabout.git
cd walkabout

# 后端
uv pip install -e ".[gui]"

# 前端
cd frontend && npm install && npm run build && cd ..

# 启动
walkabout
```

打开后点击侧边栏的演示脚本，按 ▶ Run 查看逐行回放效果。

---

## 如何编写 Walkthrough

在 Walkabout 中新建一个 `.py` 文件：

```python
from execute_util import text, image, link

def main():
    text("## 梯度下降直观理解")

    # @inspect 标注的变量会在右侧面板实时显示
    x = 10.0          # @inspect x
    lr = 0.1          # @inspect lr

    for step in range(5):
        grad = 2 * (x - 3)    # @inspect grad
        x = x - lr * grad     # @inspect x
        text(f"Step {step}: x = {x:.2f}, gradient = {grad:.2f}")

    # 嵌入图片
    image("assets/gradient_descent.png", width=600)

    # arXiv 链接自动解析
    link("https://arxiv.org/abs/1706.03762")
```

### 标注语法速查

| 语法 | 效果 |
|------|------|
| `# @inspect var` | 变量值实时显示在回放面板 |
| `# @stepover` | 跳过函数内部调用，不进入细节 |
| `text("markdown")` | 渲染为富文本（支持 LaTeX: `$E=mc^2$`） |
| `image(url, width)` | 嵌入图片（支持本地路径和远程 URL） |
| `link(url)` | 添加引用链接（arXiv 自动解析标题/作者） |
| `system_text(["cmd"])` | 执行 shell 命令并显示输出 |

---

## CLI 模式

不用打开 GUI，命令行直接执行和导出：

```bash
# 执行并保存 trace JSON
walkabout run my_lecture.py -o trace.json --inspect-all

# 导出为独立 HTML（对方无需安装任何东西）
walkabout export my_lecture.py -o lecture.html --strip-source

# 从已有 trace 导出（跳过重新执行）
walkabout export --from-trace trace.json -o lecture.html
```

导出的 HTML 是**完全自包含的**——发给学生，浏览器打开就能逐行回放你的代码。

---

## 特性

- **独立桌面应用** — 不依赖外部浏览器，原生窗口
- **逐行执行引擎** — `sys.settrace` 精确捕获每一步的状态
- **富文本渲染** — Markdown、LaTeX 数学公式、图片、链接
- **导出为独立 HTML** — 生成的课件可在任何浏览器中回放
- **双主题** — 暗色 / 亮色一键切换
- **插件系统** — `~/.walkabout/plugins/` 下编写 Python 插件扩展功能
- **跨平台** — Windows、Linux、macOS

---

## 架构

```
┌──────────────────────────────────────────────────────────┐
│                  独立桌面窗口 (pywebview)                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │                React SPA 前端                       │  │
│  │  ┌──────────┬──────────────────┬─────────────────┐ │  │
│  │  │FileBrowser│  Monaco Editor   │  TraceViewer    │ │  │
│  │  │(文件列表) │  (代码编辑)       │  (逐行回放)     │ │  │
│  │  └──────────┴──────────────────┴─────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│                          │ HTTP                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                 FastAPI 后端                         │  │
│  │  /api/notes  /api/execute  /api/export  /api/config │  │
│  │                     │                               │  │
│  │           execute.py (sys.settrace 引擎)             │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│  ~/.walkabout/                                            │
│  ├── notes/*.py         你写的 walkthrough 脚本           │
│  ├── traces/*.json       执行结果（可复用）               │
│  ├── plugins/            插件目录                         │
│  └── settings.json       用户配置                         │
└──────────────────────────────────────────────────────────┘
```

---

## 开发

```bash
git clone https://github.com/CraneBW/walkabout.git
cd walkabout

# 安装依赖
uv pip install -e ".[gui]"
cd frontend && npm install && cd ..

# 开发模式（前端热重载）
cd frontend && npm run dev &
PYTHONPATH=. python -m walkabout serve

# 运行测试
pytest tests/ -v                    # Python 后端（208 测试）
cd frontend && npx vitest run       # 前端（42 测试）

# Lint
ruff check .                        # Python
cd frontend && npx eslint src/      # JavaScript/JSX
```

CI 在每次 push 和 PR 时自动执行 `ruff` + `pytest` + `eslint` + `vitest`。

---

## 设置

| 设置项 | 说明 |
|--------|------|
| `python.path` | Python 解释器路径 |
| `editor.fontSize` | 编辑器字号 |
| `editor.theme` | 编辑器主题 (`vs` / `vs-dark`) |
| `appearance.theme` | 界面主题 (`dark` / `light` / `system`) |
| `window.port` | 服务端口（默认 8000） |

---

## 致谢

灵感来自斯坦福 CS336 — [Language Models from Scratch](https://cs336.stanford.edu/)。感谢课程团队的创新课件形式。

---

## License

MIT
