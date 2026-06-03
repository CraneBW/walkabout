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

function FolderGroup({ folderName, children, onNew }) {
  const [collapsed, setCollapsed] = useState(false);
  const [showNewInput, setShowNewInput] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  const handleCreateFile = () => {
    if (newFileName.trim()) {
      onNew(folderName + '/' + newFileName.trim());
      setNewFileName('');
      setShowNewInput(false);
    }
  };

  return (
    <li className="folder-group">
      <span className="folder-toggle" onClick={() => setCollapsed(!collapsed)}>
        <span className="folder-icon">{collapsed ? '📁' : '📂'}</span>
        <span className="folder-name">{folderName}</span>
        <span className="folder-actions">
          <button
            className="folder-add-btn"
            onClick={(e) => { e.stopPropagation(); setShowNewInput(!showNewInput); setCollapsed(false); }}
            title="New file in folder"
          >+</button>
          <span className="folder-chevron">{collapsed ? '▶' : '▼'}</span>
        </span>
      </span>
      {showNewInput && (
        <div className="new-file-input" onClick={(e) => e.stopPropagation()}>
          <input
            autoFocus
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateFile();
              if (e.key === 'Escape') { setShowNewInput(false); setNewFileName(''); }
            }}
            placeholder="filename.py"
          />
          <button onClick={handleCreateFile}>OK</button>
        </div>
      )}
      {!collapsed && <ul className="folder-children">{children}</ul>}
    </li>
  );
}

export default function FileBrowser({ files, selectedPath, onSelect, onNew, onDelete }) {
  const [creating, setCreating] = useState(false);
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newName, setNewName] = useState('');
  const [folderName, setFolderName] = useState('');

  const handleCreate = () => {
    if (newName.trim()) {
      onNew(newName.trim());
      setNewName('');
      setCreating(false);
    }
  };

  const handleCreateFolder = () => {
    if (folderName.trim()) {
      onNew(folderName.trim() + '/__init__.py');
      setFolderName('');
      setCreatingFolder(false);
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
        <div className="file-browser-actions">
          <button onClick={() => setCreatingFolder(true)} className="new-folder-btn" title="New folder">📁</button>
          <button onClick={() => setCreating(true)} className="new-btn" title="New file">+</button>
        </div>
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
      {creatingFolder && (
        <div className="new-file-input">
          <input
            autoFocus
            value={folderName}
            onChange={(e) => setFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateFolder();
              if (e.key === 'Escape') { setCreatingFolder(false); setFolderName(''); }
            }}
            placeholder="folder_name"
          />
          <button onClick={handleCreateFolder}>OK</button>
        </div>
      )}
      <ul className="file-list">
        {rootFiles.map((f) => (
          <FileItem key={f.path} f={f} selectedPath={selectedPath} onSelect={onSelect} onDelete={onDelete} />
        ))}
        {Object.entries(folders).sort(([a], [b]) => a.localeCompare(b)).map(([folderName, children]) => (
          <FolderGroup key={folderName} folderName={folderName} defaultOpen={true} onNew={onNew}>
            {children.sort((a, b) => a.displayName.localeCompare(b.displayName)).map((f) => (
              <FileItem key={f.path} f={{ ...f, name: f.displayName }} selectedPath={selectedPath} onSelect={onSelect} onDelete={onDelete} />
            ))}
          </FolderGroup>
        ))}
      </ul>
    </aside>
  );
}
