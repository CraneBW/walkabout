import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import FileBrowser from '../components/FileBrowser';
import Editor from '../components/Editor';
import TraceViewer from '../TraceViewer';
import { listNotes, getNote, saveNote, createNote, deleteNote, executeNote, exportNote, saveExport } from '../api';
import { getEnvInfo, installPackages } from '../api';
import { initTheme, toggleTheme, getCurrentTheme } from '../theme';
import { computeEnv, computeDecorations } from '../utils';
import axios from 'axios';

export default function EditorPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [files, setFiles] = useState([]);
  const [selectedPath, setSelectedPath] = useState(null);
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // Embedded viewer tab
  const [tab, setTab] = useState('edit'); // 'edit' | 'view'
  const [traceUrl, setTraceUrl] = useState(null);
  const [traceData, setTraceData] = useState(null);

  // Zen mode (fullscreen + hide chrome)
  const [zenMode, setZenMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Sidebar toggle (independent of zen mode)
  const [sidebarVisible, setSidebarVisible] = useState(true);

  // Theme
  const [currentTheme, setCurrentTheme] = useState(getCurrentTheme());

  // Editor settings (fontSize, etc.) — initialized from API and kept in sync via postMessage
  const [editorSettings, setEditorSettings] = useState({ fontSize: 14 });

  useEffect(() => {
    axios.get('/api/config').then(r => {
      const fontSize = r.data?.editor?.fontSize;
      if (fontSize) {
        setEditorSettings({ fontSize });
      }
    }).catch(() => {});
  }, []);

  // Listen for settings changes broadcast from SettingsPage
  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === 'settings-changed' && e.data?.key?.startsWith('editor.')) {
        const { key, value } = e.data;
        if (key === 'editor.fontSize') {
          setEditorSettings({ fontSize: value });
        }
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // Toast notifications
  const [toast, setToast] = useState(null);

  const toastTimer = useRef(null);
  const showToast = (msg) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(msg);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  };

  // Initialize theme from settings
  useEffect(() => {
    axios.get('/api/config').then(r => {
      const theme = r.data?.appearance?.theme;
      if (theme) {
        initTheme(theme);
        setCurrentTheme(theme);
      } else {
        initTheme();
      }
    }).catch(() => { initTheme(); });
  }, []);

  // Fetch trace data when a trace URL is available
  useEffect(() => {
    if (!traceUrl) {
      setTraceData(null);
      return;
    }
    const fetchTrace = async () => {
      try {
        const response = await axios.get(traceUrl);
        setTraceData(response.data);
      } catch (e) {
        console.error('Failed to fetch trace:', e);
      }
    };
    fetchTrace();
  }, [traceUrl]);

  // Compute inline decorations from the current trace step and source file.
  // Triggers on every URL change (TraceViewer navigates between steps).
  const decorations = useMemo(() => {
    if (tab !== 'view' || !traceData) return [];

    const params = new URLSearchParams(location.search);
    const stepIndex = parseInt(params.get('step'));
    // Use ?source param if available, otherwise fall back to selectedPath
    const sourcePath = params.get('source') || selectedPath;

    if (isNaN(stepIndex)) return [];
    if (!sourcePath || !traceData.files || !traceData.files[sourcePath]) return [];

    const env = computeEnv(traceData, stepIndex);
    return computeDecorations(env, traceData.files[sourcePath]);
  }, [tab, traceData, location.search, selectedPath]);

  const handleToggleTheme = () => {
    const next = toggleTheme();
    setCurrentTheme(next);
    // Persist to API so the setting survives page navigation.
    // Without this, EditorPage re-mount (e.g. after visiting Settings)
    // would fetch the stale API value and overwrite the toggle.
    axios.post('/api/config/set', { key: 'appearance.theme', value: next }).catch(() => {});
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen();
    }
  };

  const toggleZen = () => {
    const next = !zenMode;
    setZenMode(next);
    if (next && !document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else if (!next && document.fullscreenElement) {
      document.exitFullscreen();
    }
  };

  // ESC exits zen mode
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && zenMode) {
        setZenMode(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [zenMode]);

  // Package install
  const [showInstall, setShowInstall] = useState(false);
  const [pkgInput, setPkgInput] = useState('');
  const [installing, setInstalling] = useState(false);

  const refreshFiles = useCallback(async () => {
    try {
      const data = await listNotes();
      setFiles(data);
    } catch (e) {
      setError('Cannot connect to server');
    }
  }, []);

  useEffect(() => { refreshFiles(); }, [refreshFiles]);

  // Restore selected file from URL or sessionStorage on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fileParam = params.get('file');
    if (fileParam) {
      selectNote(fileParam);
    } else {
      const lastFile = sessionStorage.getItem('walkabout_last_file');
      if (lastFile) {
        selectNote(lastFile);
      }
    }
  }, []);

  const selectNote = async (path) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNote(path);
      setSelectedPath(path);
      setContent(data.content);
      setDirty(false);
      setExecResult(null);
      if (data.trace_url) {
        setTraceUrl(data.trace_url);
      } else {
        setTraceUrl(null);
      }
      navigate('?file=' + encodeURIComponent(path), { replace: true });
      sessionStorage.setItem('walkabout_last_file', path);
      setTab('edit');
    } catch (e) {
      setError('Failed to load: ' + path);
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!selectedPath) return;
    setSaving(true);
    setError(null);
    try {
      await saveNote(selectedPath, content);
      setDirty(false);
      await refreshFiles();
    } catch (e) {
      setError('Save failed');
    }
    setSaving(false);
  };

  const handleRun = async () => {
    if (!selectedPath) return;
    setExecuting(true);
    setError(null);
    setExecResult(null);
    try {
      if (dirty) {
        await saveNote(selectedPath, content);
        setDirty(false);
      }
      const result = await executeNote(selectedPath);
      setExecResult(result);
      if (result.status === 'ok') {
        setTraceUrl(result.trace_url);
        navigate('?trace=' + encodeURIComponent(result.trace_url));
        setTab('view');  // Switch to embedded viewer
      }
    } catch (e) {
      setError('Execution failed');
    }
    setExecuting(false);
  };

  const handleExport = async () => {
    if (!selectedPath) return;
    setExporting(true);
    setError(null);
    try {
      if (dirty) {
        await saveNote(selectedPath, content);
        setDirty(false);
      }
      // Run first to generate trace, then download standalone HTML
      const result = await executeNote(selectedPath, content);
      if (result.status !== 'ok') {
        throw new Error(result.error || 'Execution failed');
      }
      // Save to configured export directory on disk
      const saveResult = await saveExport(selectedPath);
      showToast('Exported → ' + saveResult.path);
    } catch (e) {
      setError('Export failed: ' + (e.message || e));
    }
    setExporting(false);
  };

  const handleInstall = async () => {
    if (!pkgInput.trim()) return;
    setInstalling(true);
    try {
      const pkgs = pkgInput.split(/[\s,]+/).filter(Boolean);
      await installPackages(pkgs);
      setPkgInput('');
      setError(null);
    } catch (e) {
      setError('Install failed: ' + (e.response?.data?.detail || e.message));
    }
    setInstalling(false);
    setShowInstall(false);
  };

  const handleNew = async (name) => {
    try {
      const data = await createNote(name);
      await refreshFiles();
      selectNote(data.path);
    } catch (e) {
      setError('Failed to create note');
    }
  };

  const handleDelete = async (path) => {
    try {
      await deleteNote(path);
      if (path === selectedPath) {
        setSelectedPath(null);
        setContent('');
        setTab('edit');
        setTraceUrl(null);
        navigate('', { replace: true });
      }
      await refreshFiles();
    } catch (e) {
      setError('Failed to delete');
    }
  };

  const exitZen = () => {
    setZenMode(false);
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  };

  return (
    <div className={`editor-page${zenMode ? ' zen-mode' : ''}${!sidebarVisible ? ' sidebar-hidden' : ''}`}>
      <header className="toolbar">
        <span className="logo">Walkabout</span>
        <span className="toolbar-actions">
          {selectedPath && (
            <>
              <span className="file-path">{selectedPath}</span>
              <button onClick={() => setTab('edit')} className={tab === 'edit' ? 'tab-active' : ''}>
                ✏️ Edit
              </button>
              {traceUrl && (
                <button onClick={() => {
                  navigate('?trace=' + encodeURIComponent(traceUrl));
                  setTab('view');
                }} className={tab === 'view' ? 'tab-active' : ''}>
                  👁 View
                </button>
              )}
              <span className="toolbar-sep" />
              <button onClick={handleSave} disabled={saving || !dirty}>
                {saving ? 'Saving...' : dirty ? '💾 *' : '💾'}
              </button>
              <button onClick={handleRun} disabled={executing} className="run-btn">
                {executing ? '⏳' : '▶'} Run
              </button>
              <button onClick={handleExport} disabled={exporting} className="export-btn" title="Export as standalone HTML">
                {exporting ? '⏳' : '↓'} Export
              </button>
              <button onClick={() => setSidebarVisible(!sidebarVisible)} title={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'} className="sidebar-toggle-btn">
                {sidebarVisible ? '☰' : '☰'}
              </button>
              <button onClick={handleToggleTheme} title="Toggle theme" className="theme-toggle-btn">
                {currentTheme === 'light' ? '☀' : '☾'}
              </button>
              <button onClick={toggleZen} title={zenMode ? 'Exit zen mode' : 'Zen mode (hide chrome)'} className="fs-btn">
                {zenMode ? '◻' : '⊞'}
              </button>
              <button onClick={() => navigate('/settings')} title="Settings" className="gear-btn">⚙</button>
              <button onClick={() => setShowInstall(!showInstall)} title="Install packages" className="pkg-btn">
                📦
              </button>
            </>
          )}
        </span>
      </header>

      {showInstall && (
        <div className="install-bar">
          <input
            value={pkgInput}
            onChange={(e) => setPkgInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleInstall()}
            placeholder="torch numpy matplotlib..."
          />
          <button onClick={handleInstall} disabled={installing}>
            {installing ? '...' : 'uv install'}
          </button>
          <button onClick={() => setShowInstall(false)}>×</button>
        </div>
      )}

      <div className="main-area">
        <FileBrowser
          files={files}
          selectedPath={selectedPath}
          onSelect={selectNote}
          onNew={handleNew}
          onDelete={handleDelete}
        />
        <div className="editor-area">
          {error && <div className="error-banner">{error} <button onClick={() => setError(null)}>×</button></div>}
          {zenMode && (
            <button className="exit-zen-btn" onClick={exitZen} title="Exit zen mode (ESC)">
              ⊞ Exit zen
            </button>
          )}
          {execResult && execResult.status === 'error' && (
            <div className="exec-error">
              <strong>Execution Error:</strong>
              <pre>{execResult.error}</pre>
            </div>
          )}
          {loading ? (
            <div className="loading">Loading...</div>
          ) : tab === 'view' && traceUrl ? (
            <div className="viewer-embed" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1, overflow: 'auto' }}>
                <TraceViewer />
              </div>
              {selectedPath && traceData?.files?.[selectedPath] && (
                <div style={{ height: '35%', minHeight: 200, borderTop: '1px solid var(--border-glass)' }}>
                  <Editor
                    content={traceData.files[selectedPath]}
                    onChange={() => {}}
                    settings={editorSettings}
                    decorations={decorations}
                  />
                </div>
              )}
            </div>
          ) : selectedPath ? (
            <Editor
              content={content}
              onChange={(v) => { setContent(v); setDirty(true); }}
              settings={editorSettings}
            />
          ) : (
            <div className="welcome">
              <div className="welcome-icon">?</div>
              <h2>Walkabout</h2>
              <p>Interactive code walkthrough editor. Select a note from the sidebar to begin, or create a new one.</p>
              <div className="welcome-shortcuts">
                <span className="welcome-kbd">Ctrl+N</span> New
                <span className="welcome-kbd">Ctrl+S</span> Save
                <span className="welcome-kbd">Ctrl+Enter</span> Run
                <span className="welcome-kbd">F11</span> Zen
              </div>
              <p className="welcome-hint">Click the package icon in the toolbar to install Python dependencies.</p>
            </div>
          )}
        </div>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
