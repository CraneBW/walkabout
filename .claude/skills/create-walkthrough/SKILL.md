---
name: create-walkthrough
description: 在 Walkabout 工作空间创建交互式代码讲解脚本
author: walkabout
version: "1.0"
---

# Create Walkthrough

在 `~/.walkabout/notes/` 中创建交互式代码讲解 `.py` 脚本。

## 输入

用户提供主题名称（英文）。如果名称不含 `.py` 后缀，自动添加。

## 工作流

1. 确认目标路径在 `~/.walkabout/notes/` 下
2. 如果用户提供了大致内容描述，将其转化为 walkthrough 脚本
3. 使用以下模板创建文件：

```python
"""
<主题标题> — 交互式代码讲解

作者: <作者名>
日期: <今天日期>
"""

from execute_util import text, image, link, system_text


def main():
    """
    Walkabout 入口函数。每一行代码都会被追踪和回放。
    """
    text("## <主题标题>")

    # 在这里编写你的讲解代码
    # 使用 @inspect 暴露变量
    x = 42  # @inspect x
    text(f"答案是 **{x}**！")

    # 使用 system_text 运行 shell
    # system_text(["python", "--version"])

    # 使用 image 嵌入图片
    # image("figures/my_diagram.png", width=600)

    # 使用 @stepover 跳过函数内部细节
    # helper()  # @stepover

    text("## 总结")
    text("- 要点一")
    text("- 要点二")


if __name__ == "__main__":
    main()
```

4. 写入文件后，提示用户：在 Walkabout 中打开该文件，点击 ▶ Run 即可回放。

## 标注语法参考

| 语法 | 位置 | 用途 |
|------|------|------|
| `# @inspect var` | 行末注释 | 将变量值暴露到回放面板 |
| `# @stepover` | 行末注释 | 跳过该行进入函数内部 |
| `text("md")` | 代码行 | 在回放面板渲染 Markdown |
| `text("md", verbatim=True)` | 代码行 | 纯文本显示（不渲染 Markdown） |
| `image(url, width=600)` | 代码行 | 嵌入图片（本地路径或 http URL） |
| `link(url)` | 代码行 | 添加引用链接（arXiv 自动解析） |
| `system_text(["cmd", "arg"])` | 代码行 | 运行 shell 命令并显示输出 |

## 注意事项

- Walkabout 会在 `@inspect` 行执行后捕获变量值
- `@stepover` 是 toggle：第一次遇到进入函数，再次遇到退出
- 远程图片自动缓存到 `~/.walkabout/files/`
- 脚本必须定义 `main()` 函数作为入口
