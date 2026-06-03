import { useState, useMemo } from 'react';

function FileItem({ f, selectedPath, onSelect, onDelete }) {
  return (
    <li
      key={f.path}
      className={selectedPath === f.path ? 'selected' : ''}
      onClick={() => onSelect(f.path)}
    >
      <span className="file-icon">📄</span>
      <span className="file-name">{f.name}</span>
      <button
        className="delete-btn"
        onClick={(e) => { e.stopPropagation(); if (confirm('Delete ' + f.name + '?')) onDelete(f.path); }}
        title="Delete"
      >×</button>
    </li>
  );
}

function FolderGroup({ folderName, children, defaultOpen }) {
  const [collapsed, setCollapsed] = useState(!defaultOpen);
  return (
    <li className="folder-group">
      <span className="folder-toggle" onClick={() => setCollapsed(!collapsed)}>
        <span className="folder-icon">{collapsed ? '📁' : '📂'}</span>
        <span className="folder-name">{folderName}</span>
        <span className="folder-chevron">{collapsed ? '▶' : '▼'}</span>
      </span>
      {!collapsed && <ul className="folder-children">{children}</ul>}
    </li>
  );
}

export default function FileBrowser({ files, selectedPath, onSelect, onNew, onDelete }) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');

  const handleCreate = () => {
    if (newName.trim()) {
      onNew(newName.trim());
      setNewName('');
      setCreating(false);
    }
  };

  // Group files by their first directory component
  const { rootFiles, folders } = useMemo(() => {
    const root = [];
    const folderMap = {};
    for (const f of files) {
      const slashIdx = f.name.indexOf('/');
      if (slashIdx === -1) {
        root.push(f);
      } else {
        const folder = f.name.substring(0, slashIdx);
        const rest = f.name.substring(slashIdx + 1);
        if (!folderMap[folder]) folderMap[folder] = [];
        folderMap[folder].push({ ...f, displayName: rest });
      }
    }
    return { rootFiles: root, folders: folderMap };
  }, [files]);

  return (
    <aside className="file-browser">
      <div className="file-browser-header">
        <h3>Notes</h3>
        <button onClick={() => setCreating(true)} className="new-btn">+</button>
      </div>
      {creating && (
        <div className="new-file-input">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
              if (e.key === 'Escape') { setCreating(false); setNewName(''); }
            }}
            placeholder="filename.py or path/name.py"
          />
          <button onClick={handleCreate}>OK</button>
        </div>
      )}
      <ul className="file-list">
        {rootFiles.map((f) => (
          <FileItem key={f.path} f={f} selectedPath={selectedPath} onSelect={onSelect} onDelete={onDelete} />
        ))}
        {Object.entries(folders).sort(([a], [b]) => a.localeCompare(b)).map(([folderName, children]) => (
          <FolderGroup key={folderName} folderName={folderName} defaultOpen={true}>
            {children.sort((a, b) => a.displayName.localeCompare(b.displayName)).map((f) => (
              <FileItem key={f.path} f={{ ...f, name: f.displayName }} selectedPath={selectedPath} onSelect={onSelect} onDelete={onDelete} />
            ))}
          </FolderGroup>
        ))}
      </ul>
    </aside>
  );
}
