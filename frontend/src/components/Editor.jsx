import Monaco from '@monaco-editor/react';

export default function Editor({ content, onChange }) {
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
