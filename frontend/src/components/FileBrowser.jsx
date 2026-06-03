import { useState } from 'react';

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
            placeholder="filename.py"
          />
          <button onClick={handleCreate}>OK</button>
        </div>
      )}
      <ul className="file-list">
        {files.map((f) => (
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
        ))}
      </ul>
    </aside>
  );
}
