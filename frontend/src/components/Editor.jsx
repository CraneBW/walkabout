import { useState, useEffect, useRef } from 'react';

export default function Editor({ content, onChange }) {
  const [Monaco, setMonaco] = useState(null);

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

  if (!Monaco) {
    return (
      <div className="editor-container editor-loading">
        <div className="loading-spinner" />
        <span>Preparing editor...</span>
      </div>
    );
  }

  return (
    <div className="editor-container">
      <Monaco
        height="100%"
        language="python"
        theme="vs-dark"
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
