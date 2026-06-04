"""Export trace JSON to a self-contained static HTML file.

The generated HTML bundles the trace data and a standalone viewer so
the walkthrough can be shared and viewed without a Python backend.
"""
import json
from pathlib import Path
from typing import Any, Optional


def _clean_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Strip unreferenced source code, keeping only lines that appear in steps.

    Walks every stack frame across all steps and rebuilds file contents from
    only the code lines that were actually executed.  Any line number that is
    never referenced becomes an empty line in the reconstructed file so the
    viewer's line-numbering stays correct.
    """
    steps = trace.get("steps", [])
    file_lines: dict[str, dict[int, str]] = {}  # path -> {line_number: code}

    for step in steps:
        for frame in step.get("stack", []):
            path = frame.get("path", "")
            line = frame.get("line_number", 0)
            code = frame.get("code", "")
            if path and line:
                file_lines.setdefault(path, {})[line] = code

    cleaned: dict[str, str] = {}
    for path, lines in file_lines.items():
        max_line = max(lines)
        cleaned[path] = "\n".join(lines.get(i, "") for i in range(1, max_line + 1))

    trace = dict(trace)
    trace["files"] = cleaned
    return trace


def generate_html(
    trace: dict[str, Any],
    title: str = "Walkthrough",
    strip_source: bool = False,
) -> str:
    """Generate a self-contained HTML file from a trace dict.

    When *strip_source* is True, only the lines referenced in step stack
    frames are kept in the embedded files — unreferenced source code is
    stripped from the export.  The viewer still renders a full file view
    with syntax highlighting for the lines that remain.
    """
    if strip_source:
        trace = _clean_trace(trace)
    trace_json = json.dumps(trace, ensure_ascii=False, indent=2)
    files: dict[str, str] = trace.get("files", {})
    file_entries = "".join(
        f'<option value="{k}">{k}</option>' for k in files
    )
    file_style = "display:none" if not files else ""

    title_escaped = _escape_html(title)
    html = _TEMPLATE
    html = html.replace("__TITLE__", title_escaped)
    html = html.replace("__TRACE_JSON__", trace_json)
    html = html.replace("__FILE_ENTRIES__", file_entries)
    html = html.replace("__FILE_SELECT_STYLE__", file_style)
    return html


def export_note(
    trace_path: Path,
    output_path: Path,
    title: Optional[str] = None,
    strip_source: bool = False,
) -> Path:
    """Read a trace JSON file and write a standalone HTML file.

    Returns the path to the generated HTML file.
    """
    with open(trace_path, encoding="utf-8") as f:
        trace = json.load(f)

    name = title or trace_path.stem
    html = generate_html(trace, title=name, strip_source=strip_source)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── The standalone viewer HTML template ──────────────────────────────

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Walkabout - __TITLE__</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #d4d4d4; }

/* Header */
.header { display: flex; align-items: center; justify-content: space-between; padding: 8px 20px; background: #252526; border-bottom: 1px solid #3c3c3c; position: sticky; top: 0; z-index: 10; flex-wrap: wrap; gap: 6px; }
.header-title { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.header-title select { background: #3c3c3c; color: #ccc; border: 1px solid #555; padding: 2px 6px; border-radius: 3px; font-size: 12px; }
.icon-buttons { display: flex; gap: 4px; align-items: center; font-size: 13px; }
.icon-buttons button { background: none; border: 1px solid #555; color: #ccc; padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 13px; }
.icon-buttons button:hover { background: #3c3c3c; }
.icon-buttons button:disabled { opacity: 0.4; cursor: default; }
.step-counter { color: #888; font-size: 12px; margin: 0 4px; }

/* Lines panel */
.lines-panel { padding: 8px 0; font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.6; }
.line { display: flex; min-height: 22px; padding: 0; }
.line-number { width: 48px; text-align: right; padding-right: 12px; color: #555; flex-shrink: 0; user-select: none; cursor: pointer; }
.line-number:hover { color: #ccc; }
.code-container { white-space: pre-wrap; word-break: break-all; flex: 1; padding-right: 12px; }
.current-line { background: #2a2d2e; }
.current-line .line-number { color: #60c0ff; }
.renderings { padding: 4px 0 4px 60px; border-left: 2px solid #444; margin: 4px 0 4px 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

/* Markdown */
.markdown h1, .markdown h2, .markdown h3 { color: #e0e0e0; margin: 8px 0 4px; }
.markdown p { margin: 4px 0; }
.markdown strong { color: #ffcb6b; }
.markdown ul, .markdown ol { margin: 4px 0; padding-left: 24px; }
.markdown li { margin: 2px 0; }
.markdown code { background: #2d2d30; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
.markdown pre { background: #2d2d30; padding: 8px 12px; border-radius: 4px; overflow-x: auto; margin: 8px 0; }
.markdown pre code { background: none; padding: 0; }
.markdown blockquote { border-left: 3px solid #555; padding-left: 12px; color: #888; margin: 8px 0; }
.markdown a { color: #60c0ff; }
.markdown img { max-width: 100%; border-radius: 4px; margin: 8px 0; }

/* Env panel */
.env-panel { position: fixed; top: 60px; right: 20px; background: #252526; border: 1px solid #555; border-radius: 6px; padding: 12px; max-width: 360px; max-height: 300px; overflow-y: auto; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.5); cursor: move; font-size: 12px; min-width: 180px; }
.env-panel h4 { color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 6px; }
.env-panel table { width: 100%; border-collapse: collapse; }
.env-panel td { padding: 2px 4px; vertical-align: top; border-bottom: 1px solid #2d2d30; font-family: 'Fira Code', monospace; font-size: 11px; word-break: break-all; }
.env-panel td:first-child { color: #60c0ff; white-space: nowrap; padding-right: 8px; }
.env-empty { color: #555; font-style: italic; font-size: 11px; }

/* External link hover */
.link-container { position: relative; display: inline; }
.link-hover-panel { display: none; position: absolute; bottom: 100%; left: 0; background: #333; border: 1px solid #555; border-radius: 4px; padding: 8px; min-width: 220px; z-index: 50; font-size: 12px; margin-bottom: 4px; }
.link-container:hover .link-hover-panel { display: block; }
.external-link { color: #60c0ff; text-decoration: none; cursor: pointer; }
.external-link:hover { text-decoration: underline; }
.internal-link { color: #60c0ff; text-decoration: none; cursor: pointer; border-bottom: 1px dashed #60c0ff; }
.internal-link:hover { text-decoration: underline; }
.link-title { font-weight: 600; color: #e0e0e0; }
.link-authors, .link-date, .link-description, .link-notes { color: #888; font-size: 11px; margin-top: 2px; }

/* Error toast */
.error-toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #5a1d1d; color: #f48771; padding: 8px 16px; border-radius: 4px; font-size: 12px; z-index: 9999; }
</style>
</head>
<body>

<div id="app">
  <div class="header">
    <div class="header-title">
      <strong>__TITLE__</strong>
      <span id="file-select-wrap" style="__FILE_SELECT_STYLE__">
        <select id="file-select">__FILE_ENTRIES__</select>
      </span>
    </div>
    <div class="icon-buttons">
      <button id="prev-btn" title="Previous step (&#x2190;)">&#x25C0;</button>
      <span class="step-counter"><span id="step-num">0</span> / <span id="step-total">0</span></span>
      <button id="next-btn" title="Next step (&#x2192;)">&#x25B6;</button>
    </div>
  </div>
  <div class="lines-panel" id="lines-panel"></div>
</div>

<div class="env-panel" id="env-panel">
  <h4>Variables</h4>
  <div id="env-content"><span class="env-empty">No variables</span></div>
</div>

<!-- Trace data embedded as JSON -->
<script id="trace-data" type="application/json">__TRACE_JSON__</script>

<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']]
  },
  svg: { fontCache: 'global' }
};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<script>
(function () { 'use strict';

/* Load trace */
var trace = JSON.parse(document.getElementById('trace-data').textContent);
var files = trace.files || {};
var steps = trace.steps || [];
var currentIndex = 0;
var currentPath = Object.keys(files)[0] || '';
/* When source files were stripped, grab path from first step */
if (!currentPath && steps.length > 0 && steps[0].stack && steps[0].stack.length > 0) {
    currentPath = steps[0].stack[steps[0].stack.length - 1].path || '';
}

document.getElementById('step-total').textContent = steps.length;

/* Env panel drag */
var envPanel = document.getElementById('env-panel');
var dragOffset = { rx: 0, y: 0 };
var dragging = false;

envPanel.addEventListener('mousedown', function (e) {
    var rect = envPanel.getBoundingClientRect();
    dragOffset = { rx: window.innerWidth - e.clientX, y: e.clientY - rect.top };
    dragging = true;
    e.preventDefault();
});
document.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    envPanel.style.right = (window.innerWidth - e.clientX - dragOffset.rx) + 'px';
    envPanel.style.top = (e.clientY - dragOffset.y) + 'px';
    envPanel.style.left = 'auto';
    envPanel.style.bottom = 'auto';
});
document.addEventListener('mouseup', function () { dragging = false; });

/* Helpers */
function getStepPath(idx) {
    var s = steps[idx];
    return s && s.stack && s.stack.length ? s.stack[s.stack.length - 1].path : currentPath;
}
function getStepLine(idx) {
    var s = steps[idx];
    return s && s.stack && s.stack.length ? s.stack[s.stack.length - 1].line_number : 1;
}
function getStepFn(idx) {
    var s = steps[idx];
    return s && s.stack && s.stack.length ? s.stack[s.stack.length - 1].function_name : '';
}
function getStepDepth(idx) {
    return steps[idx] && steps[idx].stack ? steps[idx].stack.length : 0;
}
function escapeHtml(s) {
    if (typeof s !== 'string') s = String(s);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* Line index: which step indices map to each (path:line) */
function buildLineIndex() {
    var idx = {};
    for (var i = 0; i < steps.length; i++) {
        var key = getStepPath(i) + ':' + getStepLine(i);
        if (!idx[key]) idx[key] = [];
        idx[key].push(i);
    }
    return idx;
}
var lineIndex = buildLineIndex();

function getRenderingsForLine(path, line) {
    var si = lineIndex[path + ':' + line];
    if (!si || !si.length) return [];
    return steps[si[si.length - 1]].renderings || [];
}

function renderValue(v) {
    if (v === null) return '<span style="color:#569cd6">null</span>';
    if (v === undefined) return '<span style="color:#569cd6">undefined</span>';
    if (typeof v === 'boolean') return '<span style="color:#569cd6">' + v + '</span>';
    if (typeof v === 'number') return '<span style="color:#b5cea8">' + v + '</span>';
    if (typeof v === 'string') return '<span style="color:#ce9178">"' + escapeHtml(v) + '"</span>';
    try { return '<pre style="margin:0;font-size:11px">' + escapeHtml(JSON.stringify(v, null, 2)) + '</pre>'; }
    catch (e) { return escapeHtml(String(v)); }
}

function renderRendering(r) {
    var type = r.type || 'text';
    var data = r.data || '';
    var style = r.style || {};
    var styleStr = '';
    Object.keys(style).forEach(function (k) { styleStr += k + ':' + style[k] + ';'; });

    if (type === 'markdown') {
        var mdHtml = '';
        try { mdHtml = marked.parse(data); } catch (e) { mdHtml = escapeHtml(data); }
        return '<div class="markdown">' + mdHtml + '</div>';
    }
    if (type === 'image') {
        return '<img src="' + escapeHtml(data) + '" style="' + styleStr + '" alt="" loading="lazy">';
    }
    if (type === 'link') {
        if ((r.external_link || {}).url) {
            var el = r.external_link;
            return '<div class="link-container">' +
                '<a class="external-link" href="' + escapeHtml(el.url) + '" target="_blank" rel="noopener">' +
                escapeHtml(data || el.url) + '</a>' +
                '<div class="link-hover-panel">' +
                (el.title ? '<div class="link-title">' + escapeHtml(el.title) + '</div>' : '') +
                (el.authors && el.authors.length ? '<div class="link-authors">' + escapeHtml(el.authors.join(', ')) + '</div>' : '') +
                (el.date ? '<div class="link-date">' + escapeHtml(el.date) + '</div>' : '') +
                (el.description ? '<div class="link-description">' + escapeHtml(el.description) + '</div>' : '') +
                (el.notes ? '<div class="link-notes">' + escapeHtml(el.notes) + '</div>' : '') +
                '</div></div>';
        }
        if ((r.internal_link || {}).path) {
            var il = r.internal_link;
            return '<a class="internal-link" href="#" data-path="' + escapeHtml(il.path) +
                '" data-line="' + il.line_number + '">' + escapeHtml(data) + '</a>';
        }
        return '<span>' + escapeHtml(data) + '</span>';
    }
    return '<span style="' + styleStr + '">' + escapeHtml(data) + '</span>';
}

function renderLines() {
    var panel = document.getElementById('lines-panel');
    var path = currentPath;
    var source = files[path] || '';
    var currentLine = getStepLine(currentIndex);

    /* When source files are not available (stripped for privacy), show step stack only */
    if (!source) {
        renderStepOnly(panel);
        renderEnv();
        document.getElementById('step-num').textContent = currentIndex;
        if (window.MathJax && MathJax.typesetPromise) {
            MathJax.typesetPromise([panel]).catch(function () {});
        }
        return;
    }

    var allLines = source.split('\\n');

    /* Syntax highlight */
    var highlighted = '';
    try { highlighted = hljs.highlight(source, { language: 'python' }).value; }
    catch (e) { highlighted = escapeHtml(source); }
    var hlLines = highlighted.split('\\n');

    var html = '';
    for (var i = 0; i < allLines.length; i++) {
        var lineNum = i + 1;
        var cls = 'line';
        if (lineNum === currentLine) cls += ' current-line';

        html += '<div class="' + cls + '">';
        html += '<span class="line-number" data-path="' + escapeHtml(path) + '" data-line="' + lineNum + '">' + lineNum + '</span>';
        html += '<span class="code-container">' + (hlLines[i] || '') + '</span>';
        html += '</div>';

        var renderings = getRenderingsForLine(path, lineNum);
        if (renderings.length > 0) {
            html += '<div class="renderings">';
            for (var r = 0; r < renderings.length; r++) {
                html += renderRendering(renderings[r]);
            }
            html += '</div>';
        }
    }

    panel.innerHTML = html;

    /* Scroll current line into view */
    var lines = panel.querySelectorAll('.line');
    for (var i = 0; i < lines.length; i++) {
        if (lines[i].classList.contains('current-line')) {
            if (lines[i].scrollIntoViewIfNeeded) lines[i].scrollIntoViewIfNeeded();
            else lines[i].scrollIntoView({ block: 'center' });
            break;
        }
    }

    renderEnv();
    document.getElementById('step-num').textContent = currentIndex;

    if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([panel]).catch(function () {});
    }
}

/* Render current step stack frames when full file source is not available */
function renderStepOnly(panel) {
    var step = steps[currentIndex];
    if (!step || !step.stack || step.stack.length === 0) {
        panel.innerHTML = '<div class="env-empty" style="padding:20px;text-align:center">No source code available</div>';
        return;
    }
    var html = '';
    for (var s = 0; s < step.stack.length; s++) {
        var frame = step.stack[s];
        var cls = (s === step.stack.length - 1) ? 'line current-line' : 'line';
        html += '<div class="' + cls + '">';
        html += '<span class="line-number" data-path="' + escapeHtml(frame.path) + '" data-line="' + frame.line_number + '">' + frame.line_number + '</span>';
        html += '<span class="code-container">' + escapeHtml(frame.code) + '</span>';
        html += '</div>';
    }
    var renderings = step.renderings || [];
    if (renderings.length > 0) {
        html += '<div class="renderings">';
        for (var r = 0; r < renderings.length; r++) {
            html += renderRendering(renderings[r]);
        }
        html += '</div>';
    }
    panel.innerHTML = html;
}

function renderEnv() {
    if (!steps[currentIndex]) return;
    var fn = getStepFn(currentIndex);

    var merged = {};
    for (var i = currentIndex; i >= 0; i--) {
        if (getStepFn(i) !== fn) break;
        var env = steps[i].env || {};
        Object.keys(env).forEach(function (k) { merged[k] = env[k]; });
    }

    var keys = Object.keys(merged);
    var content = document.getElementById('env-content');
    if (keys.length === 0) {
        content.innerHTML = '<span class="env-empty">No variables</span>';
        return;
    }
    var tbl = '<table>';
    for (var k = 0; k < keys.length; k++) {
        tbl += '<tr><td>' + escapeHtml(keys[k]) + '</td><td>' + renderValue(merged[keys[k]]) + '</td></tr>';
    }
    tbl += '</table>';
    content.innerHTML = tbl;
}

function jumpToLine(path, line) {
    currentPath = path;
    document.getElementById('file-select').value = path;
    for (var i = 0; i < steps.length; i++) {
        if (getStepPath(i) === path && getStepLine(i) === line) {
            currentIndex = i;
            renderLines();
            updateButtons();
            return;
        }
    }
}

function updateButtons() {
    document.getElementById('prev-btn').disabled = (currentIndex <= 0);
    document.getElementById('next-btn').disabled = (currentIndex >= steps.length - 1);
}

/* Event delegation: handle clicks on line numbers, internal links, and buttons */
document.addEventListener('click', function (e) {
    var t = e.target;

    /* Line number click -> jump to that line's step */
    if (t.classList.contains('line-number')) {
        jumpToLine(t.dataset.path, parseInt(t.dataset.line));
        return;
    }

    /* Internal link click -> jump to referenced code location */
    if (t.classList.contains('internal-link')) {
        e.preventDefault();
        jumpToLine(t.dataset.path, parseInt(t.dataset.line));
        return;
    }

    /* Button clicks */
    if (t.id === 'prev-btn' || t.parentElement.id === 'prev-btn') {
        if (currentIndex > 0) { currentIndex--; renderLines(); updateButtons(); }
        return;
    }
    if (t.id === 'next-btn' || t.parentElement.id === 'next-btn') {
        if (currentIndex < steps.length - 1) { currentIndex++; renderLines(); updateButtons(); }
        return;
    }
});

/* File selector switch */
var fileSelect = document.getElementById('file-select');
if (fileSelect) {
    fileSelect.addEventListener('change', function () {
        currentPath = this.value;
        renderLines();
    });
}

/* Keyboard navigation */
document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if (e.key === 'ArrowLeft') {
        e.shiftKey ? stepOver(-1) : (currentIndex > 0 ? (currentIndex--, renderLines(), updateButtons()) : 0);
    } else if (e.key === 'ArrowRight') {
        e.shiftKey ? stepOver(1) : (currentIndex < steps.length - 1 ? (currentIndex++, renderLines(), updateButtons()) : 0);
    }
});

function stepOver(dir) {
    var depth = getStepDepth(currentIndex);
    var start = currentIndex + dir;
    var end = dir > 0 ? steps.length : -1;
    var step = dir > 0 ? 1 : -1;
    for (var i = start; i !== end; i += step) {
        if (getStepDepth(i) <= depth) { currentIndex = i; renderLines(); updateButtons(); return; }
    }
    currentIndex = dir > 0 ? steps.length - 1 : 0;
    renderLines();
    updateButtons();
}

/* Bootstrap */
currentPath = Object.keys(files)[0] || '';
renderLines();
updateButtons();

})();
</script>
</body>
</html>
"""
