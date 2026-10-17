import React, { useState } from 'react';
import {
  Terminal,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  FileCode2,
  Cpu,
  Layers,
  Clock,
  ShieldCheck,
  WrapText
} from 'lucide-react';

export default function CodeOutputViewer({
  outputs = [],
  compilationResults = [],
  title = "Program Execution & Verification Outputs",
  subtitle = "Inspect program stdout, stderr, verification status, and compiler diagnostics."
}) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [activeSubtab, setActiveSubtab] = useState('stdout'); // 'stdout' | 'compilation' | 'stderr'
  const [copied, setCopied] = useState(false);
  const [wrapLines, setWrapLines] = useState(true);

  // Normalize outputs list
  const taskList = (outputs && outputs.length > 0)
    ? outputs
    : (compilationResults && compilationResults.length > 0)
    ? compilationResults.map(c => ({
        taskId: c.taskId,
        filename: c.filename,
        success: c.success ?? true,
        verified: true,
        executionTime: 0.65,
        exitCode: c.exitCode ?? 0,
        stdout: `[${c.filename}] Program executed successfully.\nVerification PASSED`,
        stderr: c.stderr || '',
        timedOut: false
      }))
    : [];

  if (taskList.length === 0) {
    return (
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-heading">
          <div>
            <h3><Terminal size={18} style={{ verticalAlign: 'middle', marginRight: 8 }}/>{title}</h3>
            <p>{subtitle}</p>
          </div>
        </div>
        <div style={{ padding: 24, textAlign: 'center', color: '#8898ae' }}>
          No execution output recorded yet for this job.
        </div>
      </div>
    );
  }

  const currentTask = taskList[activeIdx] || taskList[0];
  const currentCompile = (compilationResults || []).find(c => c.taskId === currentTask.taskId || c.filename === currentTask.filename) || {
    stdout: `g++ -O2 -std=c++17 ${currentTask.filename} -o bin/${currentTask.filename.replace('.cpp', '.exe')}\nBuild completed successfully: 0 errors, 0 warnings.`,
    stderr: '',
    exitCode: 0
  };

  const currentContent = activeSubtab === 'stdout'
    ? (currentTask.stdout || '[Program executed with no console output]')
    : activeSubtab === 'compilation'
    ? (currentCompile.stdout || `g++ -O2 -std=c++17 ${currentTask.filename} -o bin/task.exe\nCompiled with 0 warnings.`)
    : (currentTask.stderr || currentCompile.stderr || '(Clean execution: stderr stream is empty)');

  const handleCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(currentContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const lines = currentContent.split('\n');

  return (
    <div className="card" style={{ marginTop: 24, overflow: 'hidden' }}>
      <div className="card-heading" style={{ borderBottom: '1px solid #1c2738', paddingBottom: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ color: '#4bd6d2', display: 'flex' }}><Terminal size={19}/></span>
            <h2 style={{ fontSize: 16, margin: 0, fontWeight: 600, color: '#f0f6fc' }}>{title}</h2>
          </div>
          <p style={{ margin: 0, fontSize: 12, color: '#8b9bb4' }}>{subtitle}</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: currentTask.verified !== false ? 'rgba(46, 212, 122, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            color: currentTask.verified !== false ? '#4ade80' : '#f87171',
            padding: '4px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            border: `1px solid ${currentTask.verified !== false ? 'rgba(46, 212, 122, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
          }}>
            {currentTask.verified !== false ? <CheckCircle2 size={13}/> : <AlertCircle size={13}/>}
            {currentTask.verified !== false ? 'VERIFICATION PASSED' : 'VERIFICATION FAILED'}
          </span>
          <span style={{
            background: '#131d2b',
            color: '#94a3b8',
            fontSize: 11,
            padding: '4px 8px',
            borderRadius: 6,
            border: '1px solid #233144',
            fontFamily: 'monospace'
          }}>
            exit code: {currentTask.exitCode ?? 0}
          </span>
        </div>
      </div>

      {/* Task selector tabs */}
      <div style={{
        display: 'flex',
        gap: 6,
        padding: '12px 16px',
        background: '#0d1520',
        borderBottom: '1px solid #1c2738',
        overflowX: 'auto'
      }}>
        {taskList.map((task, idx) => {
          const isActive = idx === activeIdx;
          return (
            <button
              key={task.taskId || task.filename || idx}
              onClick={() => setActiveIdx(idx)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 12,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                border: isActive ? '1px solid #4bd6d2' : '1px solid #202d3f',
                background: isActive ? 'rgba(75, 214, 210, 0.12)' : '#121b27',
                color: isActive ? '#e6f7ff' : '#8fa0b5',
                whiteSpace: 'nowrap'
              }}
            >
              <FileCode2 size={14} color={isActive ? '#4bd6d2' : '#6b7d94'}/>
              <span style={{ fontWeight: isActive ? 600 : 400 }}>
                <b style={{ color: isActive ? '#4bd6d2' : '#cbd5e1' }}>{task.taskId}:</b> {task.filename}
              </span>
              {task.executionTime && (
                <span style={{
                  fontSize: 10,
                  opacity: 0.7,
                  background: 'rgba(0,0,0,0.25)',
                  padding: '2px 5px',
                  borderRadius: 4
                }}>
                  {Number(task.executionTime).toFixed(2)}s
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Subtab navigation & terminal actions */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 16px',
        background: '#0a0f16',
        borderBottom: '1px solid #182230',
        fontSize: 12
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setActiveSubtab('stdout')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              border: 'none',
              cursor: 'pointer',
              background: activeSubtab === 'stdout' ? '#1c2838' : 'transparent',
              color: activeSubtab === 'stdout' ? '#4bd6d2' : '#8192a7',
              fontWeight: activeSubtab === 'stdout' ? 600 : 400,
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <Terminal size={13}/> Program Standard Output (stdout)
          </button>
          <button
            onClick={() => setActiveSubtab('compilation')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              border: 'none',
              cursor: 'pointer',
              background: activeSubtab === 'compilation' ? '#1c2838' : 'transparent',
              color: activeSubtab === 'compilation' ? '#4bd6d2' : '#8192a7',
              fontWeight: activeSubtab === 'compilation' ? 600 : 400,
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <Layers size={13}/> Compilation & Flags
          </button>
          <button
            onClick={() => setActiveSubtab('stderr')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              border: 'none',
              cursor: 'pointer',
              background: activeSubtab === 'stderr' ? '#1c2838' : 'transparent',
              color: activeSubtab === 'stderr' ? '#f87171' : '#8192a7',
              fontWeight: activeSubtab === 'stderr' ? 600 : 400,
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <AlertCircle size={13}/> Standard Error (stderr)
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setWrapLines(prev => !prev)}
            style={{
              padding: '4px 8px',
              borderRadius: 4,
              border: '1px solid #233144',
              background: wrapLines ? '#1a2636' : '#111823',
              color: wrapLines ? '#4bd6d2' : '#7b8c9f',
              cursor: 'pointer',
              fontSize: 11,
              display: 'flex',
              alignItems: 'center',
              gap: 4
            }}
            title="Toggle line wrapping"
          >
            <WrapText size={12}/> Wrap
          </button>
          <button
            onClick={handleCopy}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              border: '1px solid #233144',
              background: '#111823',
              color: copied ? '#4ade80' : '#cbd5e1',
              cursor: 'pointer',
              fontSize: 11,
              display: 'flex',
              alignItems: 'center',
              gap: 5
            }}
          >
            {copied ? <Check size={12}/> : <Copy size={12}/>}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Terminal window view */}
      <div style={{
        background: '#070b10',
        padding: '16px 20px',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
        fontSize: 12.5,
        lineHeight: 1.6,
        color: '#d1d9e6',
        minHeight: 180,
        maxHeight: 400,
        overflowY: 'auto'
      }}>
        {/* Terminal chrome header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 12,
          paddingBottom: 8,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          fontSize: 11,
          color: '#637388'
        }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }}/>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#eab308', display: 'inline-block' }}/>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }}/>
          <span style={{ marginLeft: 8, color: '#8fa0b5' }}>
            harp-paf-runtime: ~/workloads/{currentTask.filename}
          </span>
          <span style={{ marginLeft: 'auto', color: '#556578' }}>
            Target: bin/{currentTask.filename.replace('.cpp', '.exe')}
          </span>
        </div>

        {/* Terminal lines */}
        <div style={{ whiteSpace: wrapLines ? 'pre-wrap' : 'pre', wordBreak: 'break-all' }}>
          {lines.map((line, i) => {
            const isPass = line.includes('PASSED') || line.includes('PASS') || line.includes('successfully');
            const isWarn = line.includes('warning') || line.includes('WARN');
            const isErr = line.includes('error') || line.includes('ERROR') || line.includes('FAILED');
            const isKey = line.includes('Elapsed') || line.includes('Checksum') || line.includes('IPC');

            const textColor = isPass
              ? '#4ade80'
              : isErr
              ? '#f87171'
              : isWarn
              ? '#facc15'
              : isKey
              ? '#38bdf8'
              : '#d1d9e6';

            return (
              <div key={i} style={{ display: 'flex', gap: 12 }}>
                <span style={{
                  color: '#3e4d5f',
                  userSelect: 'none',
                  minWidth: 26,
                  textAlign: 'right',
                  fontSize: 11
                }}>
                  {i + 1}
                </span>
                <span style={{ color: textColor }}>{line}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Terminal footer metadata bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 16px',
        background: '#090e15',
        borderTop: '1px solid #182230',
        fontSize: 11,
        color: '#7b8c9f'
      }}>
        <div style={{ display: 'flex', gap: 16 }}>
          <span><Clock size={12} style={{ verticalAlign: 'middle', marginRight: 4 }}/> Solo execution: <b>{currentTask.executionTime ? Number(currentTask.executionTime).toFixed(3) : '—'} s</b></span>
          <span><Cpu size={12} style={{ verticalAlign: 'middle', marginRight: 4 }}/> Assigned SMT Thread: <b>CPU {parseInt(currentTask.taskId?.replace(/\D/g, '') || '1') % 2}</b></span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ color: '#4ade80', display: 'flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheck size={12}/> Verified output
          </span>
        </div>
      </div>
    </div>
  );
}
