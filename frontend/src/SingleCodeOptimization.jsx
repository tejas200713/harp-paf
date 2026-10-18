
import React, { useState } from 'react';
import { analyzeSingleCode } from './services/api.js';

export default function SingleCodeOptimization() {
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('input.cpp');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const analyze = async () => {
    setError('');
    setResult(null);

    if (!code.trim()) {
      setError('Please enter or upload C++ code.');
      return;
    }

    setLoading(true);

    try {
      const file = new File(
        [code],
        filename.endsWith('.cpp') ? filename : 'input.cpp',
        { type: 'text/plain' }
      );

      const response = await analyzeSingleCode(file);
      setResult(response);
    } catch (err) {
      setError(err.message || 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError('');
    setResult(null);

    if (!file.name.toLowerCase().endsWith('.cpp')) {
      setError('Please choose a .cpp file.');
      return;
    }

    if (file.size > 100 * 1024) {
      setError('Maximum file size is 100 KB.');
      return;
    }

    setFilename(file.name);
    setCode(await file.text());
    event.target.value = '';
  };

  const downloadFile = (file) => {
    const blob = new Blob([file.code], {
      type: 'text/plain'
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = file.filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const benchmark = result?.benchmark;

  return (
    <div style={{
      padding: 28,
      maxWidth: 1100,
      margin: '0 auto',
      color: '#e2e8f0'
    }}>
      <h1>Single Code Optimization</h1>
      <p>
        Convert one C++ program into multiple source files,
        compile them in parallel, and compare compilation times.
      </p>

      <div style={{
        background: '#172235',
        padding: 20,
        borderRadius: 12,
        marginTop: 24
      }}>
        <h2>Enter C++ Code</h2>

        <input
          type="file"
          accept=".cpp"
          onChange={handleFile}
          style={{ marginBottom: 16 }}
        />

        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          placeholder="Paste your C++ code here..."
          style={{
            width: '100%',
            minHeight: 300,
            boxSizing: 'border-box',
            background: '#0b1220',
            color: '#e2e8f0',
            padding: 16,
            borderRadius: 8,
            border: '1px solid #334155',
            fontFamily: 'Consolas, monospace',
            fontSize: 13
          }}
        />

        <button
          onClick={analyze}
          disabled={loading}
          style={{
            marginTop: 16,
            padding: '12px 24px',
            background: '#0d9488',
            color: 'white',
            border: 0,
            borderRadius: 8,
            cursor: loading ? 'wait' : 'pointer'
          }}
        >
          {loading ? 'Analyzing...' : 'Split & Compare'}
        </button>

        {error && (
          <p role="alert" style={{ color: '#f87171' }}>
            {error}
          </p>
        )}
      </div>

      {benchmark && (
        <div style={{
          background: '#172235',
          padding: 20,
          borderRadius: 12,
          marginTop: 24
        }}>
          <h2>Compilation Results</h2>

          <p>
            Original compilation:
            {' '}{benchmark.originalCompileSeconds} seconds
          </p>

          <p>
            Split compilation:
            {' '}{benchmark.splitCompileSeconds} seconds
          </p>

          <p>
            Speedup: <strong>{benchmark.speedup}x</strong>
          </p>

          <p>
            Generated C++ files:
            {' '}{benchmark.generatedSourceCount}
          </p>

          <p>
            Output verification:
            {' '}
            <strong style={{
              color: benchmark.outputVerified
                ? '#4ade80'
                : '#f87171'
            }}>
              {benchmark.outputVerified ? 'PASSED' : 'FAILED'}
            </strong>
          </p>

          <p style={{ color: '#94a3b8' }}>
            These timings are from one benchmark run.
            Repeat measurements are needed to establish
            a reliable speedup.
          </p>

          <div style={{
            marginTop: 24,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 16
          }}>
            <div>
              <h3>Original Program Output</h3>
              <pre style={{
                background: '#0b1220',
                color: '#e2e8f0',
                padding: 16,
                borderRadius: 8,
                whiteSpace: 'pre-wrap',
                overflowWrap: 'anywhere',
                minHeight: 70
              }}>
                {benchmark.originalOutput ?? 'Output not available.'}
              </pre>
            </div>

            <div>
              <h3>Split Program Output</h3>
              <pre style={{
                background: '#0b1220',
                color: '#e2e8f0',
                padding: 16,
                borderRadius: 8,
                whiteSpace: 'pre-wrap',
                overflowWrap: 'anywhere',
                minHeight: 70
              }}>
                {benchmark.splitOutput ?? 'Output not available.'}
              </pre>
            </div>
          </div>
        </div>
      )}

      {result?.generatedFiles && (
        <div style={{ marginTop: 24 }}>
          <h2>Generated Source Files</h2>

          {result.generatedFiles.map((file) => (
            <div key={file.filename} style={{
              background: '#172235',
              padding: 20,
              borderRadius: 12,
              marginBottom: 16
            }}>
              <h3>{file.filename}</h3>

              <button onClick={() => downloadFile(file)}>
                Download File
              </button>

              <pre style={{
                background: '#0b1220',
                padding: 16,
                borderRadius: 8,
                overflowX: 'auto',
                whiteSpace: 'pre-wrap',
                overflowWrap: 'anywhere',
                fontSize: 12
              }}>
                {file.code}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
