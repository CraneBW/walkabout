---
name: walkabout-dev
description: Walkabout 开发环境检查、构建、启动一条龙
author: walkabout
version: "1.0"
---

# Walkabout Dev

Walkabout 项目的开发工作流自动化：环境检查 → 构建前端 → 启动服务。

## 输入

无需输入。自动检测当前项目状态。

## 工作流

### 1. 环境检查

检查以下条件是否满足：

```bash
# Python 版本
python3 --version  # >= 3.9

# Node.js 版本
node --version     # >= 18

# 系统依赖（Linux）
# Arch: pacman -Q webkit2gtk gtk3
# Ubuntu: dpkg -l libwebkit2gtk-4.1*
# macOS/Windows: 无需额外检查
```

如果缺少依赖，提示安装命令（见 README.md 系统依赖章节）。

### 2. 检查 Python 依赖

```bash
cd <walkabout-repo>
python3 -c "import fastapi, uvicorn" 2>/dev/null || uv pip install -e "."
```

### 3. 构建前端

```bash
cd frontend
npm install --silent 2>/dev/null || npm install
npm run build
cd ..
```

如果前端已有 `dist/index.html` 且 `node_modules` 存在，跳过 npm install。

### 4. 启动

**有显示器（Linux/macOS/Windows 桌面）**：
```bash
python -m walkabout
```

**WSL2 / 无显示器**：
```bash
echo "WSL2 模式 — 在 Windows 浏览器打开 http://localhost:8000"
python -m walkabout
```

### 5. 开发模式（前端热重载）

如果需要修改前端代码：

```bash
# 终端 1: Vite dev server
cd frontend && npm run dev &

# 终端 2: Walkabout (会自动检测 dist/ 不存在，使用 Vite)
PYTHONPATH=$PWD python3 -m walkabout
```

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: walkabout` | PYTHONPATH 未设 | export PYTHONPATH=$PWD |
| `pywebview failed` | 系统库缺失 | 见 README 系统依赖 |
| `Frontend not built` | dist/ 不存在 | cd frontend && npm run build |
| `port 8000 in use` | 旧进程未退出 | pkill -f "python -m walkabout" |
| `Node.js not found` | nvm 未加载 | source ~/.nvm/nvm.sh |
