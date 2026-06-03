import { useState, useEffect } from 'react';
import axios from 'axios';

export default function SettingsPage() {
  const [schema, setSchema] = useState([]);
  const [settings, setSettings] = useState({});
  const [defaults, setDefaults] = useState({});
  const [search, setSearch] = useState('');
  const [mode, setMode] = useState('gui'); // 'gui' | 'json'
  const [jsonText, setJsonText] = useState('');
  const [jsonError, setJsonError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      axios.get('/api/config/schema').then(r => r.data),
      axios.get('/api/config').then(r => r.data),
      axios.get('/api/config/defaults').then(r => r.data),
    ]).then(([s, cfg, def]) => {
      setSchema(s);
      setSettings(cfg);
      setDefaults(def);
      setJsonText(JSON.stringify(cfg, null, 2));
    });
  }, []);

  const setValue = async (key, value) => {
    setSaving(true);
    try {
      await axios.post('/api/config/set', { key, value });
      const res = await axios.get('/api/config');
      setSettings(res.data);
      setJsonText(JSON.stringify(res.data, null, 2));
    } catch (e) {
      console.error(e);
    }
    setSaving(false);
  };

  const saveJson = async () => {
    try {
      const parsed = JSON.parse(jsonText);
      await axios.post('/api/config', { settings: parsed });
      setSettings(parsed);
      setJsonError(null);
    } catch (e) {
      setJsonError(e.message);
    }
  };

  const resetAll = async () => {
    await axios.post('/api/config/reset');
    const res = await axios.get('/api/config');
    setSettings(res.data);
    setJsonText(JSON.stringify(res.data, null, 2));
  };

  // Group by category
  const categories = {};
  schema.forEach(item => {
    const cat = item.category || 'General';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(item);
  });

  // Filter by search
  const filter = (item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return item.key.toLowerCase().includes(q) ||
           item.description.toLowerCase().includes(q) ||
           (item.category || '').toLowerCase().includes(q);
  };

  const getValue = (key) => {
    const parts = key.split('.');
    let v = settings;
    for (const p of parts) {
      if (v && typeof v === 'object') v = v[p];
      else return undefined;
    }
    return v;
  };

  const renderControl = (item) => {
    const val = getValue(item.key);
    const def = (() => { const p = item.key.split('.'); let d = defaults; for (const k of p) d = d?.[k]; return d; })();
    const isModified = JSON.stringify(val) !== JSON.stringify(def);

    if (item.type === 'boolean') {
      return (
        <label className="setting-toggle">
          <input type="checkbox" checked={!!val} onChange={e => setValue(item.key, e.target.checked)} />
          <span className="toggle-slider" />
        </label>
      );
    }
    if (item.enum) {
      return (
        <select value={val ?? ''} onChange={e => setValue(item.key, e.target.value)} className="setting-select">
          {item.enum.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      );
    }
    if (item.type === 'integer' || item.type === 'number') {
      return (
        <input type="number" value={val ?? ''} onChange={e => setValue(item.key, parseInt(e.target.value) || 0)}
          className="setting-number" />
      );
    }
    return (
      <input type="text" value={val ?? ''} onChange={e => setValue(item.key, e.target.value)}
        className="setting-text" />
    );
  };

  return (
    <div className="settings-page">
      <header className="toolbar">
        <span className="logo">⚙ Settings</span>
        <span className="toolbar-actions">
          <button onClick={() => setMode('gui')} className={mode === 'gui' ? 'tab-active' : ''}>
            🖱 GUI
          </button>
          <button onClick={() => setMode('json')} className={mode === 'json' ? 'tab-active' : ''}>
            {'{ }'} JSON
          </button>
          <button onClick={resetAll} className="reset-btn">↺ Reset</button>
        </span>
      </header>

      {mode === 'gui' ? (
        <div className="settings-gui">
          <div className="settings-search">
            <input placeholder="Search settings..." value={search}
              onChange={e => setSearch(e.target.value)} />
          </div>
          <div className="settings-list">
            {Object.entries(categories).map(([cat, items]) => {
              const filtered = items.filter(filter);
              if (!filtered.length) return null;
              return (
                <div key={cat} className="settings-category">
                  <h3 className="category-title">{cat}</h3>
                  {filtered.map(item => {
                    const val = getValue(item.key);
                    const def = (() => { const p = item.key.split('.'); let d = defaults; for (const k of p) d = d?.[k]; return d; })();
                    const isModified = JSON.stringify(val) !== JSON.stringify(def);
                    return (
                      <div key={item.key} className="setting-item">
                        <div className="setting-info">
                          <div className="setting-key">
                            {item.key}
                            {isModified && <span className="modified-dot" title="Modified from default" />}
                          </div>
                          <div className="setting-desc">{item.description}</div>
                          {def !== undefined && <div className="setting-default">Default: {JSON.stringify(def)}</div>}
                        </div>
                        <div className="setting-control">
                          {renderControl(item)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="settings-json">
          <textarea value={jsonText} onChange={e => { setJsonText(e.target.value); setJsonError(null); }}
            spellCheck={false} />
          {jsonError && <div className="json-error">Error: {jsonError}</div>}
          <button onClick={saveJson} className="save-json-btn">Apply</button>
        </div>
      )}
    </div>
  );
}
