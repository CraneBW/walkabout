import { useState, useEffect, useRef } from 'react';

function getEditorTheme() {
  const theme = document.documentElement.getAttribute('data-theme');
  return theme === 'light' ? 'vs' : 'vs-dark';
}

export default function Editor({ content, onChange }) {
  const [Monaco, setMonaco] = useState(null);
  const [editorTheme, setEditorTheme] = useState(getEditorTheme());

  // Dynamically import monaco-editor to code-split ~5MB from the main chunk,
  // then configure @monaco-editor/react to use the local bundle instead of CDN
  const configured = useRef(false);

  useEffect(() => {
    if (configured.current) return;
    configured.current = true;

    // Dynamic import: Vite code-splits monaco-editor into a separate chunk (~5MB),
    // keeping the main bundle small (~1.3MB) for fast initial render
    Promise.all([
      import('monaco-editor'),
      import('@monaco-editor/react'),
    ]).then(([monaco, reactMonaco]) => {
      reactMonaco.loader.config({ monaco });
      setMonaco(() => reactMonaco.default);
    });
  }, []);

  // Listen for theme changes
  useEffect(() => {
    const observer = new MutationObserver(() => {
      setEditorTheme(getEditorTheme());
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  if (!Monaco) {
    return (
      <div className="editor-container editor-loading">
        <span>Preparing editor...</span>
      </div>
    );
  }

  return (
    <div className="editor-container">
      <Monaco
        height="100%"
        language="python"
        theme={editorTheme}
        value={content}
        onChange={(v) => onChange(v || '')}
        options={{
          fontSize: 14,
          lineNumbers: 'on',
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          tabSize: 4,
        }}
      />
    </div>
  );
}
