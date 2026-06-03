# Walkabout

交互式代码讲解编辑器 — 写 Python 脚本，逐行回放。

## 快速开始

```bash
# 安装
pip install walkabout[gui]

# 启动
walkabout

# 或从源码运行
git clone <repo>
cd walkabout
pip install -e ".[gui]"
walkabout
```

浏览器打开 `http://localhost:8000` → 左侧新建笔记 → Monaco 编辑器写代码 → Run → 逐行回放。

## 编写 Walkthrough

```python
from execute_util import text, image, link

def main():
    text("## 我的演示")
    name = "World"  # @inspect name
    text(f"Hello {name}!")
```

- `text()` — markdown 富文本
- `image()` — 嵌入图片
- `link()` — 引用链接
- `@inspect` — 暴露变量值到回放面板
- `@stepover` — 跳过函数内部细节

## 特性

- **Monaco 编辑器** — VS Code 同款编辑体验
- **嵌入式回放** — 同一窗口切换 Edit / View
- **uv 环境管理** — 内置包安装，自动创建 venv
- **原生窗口** — pywebview，不依赖外部浏览器
- **插件系统** — 自定义渲染器、执行钩子
- **可 pip 安装** — 标准 Python 包

## 配置

```bash
# 自定义工作空间
export WALKABOUT_HOME=/path/to/workspace

# 自定义 Python 解释器
curl -X POST http://localhost:8000/api/config/python \
  -H "Content-Type: application/json" \
  -d '{"path": "/usr/bin/python3.12"}'
```

## 插件开发

```python
# ~/.walkabout/plugins/my_plugin/__init__.py
from walkabout.plugins.base import WalkaboutPlugin

class MyPlugin(WalkaboutPlugin):
    name = "my-plugin"

    def on_pre_execute(self, module_name, code):
        # Inject custom imports
        return "import numpy as np\n" + code
```

## 许可

MIT
