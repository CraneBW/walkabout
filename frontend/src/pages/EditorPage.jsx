import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import FileBrowser from '../components/FileBrowser';
import Editor from '../components/Editor';
import TraceViewer from '../TraceViewer';
import { listNotes, getNote, saveNote, createNote, deleteNote, executeNote } from '../api';
import { getEnvInfo, installPackages } from '../api';

export default function EditorPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [selectedPath, setSelectedPath] = useState(null);
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // Embedded viewer tab
  const [tab, setTab] = useState('edit'); // 'edit' | 'view'
  const [traceUrl, setTraceUrl] = useState(null);

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
      navigate('');
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
        navigate('');
      }
      await refreshFiles();
    } catch (e) {
      setError('Failed to delete');
    }
  };

  return (
    <div className="editor-page">
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
              <a href="/settings" title="Settings" className="gear-link">⚙</a>
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
          {execResult && execResult.status === 'error' && (
            <div className="exec-error">
              <strong>Execution Error:</strong>
              <pre>{execResult.error}</pre>
            </div>
          )}
          {loading ? (
            <div className="loading">Loading...</div>
          ) : tab === 'view' && traceUrl ? (
            <div className="viewer-embed">
              <TraceViewer />
            </div>
          ) : selectedPath ? (
            <Editor
              content={content}
              onChange={(v) => { setContent(v); setDirty(true); }}
            />
          ) : (
            <div className="welcome">
              <h2>Walkabout</h2>
              <p>Select a note from the sidebar or create a new one.</p>
              <p className="welcome-hint">📦 Click the package icon to install Python dependencies via uv.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
