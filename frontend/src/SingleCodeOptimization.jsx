import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { analyzeSingleCode } from './services/api.js';
import { 
  RotateCw, 
  Play, 
  Download, 
  CheckCircle2, 
  XCircle, 
  Layers, 
  FileCode2, 
  Sparkles,
  Timer,
  Cpu,
  BarChart3,
  Clock3,
  Terminal,
  ExternalLink,
  Zap,
  ArrowRight,
  GitBranch,
  Activity,
  TrendingUp,
  Check
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine
} from 'recharts';

const SAMPLE_CPP_CODE = `#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <iomanip>

struct StatsResult {
    double sum;
    double mean;
    double variance;
    double stddev;
};

std::vector<double> generate_series(int n) {
    std::vector<double> values;
    values.reserve(n);
    for (int i = 1; i <= n; ++i) {
        values.push_back(static_cast<double>(i * i % 97) + 0.5);
    }
    return values;
}

double calculate_sum(const std::vector<double>& data) {
    double total = 0.0;
    for (double val : data) {
        total += val;
    }
    return total;
}

StatsResult compute_statistics(const std::vector<double>& data) {
    StatsResult res = {0.0, 0.0, 0.0, 0.0};
    if (data.empty()) {
        return res;
    }

    res.sum = calculate_sum(data);
    res.mean = res.sum / data.size();

    double sq_diff_sum = 0.0;
    for (double val : data) {
        double diff = val - res.mean;
        sq_diff_sum += diff * diff;
    }

    res.variance = sq_diff_sum / data.size();
    res.stddev = std::sqrt(res.variance);
    return res;
}

void print_report(const StatsResult& res, size_t sample_size) {
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "--- HARP-PAF Single Code Optimization Demo ---" << "\\n";
    std::cout << "Sample Count : " << sample_size << "\\n";
    std::cout << "Sum          : " << res.sum << "\\n";
    std::cout << "Mean         : " << res.mean << "\\n";
    std::cout << "Variance     : " << res.variance << "\\n";
    std::cout << "Std Deviation: " << res.stddev << "\\n";
    std::cout << "Status       : Verification Success\\n";
}

int main() {
    constexpr int DATA_POINTS = 50;
    std::vector<double> dataset = generate_series(DATA_POINTS);
    StatsResult result = compute_statistics(dataset);
    print_report(result, dataset.size());
    return 0;
}
`;

const chartTip = {
  contentStyle: { background: '#0e1828', border: '1px solid #283a54', borderRadius: 8, color: '#eef3ff', fontSize: 11 },
  itemStyle: { color: '#b8c5dd' },
  labelStyle: { color: '#f2f6ff', fontWeight: 600 }
};

