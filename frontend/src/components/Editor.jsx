import Monaco, { loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor';

// Use local monaco-editor bundle instead of CDN
// This eliminates ~30MB download on every file open
loader.config({ monaco });

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
