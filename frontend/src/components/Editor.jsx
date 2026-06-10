import { useState, useEffect, useRef } from 'react';

function getEditorTheme() {
  const theme = document.documentElement.getAttribute('data-theme');
  return theme === 'light' ? 'vs' : 'vs-dark';
}

export default function Editor({ content, onChange, settings, decorations, onMount }) {
  const [Monaco, setMonaco] = useState(null);
  const [editorTheme, setEditorTheme] = useState(getEditorTheme());
  const fontSize = settings?.fontSize ?? 14;

  // Editor instance refs for inline decorations
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const decorationIdsRef = useRef([]);

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

  // Apply / update inline decorations whenever the `decorations` prop changes
  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;

    const newDecorations = (decorations || []).map((d) => ({
      range: new monaco.Range(d.line, 1, d.line, 1),
      options: {
        isWholeLine: true,
        after: {
          content: '  ' + d.text,
          inlineClassName: 'inline-var',
        },
      },
    }));

    decorationIdsRef.current = editor.deltaDecorations(
      decorationIdsRef.current,
      newDecorations,
    );
  }, [decorations]);

  function handleMount(editor, monaco) {
    editorRef.current = editor;
    monacoRef.current = monaco;
    if (onMount) onMount(editor);
  }

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
        onMount={handleMount}
        options={{
          fontSize,
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
