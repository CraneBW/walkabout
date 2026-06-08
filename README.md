<p align="center">
  <h1 align="center">Walkabout</h1>
  <p align="center">Interactive code walkthrough editor — write Python, step through line by line, replay anywhere.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python">
  <img src="https://img.shields.io/badge/tests-250-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey" alt="Platform">
</p>

---

## Download

Pre-built single-file executables — no Python installation required.

| Platform | Download | System Requirements |
|----------|----------|-------------------|
| **Windows** | `walkabout.exe` | Windows 10+ (Edge WebView2 built-in) |
| **Linux** | `walkabout-linux` | `webkit2gtk-4.1`, `gtk3` |

> [Download from GitHub Releases](https://github.com/CraneBW/walkabout/releases)

**Linux users** — install the required system libraries:

| Distribution | Command |
|-------------|---------|
| Arch | `sudo pacman -S webkit2gtk gtk3` |
| Ubuntu/Debian | `sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev` |
| Fedora | `sudo dnf install webkit2gtk4.1-devel gtk3-devel` |

---

## What is Walkabout?

Walkabout is a native desktop app for creating interactive code walkthroughs — like Jupyter Notebooks, but designed for teaching and presenting code step-by-step.

- **Write** Python scripts with special annotations (`@inspect`, `@stepover`)
- **Run** them with line-by-line tracing
- **View** execution results with variable inspection and Markdown rendering
- **Export** to standalone HTML files, shareable with anyone

<p align="center">
  <em>Screenshots: dark theme · light theme · export preview</em>
</p>

---

## Build from Source

```bash
git clone https://github.com/CraneBW/walkabout.git
cd walkabout

# Install Python dependencies
uv pip install -e ".[gui]"

# Build the frontend
cd frontend && npm install && npm run build && cd ..

# Launch
walkabout
```

---

## Writing a Walkthrough

```python
from execute_util import text, image, link

def main():
    text("## Hello, World!")
    name = "Walkabout"         # @inspect name
    text(f"Welcome to **{name}**!")

    # Shell commands
    system_text(["python", "--version"])

    # Images and links
    image("diagram.png", width=600)
    link("https://arxiv.org/abs/1706.03762")
```

### Annotation Reference

| Syntax | Purpose |
|--------|---------|
| `# @inspect var` | Expose variable values in the replay panel |
| `# @stepover` | Skip into function internals |
| `text("md")` | Render Markdown output |
| `image(url, w)` | Embed an image |
| `link(url)` | Add a reference link (arXiv auto-parsed) |
| `system_text([cmd])` | Run a shell command and display output |

---

## CLI Mode

```bash
# Execute a walkthrough headlessly, save trace JSON
walkabout run my_demo.py -o trace.json --inspect-all

# Export to standalone HTML
walkabout export my_demo.py -o demo.html --strip-source

# Export from an existing trace (skip re-execution)
walkabout export --from-trace trace.json -o demo.html
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notes` | List all notes |
| `GET/PUT/DELETE` | `/api/notes/{path}` | Read / save / delete a note |
| `POST` | `/api/notes` | Create a note |
| `POST` | `/api/execute` | Execute a walkthrough |
| `GET/POST` | `/api/export` | Export to standalone HTML |
| `GET/POST` | `/api/config` | Read / update settings |
| `GET/POST` | `/api/env` | Python environment info / install packages |

---

## Settings

Click the gear icon in the toolbar to open the Settings page (GUI mode), or edit `~/.walkabout/settings.json` directly (JSON mode). Only changed values are saved — defaults come from the schema.

| Category | Key | Type |
|----------|-----|------|
| Python | `python.path`, `python.timeout` | string, number |
| Editor | `editor.fontSize`, `editor.theme`, `editor.wordWrap`, `editor.minimap`, `editor.tabSize` | number, enum, boolean |
| Appearance | `appearance.theme`, `appearance.locale` | enum (dark/light/system) |
| Window | `window.width`, `window.height`, `window.port` | number |
| Execution | `execution.autoSave`, `execution.clearOutput`, `execution.animate` | boolean |

---

## Plugins

Create Python plugins under `~/.walkabout/plugins/` to extend Walkabout:

```python
from walkabout.plugins.base import WalkaboutPlugin

class MyPlugin(WalkaboutPlugin):
    name = "my-plugin"

    def on_pre_execute(self, module_name, code):
        """Modify code before execution."""
        return "import numpy as np\n" + code

    def on_post_execute(self, module_name, trace):
        """Modify trace after execution."""
        return trace
```

Hooks: `on_startup`, `on_pre_execute`, `on_post_execute`, `get_frontend_components`.

---

## Development

```bash
git clone https://github.com/CraneBW/walkabout.git
cd walkabout

# Python backend
uv pip install -e ".[gui]"

# Frontend (dev mode with hot reload)
cd frontend
npm install
npm run dev &
cd ..
PYTHONPATH=. python -m walkabout serve

# Run tests
pytest tests/ -v                  # Python (208 tests)
cd frontend && npx vitest run     # Frontend (42 tests)
ruff check . && cd frontend && npx eslint src/   # Lint

# CI runs lint + tests on every push/PR (.github/workflows/ci.yml)
```

---

## License

MIT
