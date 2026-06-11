import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import FileBrowser from '../components/FileBrowser';
import Editor from '../components/Editor';
import TabBar from '../components/TabBar';
import TraceViewer from '../TraceViewer';
import { listNotes, getNote, saveNote, createNote, deleteNote, executeNote, exportNote, saveExport } from '../api';
import { getEnvInfo, installPackages } from '../api';
import { initTheme, toggleTheme, getCurrentTheme } from '../theme';
import { computeEnv, computeDecorations } from '../utils';
import axios from 'axios';

export default function EditorPage() {
  const navigate = useNavigate();

  // ── Multi-tab state ────────────────────────────────────────
  const [tabs, setTabs] = useState([]);       // Tab[]
  const [activeTabId, setActiveTabId] = useState(null);
  const activeTab = useMemo(
    () => tabs.find((t) => t.id === activeTabId) || null,
    [tabs, activeTabId],
  );

  // Derived convenience values (mirror original single-file API)
  const selectedPath = activeTab?.path || null;
  const content = activeTab?.content || '';
  const dirty = activeTab?.dirty || false;
  const tabMode = activeTab?.tabMode || 'edit';
  const traceUrl = activeTab?.traceUrl || null;

  // ── Refs (tabs ref + Monaco model management) ────────────
  const tabsRef = useRef([]);
  useEffect(() => { tabsRef.current = tabs; }, [tabs]);

  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const modelsRef = useRef({});       // tabId → ITextModel
  const viewStatesRef = useRef({});   // tabId → IEditorViewState

  // MRU activation order (most-recently-used first)
  const tabOrderRef = useRef([]);

  // ── Remaining state (unchanged from original) ──────────────
  const [files, setFiles] = useState([]);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [zenMode, setZenMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [currentTheme, setCurrentTheme] = useState(getCurrentTheme());
  // URL version counter — incremented on popstate to trigger decoration re-computation
  const [urlVersion, setUrlVersion] = useState(0);
  const [editorSettings, setEditorSettings] = useState({ fontSize: 14 });
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);
  const [showInstall, setShowInstall] = useState(false);
  const [pkgInput, setPkgInput] = useState('');
  const [installing, setInstalling] = useState(false);

  // ── Toast helper ──────────────────────────────────────────
  const showToast = (msg) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(msg);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  };

  // ── Editor settings from API ──────────────────────────────
  useEffect(() => {
    axios.get('/api/config').then((r) => {
      const fontSize = r.data?.editor?.fontSize;
      if (fontSize) setEditorSettings({ fontSize });
    }).catch(() => {});
  }, []);

  // ── Listen for settings changes ───────────────────────────
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

  // ── Theme initialization ──────────────────────────────────
  useEffect(() => {
    axios.get('/api/config').then((r) => {
      const theme = r.data?.appearance?.theme;
      if (theme) { initTheme(theme); setCurrentTheme(theme); }
      else { initTheme(); }
    }).catch(() => { initTheme(); });
  }, []);

  // ── Fetch trace data when a tab has a trace URL ───────────
  useEffect(() => {
    const tabId = activeTabId;
    const url = activeTab?.traceUrl;
    if (!url) return;

    let cancelled = false;
    const fetchTrace = async () => {
      try {
        const response = await axios.get(url);
        if (!cancelled) {
          setTabs((prev) =>
            prev.map((t) =>
              t.id === tabId ? { ...t, traceData: response.data } : t,
            ),
          );
        }
      } catch (e) {
        if (!cancelled) console.error('Failed to fetch trace:', e);
      }
    };
    fetchTrace();
    return () => { cancelled = true; };
  }, [activeTab?.traceUrl, activeTabId]);

  // Listen for popstate events (TraceViewer pushState + browser back/forward)
  useEffect(() => {
    const handler = () => setUrlVersion(v => v + 1);
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, []);

  // ── Inline decorations from trace step ──────────────────
  const decorations = useMemo(() => {
    if (activeTab?.tabMode !== 'view' || !activeTab?.traceData) return [];

    const params = new URLSearchParams(window.location.search);
    const stepIndex = parseInt(params.get('step'));
    const sourcePath = params.get('source') || activeTab.path;

    if (isNaN(stepIndex)) return [];
    if (!sourcePath || !activeTab.traceData.files || !activeTab.traceData.files[sourcePath]) return [];

    const env = computeEnv(activeTab.traceData, stepIndex);
    return computeDecorations(env, activeTab.traceData.files[sourcePath]);
  }, [activeTab?.tabMode, activeTab?.traceData, activeTab?.path, urlVersion]);

  // ── Fullscreen handler ─────────────────────────────────────
  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) { document.exitFullscreen(); }
    else { document.documentElement.requestFullscreen(); }
  };

  const toggleZen = () => {
    const next = !zenMode;
    setZenMode(next);
    if (next && !document.fullscreenElement) { document.documentElement.requestFullscreen(); }
    else if (!next && document.fullscreenElement) { document.exitFullscreen(); }
  };

  // ── ESC exits zen mode ─────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && zenMode) setZenMode(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [zenMode]);

  // ── File list ──────────────────────────────────────────────
  const refreshFiles = useCallback(async () => {
    try { const data = await listNotes(); setFiles(data); }
    catch (e) { setError('Cannot connect to server'); }
  }, []);

  useEffect(() => { refreshFiles(); }, [refreshFiles]);

  // ── SessionStorage persistence ─────────────────────────────
  useEffect(() => {
    if (tabs.length > 0 && activeTabId) {
      const persisted = tabs.map((t) => ({
        id: t.id,
        path: t.path,
        dirty: t.dirty,
        tabMode: t.tabMode,
      }));
      sessionStorage.setItem('walkabout_tabs', JSON.stringify(persisted));
      sessionStorage.setItem('walkabout_active_tab', activeTabId);
      // Keep backward compatibility
      sessionStorage.setItem('walkabout_last_file', activeTabId);
    } else {
      sessionStorage.removeItem('walkabout_tabs');
      sessionStorage.removeItem('walkabout_active_tab');
    }
  }, [tabs, activeTabId]);

  // ── Mount: restore from URL or sessionStorage ──────────────
  useEffect(() => {
    (async () => {
      const params = new URLSearchParams(window.location.search);
      const fileParam = params.get('file');

      if (fileParam) {
        await selectNote(fileParam);
        return;
      }

      // Try restoring full tab state from sessionStorage
      const savedTabs = sessionStorage.getItem('walkabout_tabs');
      if (savedTabs) {
        try {
          const parsed = JSON.parse(savedTabs);
          const restored = await Promise.all(
            parsed.map((t) =>
              getNote(t.id).then((data) => ({
                id: t.id,
                path: t.path,
                content: data.content,
                dirty: false,           // Content re-fetched from API
                tabMode: t.tabMode || 'edit',
                traceUrl: data.trace_url || null,
                traceData: null,
              })),
            ),
          );
          const savedActive = sessionStorage.getItem('walkabout_active_tab');
          const validActive = savedActive && restored.some((t) => t.id === savedActive);
          setTabs(restored);
          setActiveTabId(validActive ? savedActive : restored[0]?.id || null);
        } catch (e) {
          // Invalid JSON — ignore and fall through
        }
        return;
      }

      // Backward compatibility: single-file restore
      const lastFile = sessionStorage.getItem('walkabout_last_file');
      if (lastFile) {
        await selectNote(lastFile);
      }
    })();
  }, []);

  // ── Tab management: selectNote ─────────────────────────────
  const selectNote = async (path) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNote(path);
      const exists = tabsRef.current.some((t) => t.id === path);

      if (!exists) {
        // Track MRU: push currently active tab to front of the order
        if (activeTabId) {
          tabOrderRef.current = [
            activeTabId,
            ...tabOrderRef.current.filter((id) => id !== activeTabId),
          ];
        }
        setTabs((prev) => [
          ...prev,
          {
            id: path,
            path,
            content: data.content,
            dirty: false,
            tabMode: 'edit',
            traceUrl: data.trace_url || null,
            traceData: null,
          },
        ]);
      }
      setActiveTabId(path);
      navigate('?file=' + encodeURIComponent(path), { replace: true });
    } catch (e) {
      setError('Failed to load: ' + path);
    }
    setLoading(false);
  };

  // ── Tab management: handleTabClose ─────────────────────────
  const handleTabClose = (tabId) => {
    // Dispose Monaco model
    const model = modelsRef.current[tabId];
    if (model) {
      model.dispose();
      delete modelsRef.current[tabId];
    }
    delete viewStatesRef.current[tabId];

    setTabs((prev) => prev.filter((t) => t.id !== tabId));

    setActiveTabId((prev) => {
      if (prev !== tabId) return prev; // Closing a non-active tab

      // Find the MRU tab (most recently used before this one)
      const order = tabOrderRef.current.filter((id) => id !== tabId);
      return order.length > 0 ? order[0] : null;
    });
  };

  // ── Content change ─────────────────────────────────────────
  const handleContentChange = (value) => {
    setTabs((prev) =>
      prev.map((t) =>
        t.id === activeTabId ? { ...t, content: value, dirty: true } : t,
      ),
    );
  };

  // ── Save ───────────────────────────────────────────────────
  const handleSave = async () => {
    if (!activeTabId) return;
    setSaving(true);
    setError(null);
    try {
      await saveNote(activeTabId, content);
      setTabs((prev) =>
        prev.map((t) =>
          t.id === activeTabId ? { ...t, dirty: false } : t,
        ),
      );
      await refreshFiles();
    } catch (e) {
      setError('Save failed');
    }
    setSaving(false);
  };

  // ── Run ────────────────────────────────────────────────────
  const handleRun = async () => {
    if (!activeTabId) return;
    setExecuting(true);
    setError(null);
    setExecResult(null);
    try {
      if (dirty) {
        await saveNote(activeTabId, content);
        setTabs((prev) =>
          prev.map((t) =>
            t.id === activeTabId ? { ...t, dirty: false } : t,
          ),
        );
      }
      const result = await executeNote(activeTabId);
      setExecResult(result);
      if (result.status === 'ok') {
        setTabs((prev) =>
          prev.map((t) =>
            t.id === activeTabId
              ? { ...t, traceUrl: result.trace_url, tabMode: 'view' }
              : t,
          ),
        );
        navigate('?trace=' + encodeURIComponent(result.trace_url));
      }
    } catch (e) {
      setError('Execution failed');
    }
    setExecuting(false);
  };

  // ── Export ─────────────────────────────────────────────────
  const handleExport = async () => {
    if (!activeTabId) return;
    setExporting(true);
    setError(null);
    try {
      if (dirty) {
        await saveNote(activeTabId, content);
        setTabs((prev) =>
          prev.map((t) =>
            t.id === activeTabId ? { ...t, dirty: false } : t,
          ),
        );
      }
      const result = await executeNote(activeTabId);
      if (result.status !== 'ok') {
        throw new Error(result.error || 'Execution failed');
      }
      const saveResult = await saveExport(activeTabId);
      showToast('Exported → ' + saveResult.path);
    } catch (e) {
      setError('Export failed: ' + (e.message || e));
    }
    setExporting(false);
  };

  // ── Install ────────────────────────────────────────────────
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

  // ── New file ───────────────────────────────────────────────
  const handleNew = async (name) => {
    try {
      const data = await createNote(name);
      await refreshFiles();
      selectNote(data.path);
    } catch (e) {
      setError('Failed to create note');
    }
  };

  // ── Delete ─────────────────────────────────────────────────
  const handleDelete = async (path) => {
    try {
      await deleteNote(path);
      // Close the tab if the deleted file was open
      const tabOpen = tabsRef.current.some((t) => t.id === path);
      if (tabOpen) {
        handleTabClose(path);
      }
      await refreshFiles();
    } catch (e) {
      setError('Failed to delete');
    }
  };

  // ── Theme toggle ───────────────────────────────────────────
  const handleToggleTheme = () => {
    const next = toggleTheme();
    setCurrentTheme(next);
    axios.post('/api/config/set', { key: 'appearance.theme', value: next }).catch(() => {});
  };

  // ── Exit zen ───────────────────────────────────────────────
  const exitZen = () => {
    setZenMode(false);
    if (document.fullscreenElement) { document.exitFullscreen(); }
  };

  // ── Monaco model management ──────────────────────────────
  const handleMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    if (activeTabId && monaco) {
      const existing = modelsRef.current[activeTabId];
      if (existing) {
        editor.setModel(existing);
        const vs = viewStatesRef.current[activeTabId];
        if (vs) editor.restoreViewState(vs);
      } else {
        // onMount fires before the active-tab-change effect, so
        // the effect below will create the model and set it.
      }
    }
  };

  // Switch Monaco models when the active tab changes
  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;

    // Save view state for current model
    const currentModel = editor.getModel();
    if (currentModel) {
      for (const [id, model] of Object.entries(modelsRef.current)) {
        if (model === currentModel) {
          viewStatesRef.current[id] = editor.saveViewState();
          break;
        }
      }
    }

    if (activeTabId) {
      let model = modelsRef.current[activeTabId];
      if (!model) {
        const uriStr = 'file:///' + activeTabId.replace(/[^a-zA-Z0-9/_.-]/g, '_');
        model = monaco.editor.createModel(activeTab?.content || '', 'python', monaco.Uri.parse(uriStr));
        modelsRef.current[activeTabId] = model;

        model.onDidChangeContent(() => {
          const newContent = model.getValue();
          setTabs((prev) =>
            prev.map((t) =>
              t.id === activeTabId ? { ...t, content: newContent, dirty: true } : t,
            ),
          );
        });
      }
      editor.setModel(model);

      const vs = viewStatesRef.current[activeTabId];
      if (vs) editor.restoreViewState(vs);
    }
  }, [activeTabId]);

  // ── Keyboard shortcuts ─────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      // Skip when input/textarea is focused
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;

      if (e.ctrlKey && e.shiftKey && e.key === 'Tab') {
        e.preventDefault();
        if (tabs.length < 2) return;
        const idx = tabs.findIndex((t) => t.id === activeTabId);
        const prev = tabs[(idx - 1 + tabs.length) % tabs.length];
        setActiveTabId(prev.id);
      } else if (e.ctrlKey && e.key === 'Tab') {
        e.preventDefault();
        if (tabs.length < 2) return;
        const idx = tabs.findIndex((t) => t.id === activeTabId);
        const next = tabs[(idx + 1) % tabs.length];
        setActiveTabId(next.id);
      } else if (e.ctrlKey && e.key === 'w') {
        e.preventDefault();
        if (activeTabId) handleTabClose(activeTabId);
      } else if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        handleSave();
      } else if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        handleRun();
      } else if (e.key === 'F11') {
        e.preventDefault();
        toggleZen();
      } else if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        const name = window.prompt('New file name:');
        if (name) handleNew(name);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [tabs, activeTabId]);

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className={`editor-page${zenMode ? ' zen-mode' : ''}${!sidebarVisible ? ' sidebar-hidden' : ''}`}>
      <header className="toolbar">
        <span className="logo">Walkabout</span>
        <span className="toolbar-actions">
          {selectedPath && (
            <>
              <button onClick={() => {
                setTabs((prev) =>
                  prev.map((t) =>
                    t.id === activeTabId ? { ...t, tabMode: 'edit' } : t,
                  ),
                );
              }} className={tabMode === 'edit' ? 'tab-active' : ''}>
                ✏️ Edit
              </button>
              {traceUrl && (
                <button onClick={() => {
                  setTabs((prev) =>
                    prev.map((t) =>
                      t.id === activeTabId ? { ...t, tabMode: 'view' } : t,
                    ),
                  );
                  navigate('?trace=' + encodeURIComponent(traceUrl));
                }} className={tabMode === 'view' ? 'tab-active' : ''}>
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
          <TabBar
            tabs={tabs}
            activeTabId={activeTabId}
            onSelect={setActiveTabId}
            onClose={handleTabClose}
          />
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
          ) : activeTab?.tabMode === 'view' && activeTab?.traceUrl ? (
            <div className="viewer-embed" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1, overflow: 'auto' }}>
                <TraceViewer />
              </div>
              {selectedPath && activeTab?.traceData?.files?.[selectedPath] && (
                <div style={{ height: '35%', minHeight: 200, borderTop: '1px solid var(--border-glass)' }}>
                  <Editor
                    content={activeTab.traceData.files[selectedPath]}
                    onChange={() => {}}
                    settings={editorSettings}
                    decorations={decorations}
                    onMount={handleMount}
                  />
                </div>
              )}
            </div>
          ) : activeTab ? (
            <Editor
              content={content}
              onChange={handleContentChange}
              settings={editorSettings}
              onMount={handleMount}
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