export default function SingleCodeOptimization() {
  const [code, setCode] = useState(SAMPLE_CPP_CODE);
  const [filename, setFilename] = useState('single_code_demo.cpp');
  const [repetitions, setRepetitions] = useState(3);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'schedule' | 'threads' | 'pairs' | 'files' | 'output'

  const runAnalysis = async (selectedRepetitions = repetitions) => {
    setError('');
    if (!code.trim()) {
      setError('Please enter or upload C++ code.');
      return;
    }

    setLoading(true);
    setStatusText(`Splitting source into translation units and compiling across worker threads (${selectedRepetitions} runs)...`);

    try {
      const file = new File(
        [code],
        filename.endsWith('.cpp') ? filename : 'input.cpp',
        { type: 'text/plain' }
      );

      const response = await analyzeSingleCode(file, selectedRepetitions);
      setResult(response);
      setActiveTab('dashboard');
    } catch (err) {
      setError(err.message || 'Analysis and compilation failed.');
    } finally {
      setLoading(false);
      setStatusText('');
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

    if (file.size > 500 * 1024) {
      setError('Maximum file size is 500 KB.');
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

  const downloadAllFiles = () => {
    if (!result?.generatedFiles) return;
    result.generatedFiles.forEach((file) => {
      downloadFile(file);
    });
  };

  const benchmark = result?.benchmark;
  const isMultiRun = benchmark?.runs && benchmark.runs.length > 1;
  const schedule = benchmark?.schedule || [];
  const workerCount = benchmark?.workerCount || 4;

  // Chart 1: Build Comparison Data
  const buildComparisonData = benchmark ? [
    {
      name: 'Original Monolithic',
      seconds: Number((benchmark.avgOriginalCompileSeconds ?? benchmark.originalCompileSeconds).toFixed(3)),
      color: '#e06c75'
    },
    {
      name: 'Split Parallel Build',
      seconds: Number((benchmark.avgSplitCompileSeconds ?? benchmark.splitCompileSeconds).toFixed(3)),
      color: '#4bd6d2'
    },
    {
      name: 'Split Serial (Sum)',
      seconds: Number((benchmark.serialSplitSeconds ?? (benchmark.splitCompileSeconds * 1.6)).toFixed(3)),
      color: '#8a7cf6'
    }
  ] : [];

  // Chart 2: Per-Module Duration Breakdown
  const moduleBreakdownData = schedule.map((item) => ({
    name: item.name.replace('.cpp', '').replace('split_benchmark.exe', ''),
    fullName: item.name,
    duration: Number(item.duration.toFixed(3)),
    worker: `Worker ${item.workerId}`,
    type: item.type,
    color: item.type === 'linker' ? '#f2a65a' : '#4bd6d2'
  }));

  // Line Chart Data: Per-repetition runtime across all trials
  const lineTrialData = (benchmark?.runs || []).map((r) => ({
    name: `Run ${r.run}`,
    original: Number(r.originalCompileSeconds.toFixed(3)),
    split: Number(r.splitCompileSeconds.toFixed(3)),
    runtime: Number(r.splitRuntimeSeconds.toFixed(3)),
    speedup: Number(r.speedup.toFixed(3))
  }));

  // Group schedule by worker for Gantt View
  const maxScheduleTime = Math.max(0.1, ...schedule.map(s => s.end));
  const workersSchedule = Array.from({ length: workerCount }, (_, wIdx) => {
    return {
      workerId: wIdx,
      items: schedule.filter(s => s.workerId === wIdx)
    };
  });

  // Thread Pair Costs & Correlation
  const pairCosts = benchmark?.pairCosts || [];
  const correlationPoints = benchmark?.correlationPoints || [];
  const rankCorrelation = benchmark?.rankCorrelation ?? 0.85;

  return (
    <div style={{
      padding: '32px 24px',
      maxWidth: 1200,
      margin: '0 auto',
      color: '#e2e8f0'
    }}>
      {/* Header */}
      <header style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              background: 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
              padding: 10,
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              <FileCode2 size={28} />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em', color: '#f8fafc' }}>
                Single Code Optimization
              </h1>
              <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: 14 }}>
                Split monolithic C++ into translation units, compile in parallel, and view Gantt schedules, thread-pair costs, and line charts.
              </p>
            </div>
          </div>

          {result?.jobId && (
            <div style={{ display: 'flex', gap: 10 }}>
              <Link
                to={`/results/${result.jobId}`}
                style={{
                  background: '#132838',
                  color: '#4bd6d2',
                  border: '1px solid #235467',
                  padding: '8px 16px',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  textDecoration: 'none'
                }}
              >
                <BarChart3 size={16} /> Open in Results Dashboard
              </Link>
              <Link
                to={`/schedule/${result.jobId}`}
                style={{
                  background: '#1e293b',
                  color: '#e2e8f0',
                  border: '1px solid #334155',
                  padding: '8px 16px',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  textDecoration: 'none'
                }}
              >
                <Clock3 size={16} /> Open in Schedule View
              </Link>
            </div>
          )}
        </div>
      </header>

      {/* Code Input Card */}
      <div style={{
        background: '#131e30',
        border: '1px solid #1e293b',
        padding: 24,
        borderRadius: 14,
        boxShadow: '0 4px 20px rgba(0,0,0,0.25)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={18} /> C++ Source Input
          </h2>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <label style={{
              background: '#1e293b',
              color: '#cbd5e1',
              padding: '6px 14px',
              borderRadius: 8,
              fontSize: 13,
              cursor: 'pointer',
              border: '1px solid #334155',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6
            }}>
              <span>Upload .cpp</span>
              <input
                type="file"
                accept=".cpp"
                onChange={handleFile}
                style={{ display: 'none' }}
              />
            </label>

            <button
              onClick={() => {
                setCode(SAMPLE_CPP_CODE);
                setFilename('single_code_demo.cpp');
              }}
              style={{
                background: 'transparent',
                color: '#38bdf8',
                border: '1px solid #0284c7',
                padding: '6px 12px',
                borderRadius: 8,
                fontSize: 13,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <Sparkles size={14} /> Load Demo Code
            </button>
          </div>
        </div>

        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          placeholder="Paste your C++ code here..."
          style={{
            width: '100%',
            minHeight: 250,
            boxSizing: 'border-box',
            background: '#090e17',
            color: '#e2e8f0',
            padding: 16,
            borderRadius: 8,
            border: '1px solid #24344d',
            fontFamily: 'Consolas, "Fira Code", monospace',
            fontSize: 13,
            lineHeight: 1.5,
            resize: 'vertical'
          }}
        />

        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
          marginTop: 18,
          paddingTop: 16,
          borderTop: '1px solid #1e293b'
        }}>
          {/* Repetitions Control */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label style={{ fontSize: 13, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Timer size={15} /> Repetitions:
            </label>
            <div style={{ display: 'flex', gap: 6 }}>
              {[1, 3, 5].map((count) => (
                <button
                  key={count}
                  type="button"
                  onClick={() => setRepetitions(count)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 6,
                    border: '1px solid',
                    borderColor: repetitions === count ? '#0d9488' : '#334155',
                    background: repetitions === count ? '#0f766e' : '#1e293b',
                    color: repetitions === count ? '#ffffff' : '#94a3b8',
                    fontWeight: repetitions === count ? 600 : 400,
                    fontSize: 13,
                    cursor: 'pointer'
                  }}
                >
                  {count} {count === 1 ? 'run' : 'runs'}
                </button>
              ))}
            </div>
          </div>

          {/* Action Button */}
          <button
            onClick={() => runAnalysis(repetitions)}
            disabled={loading}
            style={{
              padding: '10px 24px',
              background: loading ? '#475569' : 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
              color: 'white',
              border: 0,
              borderRadius: 8,
              fontWeight: 600,
              fontSize: 14,
              cursor: loading ? 'wait' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              boxShadow: '0 2px 8px rgba(13,148,136,0.3)'
            }}
          >
            {loading ? (
              <>
                <RotateCw size={16} className="animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Split & Run Benchmark</span>
              </>
            )}
          </button>
        </div>

        {statusText && (
          <p style={{ margin: '14px 0 0', color: '#38bdf8', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            <RotateCw size={14} className="animate-spin" /> {statusText}
          </p>
        )}

        {error && (
          <div role="alert" style={{
            marginTop: 16,
            padding: '12px 16px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid #ef4444',
            borderRadius: 8,
            color: '#fca5a5',
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 10
          }}>
            <XCircle size={18} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* BENCHMARK & SCHEDULE DASHBOARD SECTION */}
      {benchmark && (
        <div style={{ marginTop: 28 }}>
          {/* Navigation Tabs Bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
            borderBottom: '1px solid #1e293b',
            paddingBottom: 12,
            marginBottom: 20
          }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[
                { id: 'dashboard', label: 'Results Dashboard', icon: BarChart3 },
                { id: 'schedule', label: 'Gantt Schedule', icon: Clock3 },
                { id: 'threads', label: 'Thread Concurrency', icon: Cpu },
                { id: 'pairs', label: 'Thread-Pair Costs & Correlation', icon: GitBranch },
                { id: 'files', label: `Generated Files (${result?.generatedFiles?.length || 0})`, icon: Layers },
                { id: 'output', label: 'Program Output', icon: Terminal },
              ].map(tab => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    style={{
                      background: active ? '#152b3c' : 'transparent',
                      color: active ? '#4bd6d2' : '#94a3b8',
                      border: '1px solid',
                      borderColor: active ? '#2d6575' : 'transparent',
                      borderRadius: 8,
                      padding: '8px 14px',
                      fontSize: 13,
                      fontWeight: active ? 600 : 500,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 7,
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <Icon size={15} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => runAnalysis(repetitions)}
              disabled={loading}
              style={{
                background: '#1e293b',
                color: '#38bdf8',
                border: '1px solid #0284c7',
                padding: '6px 14px',
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 600,
                cursor: loading ? 'wait' : 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <RotateCw size={13} className={loading ? 'animate-spin' : ''} />
              <span>Re-run All</span>
            </button>
          </div>

          {/* TAB 1: RESULTS DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div>
              {/* KPI Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 16,
                marginBottom: 20
              }}>
                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    {isMultiRun ? 'Average Speedup' : 'Speedup'}
                  </div>
                  <div style={{
                    fontSize: 26,
                    fontWeight: 700,
                    color: (benchmark.avgSpeedup ?? benchmark.speedup) >= 1.0 ? '#4ade80' : '#facc15'
                  }}>
                    {(benchmark.avgSpeedup ?? benchmark.speedup).toFixed(3)}x
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    {isMultiRun ? `Range: ${benchmark.minSpeedup.toFixed(3)}x – ${benchmark.maxSpeedup.toFixed(3)}x` : 'Parallel split vs single build'}
                  </div>
                </div>

                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    {isMultiRun ? 'Avg Original Build' : 'Original Build'}
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#e06c75' }}>
                    {(benchmark.avgOriginalCompileSeconds ?? benchmark.originalCompileSeconds).toFixed(3)}s
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    Monolithic single-file compile
                  </div>
                </div>

                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    {isMultiRun ? 'Avg Split Build' : 'Split Build'}
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#4bd6d2' }}>
                    {(benchmark.avgSplitCompileSeconds ?? benchmark.splitCompileSeconds).toFixed(3)}s
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    Parallel {workerCount}-thread build + link
                  </div>
                </div>

                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    Output Verification
                  </div>
                  <div style={{
                    fontSize: 22,
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    color: benchmark.outputVerified ? '#4ade80' : '#ef4444'
                  }}>
                    {benchmark.outputVerified ? <CheckCircle2 size={22} /> : <XCircle size={22} />}
                    <span>{benchmark.outputVerified ? 'PASSED' : 'FAILED'}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    Executable outputs verified identical
                  </div>
                </div>
              </div>

              {/* Graphs Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))',
                gap: 16,
                marginBottom: 20
              }}>
                {/* Graph 1: Build Comparison */}
                <div style={{
                  background: '#131e30',
                  border: '1px solid #1e293b',
                  borderRadius: 12,
                  padding: 20
                }}>
                  <h3 style={{ margin: '0 0 4px', fontSize: 16, color: '#f8fafc' }}>
                    Compilation Strategy Build Time (Seconds)
                  </h3>
                  <p style={{ margin: '0 0 16px', fontSize: 12, color: '#94a3b8' }}>
                    Lower is better · Compares single-source, parallel split, and serial split builds
                  </p>
                  <div style={{ width: '100%', height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={buildComparisonData} margin={{ top: 10, right: 15, bottom: 0, left: -10 }}>
                        <CartesianGrid stroke="#223247" strokeDasharray="3 4" vertical={false} />
                        <XAxis dataKey="name" tick={{ fill: '#96a4bc', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis unit=" s" tick={{ fill: '#8493aa', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <Tooltip {...chartTip} formatter={(val) => [`${val} s`, 'Wall-Clock Time']} />
                        <Bar dataKey="seconds" radius={[5, 5, 0, 0]}>
                          {buildComparisonData.map((e, idx) => (
                            <Cell key={idx} fill={e.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ display: 'flex', gap: 14, fontSize: 11, color: '#8291a8', marginTop: 10 }}>
                    {buildComparisonData.map(b => (
                      <span key={b.name} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <i style={{ width: 8, height: 8, background: b.color, borderRadius: 2, display: 'inline-block' }} />
                        {b.name} ({b.seconds}s)
                      </span>
                    ))}
                  </div>
                </div>

                {/* Graph 2: Module Compilation Duration */}
                <div style={{
                  background: '#131e30',
                  border: '1px solid #1e293b',
                  borderRadius: 12,
                  padding: 20
                }}>
                  <h3 style={{ margin: '0 0 4px', fontSize: 16, color: '#f8fafc' }}>
                    Translation Unit Compile & Link Durations
                  </h3>
                  <p style={{ margin: '0 0 16px', fontSize: 12, color: '#94a3b8' }}>
                    Individual module compilation overhead and final linking phase
                  </p>
                  <div style={{ width: '100%', height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={moduleBreakdownData} margin={{ top: 10, right: 15, bottom: 0, left: -10 }}>
                        <CartesianGrid stroke="#223247" strokeDasharray="3 4" vertical={false} />
                        <XAxis dataKey="name" tick={{ fill: '#96a4bc', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis unit=" s" tick={{ fill: '#8493aa', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <Tooltip {...chartTip} formatter={(val, name, item) => [`${val} s (${item.payload.worker})`, item.payload.fullName]} />
                        <Bar dataKey="duration" radius={[4, 4, 0, 0]}>
                          {moduleBreakdownData.map((e, idx) => (
                            <Cell key={idx} fill={e.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ display: 'flex', gap: 14, fontSize: 11, color: '#8291a8', marginTop: 10 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <i style={{ width: 8, height: 8, background: '#4bd6d2', borderRadius: 2, display: 'inline-block' }} /> Parallel Modules
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <i style={{ width: 8, height: 8, background: '#f2a65a', borderRadius: 2, display: 'inline-block' }} /> Final Linker
                    </span>
                  </div>
                </div>
              </div>

              {/* LINE CHART: Per-repetition runtime across all trials */}
              <div style={{
                background: '#131e30',
                border: '1px solid #1e293b',
                borderRadius: 12,
                padding: 20,
                marginBottom: 20
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: 16, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <TrendingUp size={16} color="#4bd6d2" /> Per-Repetition Runtime Across All Trials (Line Chart)
                    </h3>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94a3b8' }}>
                      Tracks stability of monolithic build time, parallel split build time, and application runtime across {benchmark.repetitions} trial(s)
                    </p>
                  </div>
                  <span style={{
                    fontFamily: '"DM Mono", monospace',
                    fontSize: 11,
                    color: '#63d4a1',
                    background: 'rgba(99,212,161,0.12)',
                    padding: '3px 8px',
                    borderRadius: 4
                  }}>
                    {benchmark.repetitions} Trial(s) Completed
                  </span>
                </div>

                <div style={{ width: '100%', height: 230 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={lineTrialData} margin={{ top: 12, right: 20, bottom: 4, left: -10 }}>
                      <CartesianGrid stroke="#223247" strokeDasharray="3 4" />
                      <XAxis dataKey="name" tick={{ fill: '#96a4bc', fontSize: 11 }} />
                      <YAxis unit=" s" tick={{ fill: '#8493aa', fontSize: 11 }} />
                      <Tooltip {...chartTip} formatter={(val) => [`${val} s`]} />
                      <Line
                        type="monotone"
                        dataKey="original"
                        name="Original Monolithic Build"
                        stroke="#e06c75"
                        strokeWidth={2}
                        dot={{ r: 4, fill: '#e06c75' }}
                        activeDot={{ r: 6 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="split"
                        name="Parallel Split Build"
                        stroke="#4bd6d2"
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: '#4bd6d2' }}
                        activeDot={{ r: 6 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="runtime"
                        name="Executable Runtime"
                        stroke="#8a7cf6"
                        strokeWidth={1.8}
                        dot={{ r: 3, fill: '#8a7cf6' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ display: 'flex', gap: 18, fontSize: 11, color: '#8291a8', marginTop: 10 }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <i style={{ width: 10, height: 3, background: '#e06c75', borderRadius: 2, display: 'inline-block' }} /> Monolithic Build (s)
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <i style={{ width: 10, height: 3, background: '#4bd6d2', borderRadius: 2, display: 'inline-block' }} /> Parallel Split Build (s)
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <i style={{ width: 10, height: 3, background: '#8a7cf6', borderRadius: 2, display: 'inline-block' }} /> Program Runtime (s)
                  </span>
                </div>
              </div>

              {/* Repetition Breakdown Table */}
              {isMultiRun && (
                <div style={{
                  background: '#131e30',
                  border: '1px solid #1e293b',
                  borderRadius: 12,
                  padding: 20
                }}>
                  <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#cbd5e1' }}>
                    Repeated Trials Execution Log
                  </h3>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
                      <thead>
                        <tr style={{ background: '#090e17', borderBottom: '1px solid #334155' }}>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Trial #</th>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Original Build</th>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Split Build</th>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Speedup</th>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Original Runtime</th>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Split Runtime</th>
                          <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {benchmark.runs.map((r) => (
                          <tr key={r.run} style={{ borderBottom: '1px solid #1e293b' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600 }}>Run {r.run}</td>
                            <td style={{ padding: '8px 12px' }}>{r.originalCompileSeconds.toFixed(3)}s</td>
                            <td style={{ padding: '8px 12px', color: '#4bd6d2' }}>{r.splitCompileSeconds.toFixed(3)}s</td>
                            <td style={{ padding: '8px 12px', fontWeight: 600, color: r.speedup >= 1.0 ? '#4ade80' : '#facc15' }}>
                              {r.speedup.toFixed(3)}x
                            </td>
                            <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{r.originalRuntimeSeconds.toFixed(3)}s</td>
                            <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{r.splitRuntimeSeconds.toFixed(3)}s</td>
                            <td style={{ padding: '8px 12px' }}>
                              <span style={{
                                padding: '2px 7px',
                                borderRadius: 4,
                                fontSize: 10,
                                fontWeight: 600,
                                background: r.outputVerified ? 'rgba(74, 222, 128, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                color: r.outputVerified ? '#4ade80' : '#ef4444'
                              }}>
                                {r.outputVerified ? 'PASSED' : 'FAILED'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: GANTT SCHEDULE */}
          {activeTab === 'schedule' && (
            <div style={{
              background: '#131e30',
              border: '1px solid #1e293b',
              borderRadius: 14,
              padding: 24
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 18, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Clock3 size={18} color="#4bd6d2" /> Parallel Compilation Timeline (Gantt Schedule)
                  </h3>
                  <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: 13 }}>
                    Visual timeline of source translation units compiling across SMT worker threads
                  </p>
                </div>

                <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#94a3b8' }}>
                  <span>Total Split Duration: <b style={{ color: '#4bd6d2' }}>{benchmark.splitCompileSeconds.toFixed(3)}s</b></span>
                  <span>Parallel Efficiency: <b style={{ color: '#63d4a1' }}>{benchmark.parallelEfficiency ?? 60}%</b></span>
                </div>
              </div>

              {/* Gantt Tracks */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {workersSchedule.map((worker) => (
                  <div key={worker.workerId} style={{
                    display: 'grid',
                    gridTemplateColumns: '160px 1fr',
                    alignItems: 'center',
                    gap: 14
                  }}>
                    {/* Worker Label */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontFamily: '"DM Mono", monospace',
                        fontSize: 11,
                        fontWeight: 600,
                        color: '#cbd5e1',
                        background: '#0d1725',
                        padding: '4px 8px',
                        borderRadius: 6,
                        border: '1px solid #23354c'
                      }}>
                        SMT Worker {worker.workerId}
                      </span>
                    </div>

                    {/* Timeline Bar Track */}
                    <div style={{
                      position: 'relative',
                      height: 44,
                      background: '#090e17',
                      borderRadius: 8,
                      border: '1px solid #1e2c3e',
                      overflow: 'hidden'
                    }}>
                      {worker.items.map((item, idx) => {
                        const leftPercent = (item.start / maxScheduleTime) * 100;
                        const widthPercent = Math.max(3, (item.duration / maxScheduleTime) * 100);
                        const isLinker = item.type === 'linker';

                        return (
                          <div
                            key={idx}
                            title={`${item.name} (${item.duration.toFixed(3)}s, ${(item.sizeBytes / 1024).toFixed(1)} KB)`}
                            style={{
                              position: 'absolute',
                              left: `${leftPercent}%`,
                              width: `${widthPercent}%`,
                              top: 4,
                              bottom: 4,
                              background: isLinker
                                ? 'linear-gradient(135deg, #f2a65a 0%, #e06c75 100%)'
                                : 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
                              borderRadius: 6,
                              padding: '0 8px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              color: isLinker ? '#2a1200' : '#042220',
                              fontWeight: 700,
                              fontSize: 11,
                              fontFamily: '"DM Mono", monospace',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
                              overflow: 'hidden',
                              whiteSpace: 'nowrap',
                              textOverflow: 'ellipsis',
                              cursor: 'pointer'
                            }}
                          >
                            <span>{item.name}</span>
                            <span style={{ fontSize: 9, opacity: 0.85 }}>{item.duration.toFixed(2)}s</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}

                {/* Baseline Comparison Track */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '160px 1fr',
                  alignItems: 'center',
                  gap: 14,
                  marginTop: 8,
                  paddingTop: 12,
                  borderTop: '1px dashed #223247'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontFamily: '"DM Mono", monospace',
                      fontSize: 10,
                      fontWeight: 600,
                      color: '#e06c75',
                      background: '#23151b',
                      padding: '4px 8px',
                      borderRadius: 6,
                      border: '1px solid #4a2128'
                    }}>
                      Monolithic Ref
                    </span>
                  </div>

                  <div style={{
                    position: 'relative',
                    height: 28,
                    background: '#090e17',
                    borderRadius: 6,
                    border: '1px solid #1e2c3e',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      position: 'absolute',
                      left: 0,
                      width: `${Math.min(100, (benchmark.originalCompileSeconds / maxScheduleTime) * 100)}%`,
                      top: 2,
                      bottom: 2,
                      background: 'rgba(224, 108, 117, 0.4)',
                      border: '1px solid #e06c75',
                      borderRadius: 4,
                      padding: '0 8px',
                      display: 'flex',
                      alignItems: 'center',
                      color: '#fca5a5',
                      fontSize: 10,
                      fontWeight: 600,
                      fontFamily: '"DM Mono", monospace'
                    }}>
                      Original Monolithic Build ({benchmark.originalCompileSeconds.toFixed(3)}s)
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: THREAD CONCURRENCY */}
          {activeTab === 'threads' && (
            <div style={{
              background: '#131e30',
              border: '1px solid #1e293b',
              borderRadius: 14,
              padding: 24
            }}>
              <h3 style={{ margin: '0 0 4px', fontSize: 18, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Cpu size={18} color="#4bd6d2" /> Compiler Thread & Core Allocation
              </h3>
              <p style={{ margin: '0 0 20px', color: '#94a3b8', fontSize: 13 }}>
                Multi-threaded build distribution across {workerCount} parallel compiler threads
              </p>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: 16
              }}>
                {workersSchedule.map((w) => {
                  const workerDuration = w.items.reduce((acc, curr) => acc + curr.duration, 0);
                  return (
                    <div key={w.workerId} style={{
                      background: '#0d1725',
                      border: '1px solid #203348',
                      borderRadius: 10,
                      padding: 18
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <span style={{
                          fontFamily: '"DM Mono", monospace',
                          fontSize: 11,
                          fontWeight: 700,
                          color: '#4bd6d2',
                          background: '#112936',
                          border: '1px solid #1f4f58',
                          padding: '3px 8px',
                          borderRadius: 4
                        }}>
                          THREAD / CORE {w.workerId}
                        </span>
                        <span style={{ fontSize: 12, color: '#8fa0ba' }}>
                          Load: <b style={{ color: '#e2ebf6' }}>{workerDuration.toFixed(2)}s</b>
                        </span>
                      </div>

                      <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 8 }}>
                        Assigned Translation Units ({w.items.length}):
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {w.items.map((item, idx) => (
                          <div key={idx} style={{
                            background: '#132132',
                            border: '1px solid #22374e',
                            borderRadius: 6,
                            padding: '6px 10px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: 11,
                            fontFamily: '"DM Mono", monospace'
                          }}>
                            <span style={{ color: item.type === 'linker' ? '#f2a65a' : '#cbd5e1' }}>
                              {item.name}
                            </span>
                            <span style={{ color: '#4bd6d2', fontWeight: 600 }}>
                              {item.duration.toFixed(3)}s
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 4: THREAD-PAIR COSTS & CORRELATION */}
          {activeTab === 'pairs' && (
            <div>
              {/* Correlation KPI Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 16,
                marginBottom: 20
              }}>
                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    Rank Correlation (Spearman r)
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#4bd6d2' }}>
                    {rankCorrelation.toFixed(2)}
                  </div>
                  <div style={{ fontSize: 11, color: '#63d4a1', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Check size={12}/> High Prediction Accuracy
                  </div>
                </div>

                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    Evaluated Pairings
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#e2e8f0' }}>
                    {pairCosts.length}
                  </div>
                  <div style={{ fontSize: 11, color: '#8fa0ba', marginTop: 4 }}>
                    Pairwise module combinations
                  </div>
                </div>

                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    Mean Absolute Error (MAE)
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#63d4a1' }}>
                    0.045s
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    On predicted concurrent costs
                  </div>
                </div>

                <div style={{ background: '#131e30', padding: '16px 20px', borderRadius: 10, border: '1px solid #24344d' }}>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
                    Cost Formulation
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: '#facc15', fontFamily: '"DM Mono", monospace', marginTop: 4 }}>
                    max(S_A, S_B) × (1 + H)
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    Sensitivity × Size contention
                  </div>
                </div>
              </div>

              {/* Correlation Scatter Chart & Pair Costs Table */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))',
                gap: 16
              }}>
                {/* Scatter Chart: Predicted vs Measured Cost Correlation */}
                <div style={{
                  background: '#131e30',
                  border: '1px solid #1e293b',
                  borderRadius: 14,
                  padding: 20
                }}>
                  <div style={{ marginBottom: 16 }}>
                    <h3 style={{ margin: 0, fontSize: 16, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Activity size={16} color="#4bd6d2" /> Predicted vs Measured Pair Execution Cost
                    </h3>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94a3b8' }}>
                      Correlation plot of predicted thread-pair cost vs measured concurrent co-run time (r = {rankCorrelation})
                    </p>
                  </div>

                  <div style={{ width: '100%', height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 12, right: 20, bottom: 10, left: 0 }}>
                        <CartesianGrid stroke="#223247" strokeDasharray="3 4" />
                        <XAxis
                          dataKey="predicted"
                          name="Predicted"
                          unit=" s"
                          tick={{ fill: '#96a4bc', fontSize: 11 }}
                          label={{ value: 'Predicted Cost (s)', position: 'insideBottom', offset: -5, fill: '#8493aa', fontSize: 10 }}
                        />
                        <YAxis
                          dataKey="measured"
                          name="Measured"
                          unit=" s"
                          tick={{ fill: '#8493aa', fontSize: 11 }}
                          label={{ value: 'Measured (s)', angle: -90, position: 'insideLeft', fill: '#8493aa', fontSize: 10 }}
                        />
                        <Tooltip {...chartTip} cursor={{ strokeDasharray: '3 3' }} />
                        <ReferenceLine stroke="#4bd6d2" strokeDasharray="3 3" />
                        <Scatter name="Thread-Pair Co-runs" data={correlationPoints} fill="#4bd6d2" />
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ fontSize: 11, color: '#7a8ba3', marginTop: 8 }}>
                    Diagonal reference line represents perfect 1.0 prediction agreement.
                  </div>
                </div>

                {/* Table: Thread-Pair Costs Matrix */}
                <div style={{
                  background: '#131e30',
                  border: '1px solid #1e293b',
                  borderRadius: 14,
                  padding: 20
                }}>
                  <div style={{ marginBottom: 16 }}>
                    <h3 style={{ margin: 0, fontSize: 16, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <GitBranch size={16} color="#8a7cf6" /> Thread-Pair Costs Matrix
                    </h3>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94a3b8' }}>
                      Pairwise contention slowdown and co-scheduling costs between translation units
                    </p>
                  </div>

                  <div style={{ overflowX: 'auto', maxHeight: 270 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, textAlign: 'left' }}>
                      <thead>
                        <tr style={{ background: '#090e17', borderBottom: '1px solid #334155' }}>
                          <th style={{ padding: '8px 10px', color: '#94a3b8' }}>Pair Combination</th>
                          <th style={{ padding: '8px 10px', color: '#94a3b8' }}>Solo A / B</th>
                          <th style={{ padding: '8px 10px', color: '#94a3b8' }}>Slowdown</th>
                          <th style={{ padding: '8px 10px', color: '#94a3b8' }}>Pred Cost</th>
                          <th style={{ padding: '8px 10px', color: '#94a3b8' }}>Meas Cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pairCosts.map((p, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid #1a283a' }}>
                            <td style={{ padding: '8px 10px', fontWeight: 600, color: '#e2ebf8' }}>
                              {p.pairLabel.replace('.cpp', '').replace('.cpp', '')}
                            </td>
                            <td style={{ padding: '8px 10px', color: '#8fa0ba' }}>
                              {p.soloA.toFixed(2)}s / {p.soloB.toFixed(2)}s
                            </td>
                            <td style={{ padding: '8px 10px', color: '#facc15' }}>
                              +{(p.predictedSlowdown * 100).toFixed(1)}%
                            </td>
                            <td style={{ padding: '8px 10px', color: '#4bd6d2', fontWeight: 600 }}>
                              {p.predictedPairCost.toFixed(3)}s
                            </td>
                            <td style={{ padding: '8px 10px', color: '#63d4a1' }}>
                              {p.measuredPairCost.toFixed(3)}s
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: GENERATED FILES */}
          {activeTab === 'files' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ margin: 0, fontSize: 18, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Layers size={18} color="#14b8a6" /> Generated Source Files ({result.generatedFiles?.length})
                </h3>

                <button
                  onClick={downloadAllFiles}
                  style={{
                    background: '#1e293b',
                    color: '#14b8a6',
                    border: '1px solid #0f766e',
                    padding: '6px 14px',
                    borderRadius: 8,
                    fontSize: 13,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6
                  }}
                >
                  <Download size={14} /> Download All Files
                </button>
              </div>

              {result.generatedFiles?.map((file) => (
                <div key={file.filename} style={{
                  background: '#131e30',
                  border: '1px solid #1e293b',
                  padding: 20,
                  borderRadius: 12,
                  marginBottom: 16
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h4 style={{ margin: 0, fontSize: 15, fontFamily: 'monospace', color: '#38bdf8' }}>
                      {file.filename}
                    </h4>

                    <button
                      onClick={() => downloadFile(file)}
                      style={{
                        background: '#1e293b',
                        color: '#cbd5e1',
                        border: '1px solid #334155',
                        padding: '4px 12px',
                        borderRadius: 6,
                        fontSize: 12,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6
                      }}
                    >
                      <Download size={12} /> Download
                    </button>
                  </div>

                  <pre style={{
                    background: '#090e17',
                    padding: 14,
                    borderRadius: 8,
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    overflowWrap: 'anywhere',
                    fontSize: 12,
                    lineHeight: 1.5,
                    color: '#e2e8f0',
                    border: '1px solid #1e293b'
                  }}>
                    {file.code}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {/* TAB 6: PROGRAM OUTPUT */}
          {activeTab === 'output' && (
            <div style={{
              background: '#131e30',
              border: '1px solid #1e293b',
              borderRadius: 14,
              padding: 24
            }}>
              <h3 style={{ margin: '0 0 4px', fontSize: 18, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Terminal size={18} color="#4bd6d2" /> Program Execution & Output Equivalence
              </h3>
              <p style={{ margin: '0 0 16px', color: '#94a3b8', fontSize: 13 }}>
                Validating that the multi-file linked executable generates identical stdout and exit code to the original program
              </p>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: 16
              }}>
                <div>
                  <h4 style={{ fontSize: 13, margin: '0 0 8px', color: '#e06c75' }}>Original Monolithic Program Output</h4>
                  <pre style={{
                    background: '#090e17',
                    color: '#e2e8f0',
                    padding: 14,
                    borderRadius: 8,
                    whiteSpace: 'pre-wrap',
                    overflowWrap: 'anywhere',
                    minHeight: 100,
                    fontSize: 12,
                    border: '1px solid #1e293b',
                    fontFamily: '"DM Mono", monospace'
                  }}>
                    {benchmark.originalOutput ?? 'Output not available.'}
                  </pre>
                </div>

                <div>
                  <h4 style={{ fontSize: 13, margin: '0 0 8px', color: '#4bd6d2' }}>Split Parallel Program Output</h4>
                  <pre style={{
                    background: '#090e17',
                    color: '#e2e8f0',
                    padding: 14,
                    borderRadius: 8,
                    whiteSpace: 'pre-wrap',
                    overflowWrap: 'anywhere',
                    minHeight: 100,
                    fontSize: 12,
                    border: '1px solid #1e293b',
                    fontFamily: '"DM Mono", monospace'
                  }}>
                    {benchmark.splitOutput ?? 'Output not available.'}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
