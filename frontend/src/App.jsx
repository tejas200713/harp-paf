import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, NavLink, Route, Routes, useNavigate, useParams, Navigate } from 'react-router-dom';
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cpu,
  Download,
  FileCode2,
  Gauge,
  GitBranch,
  History as HistoryIcon,
  Home as HomeIcon,
  Layers3,
  Menu,
  Microscope,
  Network,
  Plus,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  AlertTriangle,
  Zap,
  Info,
  Terminal
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import LatestJobRedirect from './LatestJobRedirect.jsx';
import CodeOutputViewer from './components/CodeOutputViewer.jsx';
import AnalysisNavTabs from './components/AnalysisNavTabs.jsx';
import {
  createJob,
  getJob as getLiveJob,
  getResults,
  listJobs,
  getSystem,
  getWorkloads,
  checkHealth
} from './services/api.js';

// --- Global Method Config & Colors ---
const METHOD_CONFIG = {
  harp: { label: 'HARP-PAF', color: '#4bd6d2', highlight: true },
  harp_static: { label: 'HARP-PAF (static pairs)', color: '#2a8f8c' },
  port: { label: 'PORT', color: '#8a7cf6' },
  random: { label: 'Random', color: '#f2a65a' },
  linux: { label: 'OS default', color: '#e06c75' },
  serial: { label: 'Serial (no SMT)', color: '#6b7a93' }
};

const getMethodLabel = (methods, key) => methods?.[key]?.label || METHOD_CONFIG[key]?.label || key;
const getMethodColor = (key) => METHOD_CONFIG[key]?.color || '#4bd6d2';

const nav = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/upload', label: 'New analysis', icon: Plus },
  { section: 'Workspace' },
  { to: '/results', label: 'Results dashboard', icon: BarChart3 },
  { to: '/schedule', label: 'Schedule view', icon: Clock3 },
  { to: '/output', label: 'Code & Stdout', icon: Terminal },
  { to: '/pairs', label: 'Pair analysis', icon: Network },
  { to: '/tasks', label: 'Task metrics', icon: Activity },
  { to: '/predictions', label: 'Prediction analysis', icon: Gauge },
  { section: 'Manage' },
  { to: '/history', label: 'History & reports', icon: HistoryIcon },
  { to: '/system', label: 'System information', icon: Server }
];

function Brand({ compact = false }) {
  return (
    <Link to="/" className={'brand ' + (compact ? 'brand-compact' : '')}>
      <span className="brand-mark"><Cpu size={20}/><i/></span>
      <span>
        <b>HARP<span className="brand-accent">·</span>PAF</b>
        <small>RESEARCH PLATFORM</small>
      </span>
    </Link>
  );
}

function Sidebar({ open, onClose }) {
  return (
    <>
      <div className={'sidebar-scrim ' + (open ? 'show' : '')} onClick={onClose}/>
      <aside className={'sidebar ' + (open ? 'sidebar-open' : '')}>
        <div className="sidebar-top">
          <Brand/>
          <button className="icon-btn mobile-close" onClick={onClose} aria-label="Close navigation">
            <X size={17}/>
          </button>
        </div>
        <div className="workspace-switch">
          <span className="workspace-icon"><Microscope size={16}/></span>
          <span><b>HARP-PAF Lab</b><small>SMT Co-Scheduling</small></span>
          <ChevronDown size={14}/>
        </div>
        <nav aria-label="Main navigation">
          {nav.map((item, i) =>
            item.section ? (
              <div className="nav-section" key={i}>{item.section}</div>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={onClose}
                className={({ isActive }) => 'nav-link ' + (isActive ? 'active' : '')}
              >
                <item.icon size={17}/>
                <span>{item.label}</span>
                {item.to === '/upload' && <span className="nav-new">NEW</span>}
              </NavLink>
            )
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-health">
            <span className="health-dot"/>
            <div><b>Windows / Linux environment</b><small>FastAPI backend ready</small></div>
          </div>
          <div className="sidebar-user">
            <div className="avatar">HP</div>
            <div><b>Research Lab</b><small>Intel SMT Performance</small></div>
          </div>
        </div>
      </aside>
    </>
  );
}

function AppLayout({ children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="app-shell">
      <Sidebar open={open} onClose={() => setOpen(false)}/>
      <main className="main-shell">
        <header className="topbar">
          <button className="icon-btn mobile-menu" aria-label="Open navigation" onClick={() => setOpen(true)}>
            <Menu size={19}/>
          </button>
          <div className="breadcrumb">
            <span>HARP-PAF</span>
            <ChevronRight size={13}/>
            <b>{children.props?.title || 'Workspace'}</b>
          </div>
          <div className="topbar-right">
            <span className="connection"><i/> Backend connected</span>
            <div className="avatar avatar-small">HP</div>
          </div>
        </header>
        <div className="page-wrap">{children}</div>
      </main>
    </div>
  );
}

function Page({ title, eyebrow, subtitle, actions, children }) {
  return (
    <div className="page" title={title}>
      <div className="page-heading">
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && <div className="page-actions">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

function Status({ children, tone = 'neutral' }) {
  return <span className={'status status-' + tone}><i/>{children}</span>;
}

function MetricCard({ label, value, unit, detail, icon: Icon, trend }) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        {Icon && <span className="metric-icon"><Icon size={17}/></span>}
      </div>
      <div className="metric-value">{value}<small>{unit}</small></div>
      <div className="metric-foot">
        {trend && <span className="metric-trend"><ArrowDownRight size={14}/>{trend}</span>}
        {detail}
      </div>
    </article>
  );
}

function Card({ title, subtitle, actions, children, className = '' }) {
  return (
    <section className={'card ' + className}>
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

const fmt = (v, n = 2) => (v == null ? '—' : Number(v).toFixed(n));
const fmtSec = (v, n = 2) => (v == null ? '—' : `${Number(v).toFixed(n)} s`);
const fmtPct = (v, n = 1) => (v == null ? '—' : `${(Number(v) * 100).toFixed(n)}%`);

const chartTip = {
  contentStyle: { background: '#0e1828', border: '1px solid #283a54', borderRadius: 8, color: '#eef3ff', fontSize: 11 },
  itemStyle: { color: '#b8c5dd' },
  labelStyle: { color: '#f2f6ff', fontWeight: 600 }
};

function jsonDownload(filename, data) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function csvDownload(filename, rows) {
  if (!rows || !rows.length) return;
  const keys = Object.keys(rows[0] || {});
  const escape = v => `"${String(v ?? '').replaceAll('"', '""')}"`;
  const csv = [keys.map(escape).join(','), ...rows.map(r => keys.map(k => escape(r[k])).join(','))].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ==========================================
// HOME PAGE
// ==========================================
function Home() {
  const features = [
    ['Dynamic SMT Co-Scheduling', 'Online dispatch onto the two hardware threads of an SMT core so no thread idles while work remains.', Clock3],
    ['Sensitivity × Aggressiveness', 'Contention predictions combining workload stressor sensitivity with EMON counter profiles.', Gauge],
    ['Rigorous Multi-Method Comparison', 'Evaluated against Random, PORT, OS default scheduler, static pairs, and serial execution.', BarChart3],
    ['Validated Hardware Benchmarks', 'Calibrated on Intel Core i5-1235U with drift-free adjacent solo baseline references.', ShieldCheck]
  ];

  return (
    <Page
      title="Dynamic SMT co-scheduling for maximum core throughput"
      eyebrow="PHASE-AWARE SMT CO-SCHEDULING"
      subtitle="HARP-PAF decides which programs should share one physical CPU core running two hardware threads simultaneously. It fuses static binary analysis with runtime hardware counters and stressor probes to predict contention and dynamically schedule threads."
      actions={
        <Link className="btn btn-primary" to="/upload">
          <Upload size={16}/> Upload code <ArrowRight size={16}/>
        </Link>
      }
    >
      <div className="hero-grid">
        <div className="hero-copy">
          <span className="hero-kicker"><span className="pulse-dot"/> MEASURED SMT PERFORMANCE OPTIMIZATION</span>
          <h2>Dynamic SMT co-scheduling<br/>with <span>measured slowdown models.</span></h2>
          <p>
            On an Intel Core i5-1235U (one SMT performance core) with eight resource-specific workloads and ten repetitions,
            HARP-PAF completed the workload set in a median of <b>3.20 s</b>, compared with <b>3.49 s</b> for random co-scheduling,
            <b>3.53 s</b> for the OS scheduler, <b>3.74 s</b> for PORT, and <b>5.47 s</b> for serial execution; it was faster than every baseline in 9–10 of 10 repetitions.
          </p>
          <div className="hero-actions">
            <Link to="/upload" className="btn btn-primary"><Upload size={16}/> Upload code</Link>
            <Link to="/results" className="btn btn-secondary">View results dashboard <ArrowRight size={15}/></Link>
          </div>
          <div className="hero-proof">
            <span><Check size={14}/> Bottleneck sensitivity × aggressiveness</span>
            <span><Check size={14}/> Calibrated model (MAE 0.069)</span>
            <span><Check size={14}/> 6 evaluated methods</span>
          </div>
        </div>

        <div className="core-visual">
          <div className="core-visual-head">
            <span>PHYSICAL PERFORMANCE CORE</span>
            <span className="live-pill"><i/> SMT Siblings CPU 0 & 1</span>
          </div>
          <div className="core-pair">
            <div className="core-box">
              <div className="core-label"><Cpu size={15}/> HW THREAD 0</div>
              <div className="thread-slot"><small>CPU 0</small><b><Activity size={14}/> Task T08 (Mix)</b></div>
              <div className="thread-slot"><small>NEXT</small><b><Activity size={14}/> Task T07 (Branch)</b></div>
            </div>
            <div className="pair-connector">
              <span>SHARED<br/>CORE</span>
              <div>↔</div>
            </div>
            <div className="core-box">
              <div className="core-label"><Cpu size={15}/> HW THREAD 1</div>
              <div className="thread-slot"><small>CPU 1</small><b><Activity size={14}/> Task T01 (Int)</b></div>
              <div className="thread-slot"><small>NEXT</small><b><Activity size={14}/> Task T06 (Chase)</b></div>
            </div>
          </div>
          <div className="core-visual-foot">
            <span><i className="legend-cyan"/> HARP-PAF dynamic placement</span>
            <span><i className="legend-violet"/> Min predicted slowdown</span>
          </div>
        </div>
      </div>

      <div className="feature-grid">
        {features.map(([title, desc, Icon]) => (
          <article className="feature-card" key={title}>
            <span className="feature-icon"><Icon size={18}/></span>
            <h3>{title}</h3>
            <p>{desc}</p>
          </article>
        ))}
      </div>

      <section id="workflow" className="workflow card">
        <div className="workflow-head">
          <div>
            <div className="eyebrow">THE HARP-PAF PIPELINE</div>
            <h2>From source to measured execution</h2>
          </div>
          <Link to="/upload" className="text-link">Start an analysis <ArrowRight size={14}/></Link>
        </div>
        <div className="workflow-steps">
          {[
            ['01', 'Source code', 'Upload 2–16 workloads'],
            ['02', 'Profile fusion', 'Static mix + EMON counters'],
            ['03', 'Slowdown model', 'Bottleneck sensitivity × aggressiveness'],
            ['04', 'Dynamic scheduling', 'SMT co-runner selection'],
            ['05', 'Multi-method bench', 'Compare against 5 baselines']
          ].map(([n, title, sub], i) => (
            <div className="workflow-step" key={n}>
              <span className="step-num">{n}</span>
              <b>{title}</b>
              <small>{sub}</small>
              {i < 4 && <span className="step-line"/>}
            </div>
          ))}
        </div>
      </section>

      <div className="formula-note">
        <span className="feature-icon"><Layers3 size={17}/></span>
        <div>
          <b>Slowdown Prediction Model</b>
          <code>Slowdown(A, B) = b0 + b × max(Sensitivity_A(contended) × Aggressiveness_B(contended), Sensitivity_B(contended) × Aggressiveness_A(contended))</code>
        </div>
        <span className="formula-caption">Calibrated on 55 measured training pairs (MAE 0.069)</span>
      </div>
    </Page>
  );
}

// ==========================================
// TASK 6: UPLOAD CODE
// ==========================================
function UploadCode() {
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState([]);
  const [repetitions, setRepetitions] = useState(5);
  const [error, setError] = useState('');
  const [drag, setDrag] = useState(false);
  const [workloads, setWorkloads] = useState([]);
  const input = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    getWorkloads()
      .then(data => setWorkloads(data || []))
      .catch(() => {});
  }, []);

  const add = incoming => {
    setError('');
    const accepted = [];
    for (const f of incoming) {
      if (!f.name.toLowerCase().endsWith('.cpp')) {
        setError(`${f.name}: Only .cpp program source files are accepted.`);
        continue;
      }
      if (files.some(x => x.name === f.name) || accepted.some(x => x.name === f.name)) continue;
      accepted.push(f);
    }
    const combined = [...files, ...accepted];
    if (combined.length > 16) {
      setError('A maximum of 16 source files can be submitted for one analysis.');
      setFiles(combined.slice(0, 16));
    } else {
      setFiles(combined);
    }
  };

  const remove = i => setFiles(a => a.filter((_, n) => n !== i));

  const addPreset = (w) => {
    setError('');
    if (files.some(f => f.name === w.file)) return;
    if (files.length >= 16) {
      setError('A maximum of 16 source files can be submitted.');
      return;
    }
    const fakeFile = new File([`// Preset: ${w.file}\n// ${w.description}\n`], w.file, { type: 'text/plain' });
    setFiles(prev => [...prev, fakeFile]);
  };

  const submit = async () => {
    if (busy) return;
    setError('');

    if (files.length < 2 || files.length > 16) {
      setError('Please select between 2 and 16 C++ source files.');
      return;
    }

    if (repetitions < 3 || repetitions > 15) {
      setError('Repetitions must be between 3 and 15.');
      return;
    }

    try {
      setBusy(true);
      const job = await createJob(files, 'cpp', repetitions);
      if (!job.jobId) throw new Error('The backend did not return a job ID.');
      navigate(`/jobs/${job.jobId}`);
    } catch (err) {
      setError(err.message || 'The analysis could not be initiated.');
    } finally {
      setBusy(false);
    }
  };

  const total = files.reduce((n, f) => n + f.size, 0);

  return (
    <Page
      title="New analysis"
      eyebrow="WORKSPACE / NEW ANALYSIS"
      subtitle="Upload 2–16 C++ workloads to evaluate dynamic SMT co-scheduling against 5 baselines."
    >
      <div className="upload-layout">
        <div className="upload-main card">
          <div className="card-heading">
            <div>
              <h2>Add C++ Workload Source Files</h2>
              <p>Upload between 2 and 16 independent workload files (e.g. approved benchmark suite).</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <label style={{ fontSize: 11, color: '#90a0b6' }}>
                REPETITIONS (3–15):
                <input
                  type="number"
                  min="3"
                  max="15"
                  value={repetitions}
                  onChange={e => setRepetitions(Math.max(3, Math.min(15, parseInt(e.target.value) || 5)))}
                  style={{ width: 55, marginLeft: 8, padding: '4px 6px', background: '#101a28', border: '1px solid #28374c', color: '#eef', borderRadius: 4 }}
                />
              </label>
            </div>
          </div>

          <input ref={input} type="file" hidden multiple accept=".cpp" onChange={e => { add([...e.target.files]); e.target.value = ''; }}/>
          <div
            className={'dropzone ' + (drag ? 'dragging' : '')}
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={e => { e.preventDefault(); setDrag(false); add([...e.dataTransfer.files]); }}
          >
            <span className="drop-icon"><Upload size={20}/></span>
            <b>Drag C++ source files here</b>
            <span>or <button className="inline-button" onClick={() => input.current?.click()}>browse your files</button></span>
            <small>Accepts 2–16 files (.cpp) · Non-empty up to 100 KB each</small>
          </div>

          {files.length > 0 && (
            <div className="file-list">
              <div className="file-list-head">
                <span>SELECTED WORKLOADS <b>{files.length}</b> (2–16 allowed)</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span>{(total / 1024).toFixed(1)} KB total</span>
                  <button
                    className="inline-button"
                    style={{ color: '#f87171', fontSize: 11, cursor: 'pointer', background: 'transparent', border: 'none' }}
                    onClick={() => setFiles([])}
                  >
                    Clear all
                  </button>
                </div>
              </div>
              {files.map((f, i) => (
                <div className="file-row" key={f.name + i}>
                  <span className="file-icon"><FileCode2 size={16}/></span>
                  <span className="file-name">
                    <b>{f.name}</b>
                    <small>{f.size < 1024 ? `${f.size} B` : `${(f.size / 1024).toFixed(1)} KB`}</small>
                  </span>
                  <span className="file-valid"><Check size={13}/> Ready</span>
                  <button className="icon-btn remove-file" aria-label={`Remove ${f.name}`} onClick={() => remove(i)}>
                    <X size={15}/>
                  </button>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="form-error">
              <AlertTriangle size={15}/>{error}
            </div>
          )}

          <div className="upload-note">
            <Info size={16}/>
            <p>
              Full benchmark execution includes EMON hardware counter profiling, sensitivity stressor probing,
              and 10 repetitions across all 6 scheduling methods. Real benchmark jobs take approximately 10–15 minutes.
            </p>
          </div>

          <div className="upload-footer">
            <span><ShieldCheck size={15}/> Windows / Linux native execution</span>
            <button className="btn btn-primary" onClick={submit} disabled={busy || files.length < 2}>
              <Sparkles size={15}/>
              {busy ? 'Initiating benchmark...' : `Analyze & Optimize (${files.length} files, ${repetitions} reps)`}
              <ArrowRight size={15}/>
            </button>
          </div>
        </div>

        <aside className="upload-aside">
          <Card title="Approved Workloads" subtitle="Click to add from benchmark suite">
            <div style={{ maxHeight: 380, overflowY: 'auto' }}>
              {workloads.map(w => (
                <div
                  key={w.file}
                  style={{
                    padding: '8px 10px',
                    borderBottom: '1px solid #1c2738',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                  onClick={() => addPreset(w)}
                  title="Click to add this workload"
                >
                  <div>
                    <b style={{ display: 'block', fontSize: 11, color: '#56d5d0' }}>{w.file}</b>
                    <small style={{ fontSize: 9, color: '#8898ae' }}>{w.description}</small>
                  </div>
                  <span className="comp-badge" style={{ background: '#162334', color: '#97a8bc' }}>{w.kind}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Execution Workflow" subtitle="What happens during analysis">
            <div className="mini-steps">
              {[
                ['1', 'Source validation & compile'],
                ['2', 'Verify solo outputs'],
                ['3', 'Profile EMON counters & stressor probes'],
                ['4', 'Compute pair costs & slowdown model'],
                ['5', 'Dynamic & baseline benchmarks']
              ].map(([n, l]) => (
                <div className="mini-step" key={n}>
                  <span className="mini-step-num on">{n}</span>
                  <span><b>{l}</b></span>
                </div>
              ))}
            </div>
          </Card>
        </aside>
      </div>
    </Page>
  );
}

// ==========================================
// TASK 6: PROGRESS PAGE
// ==========================================
const PIPELINE_STAGES = [
  'Validate',
  'Compile',
  'Verify outputs',
  'Profile (counters + probes)',
  'Pair costs & model',
  'Benchmark (all methods)',
  'Save',
  'Done'
];

function JobProgress() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    let timer;

    async function loadJob() {
      try {
        const data = await getLiveJob(id);
        if (!active) return;
        setJob(data);
        setLoading(false);
        setError('');

        if (data.status === 'running') {
          timer = setTimeout(loadJob, 2000);
        }
      } catch (err) {
        if (!active) return;
        setError(err.message);
        setLoading(false);
      }
    }

    setJob(null);
    setLoading(true);
    loadJob();

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id]);

  const completed = job?.status === 'completed';
  const failed = job?.status === 'failed';
  const stage = Math.max(0, Math.min(8, Number(job?.stageIndex ?? (completed ? 8 : 0))));
  const percent = Math.round((stage / 8) * 100);

  return (
    <Page
      title="Analysis progress"
      eyebrow="WORKSPACE / LIVE JOB"
      subtitle="Execution status reported by the HARP-PAF backend service."
      actions={
        <div style={{ display: 'flex', gap: 10 }}>
          <span className="job-id-chip">{id}</span>
          <Link className="btn btn-primary" to={`/schedule/${id}`}>
            <Clock3 size={15}/> View Schedule
          </Link>
          <Link className="btn btn-secondary" to={`/results/${id}`}>
            <BarChart3 size={15}/> View Results Dashboard
          </Link>
          <Link className="btn btn-secondary" to={`/output/${id}`}>
            <Terminal size={15}/> View Stdout
          </Link>
        </div>
      }
    >
      <AnalysisNavTabs id={id} activeTab="jobs"/>
      {loading && <Card title="Loading job"><p>Fetching backend job status...</p></Card>}
      {error && <div className="form-error"><AlertTriangle size={16}/>{error}</div>}

      {job && (
        <>
          <div className="job-summary card">
            <div className="job-summary-icon"><FileCode2 size={21}/></div>
            <div className="job-summary-name">
              <small>SUBMITTED WORKLOADS ({job.files?.length || 0})</small>
              <b>{(job.files || []).map(f => f.originalName).join(', ')}</b>
              <span>{job.language?.toUpperCase()} · {job.createdAt ? new Date(job.createdAt).toLocaleString() : ''}</span>
            </div>
            <div className="job-status">
              <small>STATUS</small>
              <Status tone={failed ? 'error' : completed ? 'success' : 'info'}>
                {job.status?.toUpperCase()}
              </Status>
            </div>
          </div>

          <Card
            title="Pipeline stages"
            subtitle="Real measurement pipeline across 8 phases"
            actions={<b className="progress-percent">{percent}%</b>}
          >
            <div className="progress-track">
              <span style={{ width: `${percent}%` }}/>
            </div>

            <div className="pipeline-list">
              {PIPELINE_STAGES.map((label, i) => {
                const stepNum = i + 1;
                const isDone = !failed && (completed || stage > stepNum || (stage === 8 && i === 7));
                const isCurrent = !completed && !failed && stage === stepNum;

                return (
                  <div className={'pipeline-row ' + (isCurrent ? 'current' : '')} key={label}>
                    <span className={'pipeline-icon ' + (isDone ? 'done' : isCurrent ? 'active' : '')}>
                      {isDone ? <Check size={14}/> : isCurrent ? <span className="spinner"/> : String(stepNum).padStart(2, '0')}
                    </span>
                    <span className="pipeline-name">
                      <b>{stepNum}. {label}</b>
                      <small>
                        {isCurrent && job.stage
                          ? job.stage
                          : isDone
                          ? 'Completed successfully'
                          : 'Pending execution'}
                      </small>
                    </span>
                    <span className="pipeline-state">
                      {isDone ? 'COMPLETED' : isCurrent ? 'RUNNING' : 'PENDING'}
                    </span>
                  </div>
                );
              })}
            </div>

            {failed && (
              <div className="failure-box">
                <AlertTriangle size={16}/>
                <span>{job.error || job.stage}</span>
              </div>
            )}

            <div className="job-footnote">
              <Info size={14}/>
              Jobs take 10–15 minutes: profiling hardware counters, stressor probes, and measuring 6 methods over multiple repetitions.
            </div>
          </Card>

          {/* Workload execution output and verification */}
          <CodeOutputViewer
            outputs={job.executionResults}
            compilationResults={job.compilationResults}
            tasks={job.files}
            title="Live Workload Output & Verification"
            subtitle="Real-time execution stdout, stderr, and compilation diagnostics"
          />
        </>
      )}
    </Page>
  );
}

// ==========================================
// TASK 1: RESULTS DASHBOARD (LiveResults)
// ==========================================
function LiveResults() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';
    getResults(targetId)
      .then(result => { if (active) setData(result); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [id]);

  if (error) {
    return (
      <Page title="Results dashboard">
        <div className="form-error"><AlertTriangle size={16}/>{error}</div>
      </Page>
    );
  }

  if (!data) {
    return (
      <Page title="Results dashboard">
        <Card title="Loading measured results"><p>Fetching benchmark results from backend...</p></Card>
      </Page>
    );
  }

  const s = data.summary || {};
  const methods = data.methods || {};
  const comparisons = data.comparisons || {};
  const rawRuns = data.rawRuns || {};

  // All 6 methods for makespan comparison
  const methodKeys = ['harp', 'random', 'linux', 'harp_static', 'port', 'serial'];
  const makespanData = methodKeys
    .filter(k => methods[k])
    .map(k => {
      const m = methods[k];
      const median = m.makespan?.median ?? 0;
      const ci = m.makespan?.ci95 || [median, median];
      return {
        key: k,
        name: m.label || METHOD_CONFIG[k]?.label || k,
        value: Number(median.toFixed(2)),
        rawMedian: median,
        ciLow: Number(ci[0].toFixed(2)),
        ciHigh: Number(ci[1].toFixed(2)),
        ciError: [Math.max(0, median - ci[0]), Math.max(0, ci[1] - median)],
        color: getMethodColor(k)
      };
    });

  // ANTT data
  const anttData = methodKeys
    .filter(k => methods[k]?.antt)
    .map(k => ({
      key: k,
      name: methods[k].label || METHOD_CONFIG[k]?.label || k,
      antt: Number((methods[k].antt?.median ?? 1).toFixed(2)),
      color: getMethodColor(k)
    }));

  // Per-repetition line chart data (10 repetitions)
  const repCount = s.repetitions || 10;
  const trialData = Array.from({ length: repCount }, (_, i) => {
    const row = { run: i + 1 };
    methodKeys.forEach(k => {
      if (rawRuns[k] && rawRuns[k][i] != null) {
        row[k] = Number(rawRuns[k][i].toFixed(3));
      }
    });
    return row;
  });

  return (
    <Page
      title="Results dashboard"
      eyebrow="ANALYSIS / MEASURED RESULTS"
      subtitle="Evaluated across 6 execution methods with Intel EMON hardware counters and repeated runs."
      actions={
        <div style={{ display: 'flex', gap: 9 }}>
          <button className="btn btn-secondary" onClick={() => jsonDownload(`${id}-results.json`, data)}>
            <Download size={15}/> Export JSON
          </button>
          <Link className="btn btn-primary" to={`/schedule/${id || '609315c9a54f4a64b733cb9ff93e5478'}`}>
            <Clock3 size={15}/> View Gantt Schedule
          </Link>
          <Link className="btn btn-secondary" to={`/output/${id || '609315c9a54f4a64b733cb9ff93e5478'}`}>
            <Terminal size={15}/> View Stdout
          </Link>
        </div>
      }
    >
      <AnalysisNavTabs id={id || '609315c9a54f4a64b733cb9ff93e5478'} activeTab="results"/>
      {/* 5 Metric Cards */}
      <div className="metric-grid">
        <MetricCard
          label="HARP-PAF makespan"
          value={fmt(s.harpMakespan)}
          unit="s"
          detail="Median runtime (dynamic schedule)"
          icon={Clock3}
        />
        <MetricCard
          label={`Speedup vs ${s.baselineName || 'Random'}`}
          value={fmt(s.speedup)}
          unit="×"
          detail={`Baseline: ${fmt(s.baselineMakespan)} s`}
          icon={Gauge}
        />
        <MetricCard
          label="Gain vs serial (no SMT)"
          value={fmt(methods.harp?.smtGainVsSerialPercent, 1)}
          unit="%"
          detail="Throughput gain vs single-thread solo"
          icon={ArrowDownRight}
        />
        <MetricCard
          label="ANTT of HARP-PAF"
          value={fmt(methods.harp?.antt?.median, 2)}
          unit=""
          detail="Average Normalized Turnaround Time"
          icon={Activity}
        />
        <MetricCard
          label="Repetitions"
          value={s.repetitions}
          unit="runs"
          detail="Trials per execution method"
          icon={Zap}
        />
      </div>

      <div className="dashboard-grid">
        {/* Makespan Chart */}
        <Card
          title="Makespan by scheduling method"
          subtitle="Median wall time across repetitions (seconds) · Lower is better · Whiskers show 95% CI"
          className="span-2"
        >
          <div className="chart-wrap chart-tall">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={makespanData} margin={{ top: 18, right: 20, bottom: 4, left: 0 }}>
                <CartesianGrid stroke="#223247" strokeDasharray="3 4" vertical={false}/>
                <XAxis dataKey="name" tick={{ fill: '#96a4bc', fontSize: 11 }} axisLine={false} tickLine={false}/>
                <YAxis unit=" s" tick={{ fill: '#8493aa', fontSize: 11 }} axisLine={false} tickLine={false}/>
                <Tooltip
                  {...chartTip}
                  formatter={(val, name, item) => [
                    `${val} s (95% CI: ${item.payload.ciLow}–${item.payload.ciHigh} s)`,
                    'Makespan'
                  ]}
                />
                <Bar dataKey="value" radius={[5, 5, 0, 0]}>
                  {makespanData.map(entry => (
                    <Cell key={entry.key} fill={entry.color}/>
                  ))}
                  <ErrorBar dataKey="ciError" width={4} strokeWidth={2} stroke="#ffffffcc" direction="y"/>
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            {makespanData.map(m => (
              <span key={m.key}>
                <i style={{ background: m.color }}/> {m.name} ({m.value} s)
              </span>
            ))}
          </div>
        </Card>

        {/* Comparison Table */}
        <Card
          title="Comparative performance vs HARP-PAF"
          subtitle="Measured speedup, confidence intervals and run superiority over 10 trials"
          className="span-2"
        >
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>METHOD</th>
                  <th>SPEEDUP</th>
                  <th>95% CONFIDENCE INTERVAL</th>
                  <th>RUNTIME REDUCTION</th>
                  <th>THROUGHPUT GAIN</th>
                  <th>HARP FASTER IN RUNS</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(comparisons).map(([key, comp]) => {
                  const ci = comp.speedupCi95 || [];
                  const ciText = ci.length === 2 ? `${ci[0].toFixed(2)}–${ci[1].toFixed(2)}` : '—';
                  return (
                    <tr key={key}>
                      <td>
                        <span className="comp-badge" style={{ background: `${getMethodColor(key)}22`, color: getMethodColor(key), border: `1px solid ${getMethodColor(key)}55` }}>
                          {comp.label || key}
                        </span>
                      </td>
                      <td><b className="speedup-pill">{comp.speedup.toFixed(2)}×</b></td>
                      <td>{ciText}</td>
                      <td>{comp.runtimeReductionPercent.toFixed(1)}%</td>
                      <td>+{comp.throughputGainPercent.toFixed(1)}%</td>
                      <td>
                        <span className="file-valid">
                          <Check size={13}/> {comp.harpFasterInRuns} / {s.repetitions} runs
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        {/* ANTT Chart */}
        <Card
          title="Average Normalized Turnaround Time (ANTT)"
          subtitle="Lower is better · OS default makes workloads wait ~4.3× solo time vs HARP-PAF 1.12×"
        >
          <div className="chart-wrap chart-tall">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={anttData} margin={{ top: 12, right: 10, bottom: 4, left: -10 }}>
                <CartesianGrid stroke="#223247" strokeDasharray="3 4" vertical={false}/>
                <XAxis dataKey="name" tick={{ fill: '#96a4bc', fontSize: 10 }} axisLine={false} tickLine={false}/>
                <YAxis unit="×" tick={{ fill: '#8493aa', fontSize: 11 }} axisLine={false} tickLine={false}/>
                <Tooltip {...chartTip} formatter={v => [`${v}× solo time`, 'ANTT']}/>
                <ReferenceLine y={1.0} stroke="#6b7a93" strokeDasharray="3 3" label={{ value: 'Solo ref (1.0)', fill: '#6b7a93', fontSize: 10 }}/>
                <Bar dataKey="antt" radius={[4, 4, 0, 0]}>
                  {anttData.map(e => (
                    <Cell key={e.key} fill={e.color}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            <span><i className="legend-cyan"/> HARP-PAF: 1.12×</span>
            <span><i style={{ background: '#e06c75' }}/> OS default: 4.32×</span>
          </div>
        </Card>

        {/* Per-repetition line chart */}
        <Card
          title="Per-repetition runtime across all trials"
          subtitle="Individual trial execution times (seconds) across all 6 evaluated methods"
        >
          <div className="chart-wrap chart-tall">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trialData} margin={{ top: 12, right: 15, bottom: 4, left: -10 }}>
                <CartesianGrid stroke="#223247" strokeDasharray="3 4"/>
                <XAxis dataKey="run" tick={{ fill: '#96a4bc', fontSize: 11 }}/>
                <YAxis unit=" s" tick={{ fill: '#8493aa', fontSize: 11 }}/>
                <Tooltip {...chartTip} formatter={v => [`${v} s`, 'Runtime']}/>
                {methodKeys.map(k => (
                  <Line
                    key={k}
                    type="monotone"
                    dataKey={k}
                    name={getMethodLabel(methods, k)}
                    stroke={getMethodColor(k)}
                    strokeWidth={k === 'harp' ? 2.5 : 1.5}
                    dot={{ r: k === 'harp' ? 3 : 2 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend" style={{ flexWrap: 'wrap' }}>
            {methodKeys.map(k => (
              <span key={k}><i style={{ background: getMethodColor(k) }}/> {getMethodLabel(methods, k)}</span>
            ))}
          </div>
        </Card>
      </div>

      {/* Code execution & verification outputs */}
      <CodeOutputViewer
        outputs={data.outputByTask}
        compilationResults={data.compilationResults}
        tasks={data.tasks}
        title="Program Execution & Verification Outputs"
        subtitle="Inspect stdout, verification status, and compiler diagnostics for each workload in this benchmark run"
      />
    </Page>
  );
}

// ==========================================
// TASK 2: SCHEDULE VIEW (GANTT CHART)
// ==========================================
function LiveSchedule() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [selectedMethod, setSelectedMethod] = useState('harp');
  const [hoveredTask, setHoveredTask] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let active = true;
    const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';
    getResults(targetId)
      .then(res => { if (active) setData(res); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [id]);

  if (error) {
    return (
      <Page title="Schedule view">
        <div className="form-error"><AlertTriangle size={16}/>{error}</div>
      </Page>
    );
  }

  if (!data) {
    return (
      <Page title="Schedule view">
        <Card title="Loading schedule"><p>Fetching timeline data...</p></Card>
      </Page>
    );
  }

  const timelines = data.timelines || {};
  const timeline = timelines[selectedMethod];
  const tasksMap = useMemo(() => {
    const map = {};
    (data.tasks || []).forEach(t => { map[t.id] = t; });
    return map;
  }, [data]);

  // Available methods in timelines
  const timelineOptions = [
    { key: 'harp', label: 'HARP-PAF (dynamic SMT co-scheduling)' },
    { key: 'port', label: 'PORT (port-contention pairing)' },
    { key: 'random', label: 'Random co-scheduling' },
    { key: 'harp_static', label: 'HARP-PAF (static pairs)' },
    { key: 'linux', label: 'OS default (OS thread scheduler)' },
    { key: 'serial', label: 'Serial (no SMT baseline)' }
  ];

  // Palette for task bars
  const TASK_PALETTE = ['#4bd6d2', '#5797ff', '#8a7cf6', '#eebc65', '#63d4a1', '#ed7c86', '#f2a65a', '#2dd4bf', '#a78bfa', '#f472b6', '#38bdf8', '#fb923c', '#4ade80', '#e879f9'];
  const getTaskBarColor = (taskId) => {
    const num = parseInt((taskId || '').replace(/\D/g, ''), 10);
    if (!isNaN(num) && num > 0) return TASK_PALETTE[(num - 1) % TASK_PALETTE.length];
    return '#4bd6d2';
  };

  const maxTime = useMemo(() => {
    if (!timeline || !timeline.length) return 3.5;
    const maxEnd = Math.max(...timeline.map(t => t.end));
    return Math.ceil(maxEnd * 10) / 10 + 0.1;
  }, [timeline]);

  const ticks = [];
  for (let t = 0; t <= maxTime; t += 0.5) {
    ticks.push(t);
  }

  return (
    <Page
      title="Hardware thread schedule"
      eyebrow="EXECUTION / GANTT TIMELINE"
      subtitle="Visualise per-hardware-thread workload dispatch on the physical SMT core."
      actions={
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <label style={{ fontSize: 11, color: '#8ea0b7' }}>
            METHOD:
            <select
              className="select"
              style={{ marginLeft: 8 }}
              value={selectedMethod}
              onChange={e => setSelectedMethod(e.target.value)}
            >
              {timelineOptions.map(opt => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
          </label>
          <Link className="btn btn-secondary" to={`/output/${id || '609315c9a54f4a64b733cb9ff93e5478'}`}>
            <Terminal size={14}/> View Stdout
          </Link>
        </div>
      }
    >
      <AnalysisNavTabs id={id || '609315c9a54f4a64b733cb9ff93e5478'} activeTab="schedule"/>
      <div className="metric-grid">
        <MetricCard
          label="Scheduling mode"
          value={selectedMethod === 'harp' ? 'Dynamic' : selectedMethod.includes('static') ? 'Static' : 'Baseline'}
          unit=""
          detail={timelineOptions.find(o => o.key === selectedMethod)?.label}
          icon={Clock3}
        />
        <MetricCard
          label="Schedule makespan"
          value={timeline && timeline.length ? `${Math.max(...timeline.map(t => t.end)).toFixed(2)}` : '—'}
          unit="s"
          detail="First repetition timeline length"
          icon={Gauge}
        />
        <MetricCard
          label="Tasks scheduled"
          value={timeline?.length || 0}
          unit="tasks"
          detail="Workloads on sibling threads"
          icon={Activity}
        />
        <MetricCard
          label="Physical core"
          value="Core 0"
          unit=""
          detail="CPUs 0 & 1 (SMT siblings)"
          icon={Cpu}
        />
      </div>

      {!timeline || timeline.length === 0 ? (
        <Card title="No Per-Thread Schedule Available">
          <div className="empty-state">
            <span className="empty-icon"><Cpu size={24}/></span>
            <h3>No per-thread schedule (the OS decides / runs one at a time)</h3>
            <p>
              {selectedMethod === 'linux'
                ? 'Under the OS default method, all workloads are submitted concurrently and the operating system kernel dispatches and preempts threads dynamically across all available logical cores.'
                : selectedMethod === 'serial'
                ? 'Under the serial baseline, each workload executes alone sequentially without any SMT co-runner.'
                : 'Timeline records are not generated for this configuration.'}
            </p>
          </div>
        </Card>
      ) : (
        <Card
          title={`Gantt Timeline: ${timelineOptions.find(o => o.key === selectedMethod)?.label}`}
          subtitle="Hover over any task bar to inspect start/end time, co-runner, and predicted slowdown"
        >
          <div className="gantt-wrap">
            {/* CPU 0 */}
            <div className="gantt-track-row">
              <div className="gantt-cpu-label">
                <Cpu size={15} color="#4bd6d2"/>
                <span>Hardware thread CPU 0</span>
              </div>
              <div className="gantt-timeline">
                {timeline.filter(t => t.cpu === 0).map(item => {
                  const leftPct = (item.start / maxTime) * 100;
                  const widthPct = ((item.end - item.start) / maxTime) * 100;
                  const taskObj = tasksMap[item.task];
                  const color = getTaskBarColor(item.task);

                  return (
                    <div
                      key={item.task}
                      className="gantt-bar-item"
                      style={{
                        left: `${leftPct}%`,
                        width: `${Math.max(widthPct, 2)}%`,
                        background: color
                      }}
                      onMouseEnter={e => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        setTooltipPos({ x: rect.left + rect.width / 2, y: rect.top - 10 });
                        setHoveredTask({ ...item, filename: taskObj?.filename || item.task });
                      }}
                      onMouseLeave={() => setHoveredTask(null)}
                    >
                      {item.task}: {taskObj?.filename ? taskObj.filename.split('.')[0] : item.task}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* CPU 1 */}
            <div className="gantt-track-row">
              <div className="gantt-cpu-label">
                <Cpu size={15} color="#8a7cf6"/>
                <span>Hardware thread CPU 1</span>
              </div>
              <div className="gantt-timeline">
                {timeline.filter(t => t.cpu === 1).map(item => {
                  const leftPct = (item.start / maxTime) * 100;
                  const widthPct = ((item.end - item.start) / maxTime) * 100;
                  const taskObj = tasksMap[item.task];
                  const color = getTaskBarColor(item.task);

                  return (
                    <div
                      key={item.task}
                      className="gantt-bar-item"
                      style={{
                        left: `${leftPct}%`,
                        width: `${Math.max(widthPct, 2)}%`,
                        background: color
                      }}
                      onMouseEnter={e => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        setTooltipPos({ x: rect.left + rect.width / 2, y: rect.top - 10 });
                        setHoveredTask({ ...item, filename: taskObj?.filename || item.task });
                      }}
                      onMouseLeave={() => setHoveredTask(null)}
                    >
                      {item.task}: {taskObj?.filename ? taskObj.filename.split('.')[0] : item.task}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* X-axis Ticks */}
            <div className="gantt-axis">
              {ticks.map(t => {
                const leftPct = (t / maxTime) * 100;
                return (
                  <span key={t} className="gantt-tick" style={{ left: `${leftPct}%` }}>
                    {t.toFixed(1)} s
                  </span>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* Floating Tooltip */}
      {hoveredTask && (
        <div className="gantt-tooltip" style={{ left: tooltipPos.x, top: tooltipPos.y, transform: 'translate(-50%, -100%)' }}>
          <b>{hoveredTask.task} — {hoveredTask.filename}</b>
          <div>Timeline: {hoveredTask.start.toFixed(2)} s → {hoveredTask.end.toFixed(2)} s ({(hoveredTask.end - hoveredTask.start).toFixed(2)} s)</div>
          <div>started next to {hoveredTask.startedWith || 'None'}, predicted slowdown +{(hoveredTask.predictedSlowdown * 100).toFixed(1)} %</div>
        </div>
      )}

      {/* Code output viewer */}
      {data && (
        <CodeOutputViewer
          outputs={data.outputByTask}
          compilationResults={data.compilationResults}
          tasks={data.tasks}
          title="Scheduled Workload Output & Verification"
          subtitle="Verification logs and runtime output for all tasks in this schedule"
        />
      )}
    </Page>
  );
}

// ==========================================
// TASK 3: PAIR ANALYSIS (LivePairAnalysis)
// ==========================================
function LivePairAnalysis() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [metricMode, setMetricMode] = useState('slowdown'); // 'slowdown' | 'cost'

  useEffect(() => {
    let active = true;
    const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';
    getResults(targetId)
      .then(res => {
        if (!active) return;
        setData(res);
        setSelected(res.pairs?.[0] || null);
      })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [id]);

  if (error) return <Page title="Pair analysis"><div className="form-error"><AlertTriangle size={16}/>{error}</div></Page>;
  if (!data) return <Page title="Pair analysis"><Card title="Loading pair analysis"><p>Fetching pair predictions...</p></Card></Page>;

  const pairs = data.pairs || [];
  const ids = Array.from(new Set(pairs.flatMap(p => [p.taskA, p.taskB]))).sort();
  const getPair = (a, b) => pairs.find(p => (p.taskA === a && p.taskB === b) || (p.taskA === b && p.taskB === a));

  const resourceFeatures = [
    ['Integer ALU ports (H_int)', 'H_int', '#58d5d1'],
    ['FP / divider (H_fp)', 'H_fp', '#8a7cf6'],
    ['Memory bandwidth (H_stream)', 'H_stream', '#63d4a1'],
    ['Cache contention (H_cache)', 'H_cache', '#eebc65'],
    ['Branch execution (H_branch)', 'H_branch', '#ed7c86']
  ];

  const tasksMap = {};
  (data.tasks || []).forEach(t => { tasksMap[t.id] = t; });

  return (
    <Page
      title="Pair analysis"
      eyebrow="ANALYSIS / SLOWDOWN PREDICTION"
      subtitle="Contention predictions across all 28 workload pairings and minimum-weight matching."
      actions={
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className={'btn ' + (metricMode === 'slowdown' ? 'btn-primary' : 'btn-secondary')}
            onClick={() => setMetricMode('slowdown')}
          >
            Show Predicted Slowdown (%)
          </button>
          <button
            className={'btn ' + (metricMode === 'cost' ? 'btn-primary' : 'btn-secondary')}
            onClick={() => setMetricMode('cost')}
          >
            Show Pair Cost
          </button>
        </div>
      }
    >
      <AnalysisNavTabs id={id || '609315c9a54f4a64b733cb9ff93e5478'} activeTab="pairs"/>
      <div className="pair-layout">
        {/* Heatmap Card */}
        <Card
          title={`Task pair heatmap (${metricMode === 'slowdown' ? 'Predicted Slowdown %' : 'Final Pair Cost'})`}
          subtitle="Click any cell to inspect resource contention and solo times"
          className="heatmap-card"
        >
          <div className="heatmap-wrap">
            <div className="heatmap-grid" style={{ gridTemplateColumns: `36px repeat(${ids.length}, minmax(44px, 58px))` }}>
              <span className="heatmap-axis empty"/>
              {ids.map(t => <span className="heatmap-axis" key={t}>{t}</span>)}
              {ids.map(row => (
                <React.Fragment key={row}>
                  <span className="heatmap-axis row-axis">{row}</span>
                  {ids.map(col => {
                    const p = row === col ? null : getPair(row, col);
                    const val = p
                      ? metricMode === 'slowdown'
                        ? `+${(p.predictedSlowdown * 100).toFixed(0)}%`
                        : p.finalPairCost.toFixed(2)
                      : '—';
                    const isSelected = selected && p && ((selected.taskA === row && selected.taskB === col) || (selected.taskA === col && selected.taskB === row));

                    // Heat intensity color
                    const slowdown = p?.predictedSlowdown || 0;
                    const bgIntensity = p
                      ? slowdown > 0.45
                        ? '#3b2533'
                        : slowdown > 0.25
                        ? '#223242'
                        : '#142735'
                      : '#0d1624';

                    return (
                      <button
                        key={col}
                        className={'heat-cell ' + (!p ? 'diagonal' : '') + (isSelected ? ' chosen' : '')}
                        disabled={!p}
                        style={p ? { background: bgIntensity } : {}}
                        onClick={() => setSelected(p)}
                        title={p ? `${row} + ${col}: Slowdown +${(p.predictedSlowdown * 100).toFixed(1)}%, Cost: ${p.finalPairCost.toFixed(3)}` : 'Same task'}
                      >
                        {val}
                      </button>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
            <p className="heat-help">Color intensity indicates predicted slowdown magnitude.</p>
          </div>
        </Card>

        {/* Pair Details Card */}
        <Card
          title="Pair contention details"
          subtitle={selected ? `${selected.taskA} (${tasksMap[selected.taskA]?.filename || ''}) + ${selected.taskB} (${tasksMap[selected.taskB]?.filename || ''})` : 'Select a pair'}
          className="pair-detail"
        >
          {selected && (
            <>
              <div className="pair-highlight">
                <span className="pair-nodes">
                  <b>{selected.taskA}</b><span>↔</span><b>{selected.taskB}</b>
                </span>
                <span style={{ fontSize: 11, color: '#88d8d3' }}>
                  Predicted Pair Time: <b>{selected.predictedPairSeconds?.toFixed(2)} s</b>
                </span>
              </div>

              <div className="pair-metrics">
                <div>
                  <small>PREDICTED SLOWDOWN</small>
                  <b style={{ color: '#4bd6d2' }}>+{(selected.predictedSlowdown * 100).toFixed(1)}%</b>
                </div>
                <div>
                  <small>WORST TASK SLOWDOWN</small>
                  <b>+{(selected.predictedWorstSlowdown * 100).toFixed(1)}%</b>
                </div>
                <div>
                  <small>UNCERTAINTY</small>
                  <b>±{(selected.uncertainty * 100).toFixed(1)}%</b>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, margin: '12px 0', padding: '8px 0', borderBottom: '1px solid #223247' }}>
                <div><small style={{ color: '#8192a8', fontSize: 10 }}>Task A Solo Time:</small> <b style={{ color: '#d8e4f2', fontSize: 11 }}>{selected.soloSeconds?.[0]?.toFixed(2)} s</b></div>
                <div><small style={{ color: '#8192a8', fontSize: 10 }}>Task B Solo Time:</small> <b style={{ color: '#d8e4f2', fontSize: 11 }}>{selected.soloSeconds?.[1]?.toFixed(2)} s</b></div>
                <div><small style={{ color: '#8192a8', fontSize: 10 }}>Final Pair Cost:</small> <b style={{ color: '#d8e4f2', fontSize: 11 }}>{selected.finalPairCost?.toFixed(4)}</b></div>
                <div><small style={{ color: '#8192a8', fontSize: 10 }}>Combined Contention H:</small> <b style={{ color: '#d8e4f2', fontSize: 11 }}>{selected.features?.H?.toFixed(3)}</b></div>
              </div>

              <div className="feature-bars">
                <div style={{ fontSize: 10, color: '#8291a7', marginBottom: 4, fontWeight: 600 }}>RESOURCE CONTENTION CONTRIBUTIONS</div>
                {resourceFeatures.map(([label, key, color]) => {
                  const val = selected.contributions?.[key] ?? 0;
                  return (
                    <div className="feature-bar-row" key={key} style={{ gridTemplateColumns: '160px 1fr 45px' }}>
                      <span className="feature-label">{label}</span>
                      <div className="feature-track">
                        <i style={{ width: `${Math.min(100, (val / 0.3) * 100)}%`, background: color }}/>
                      </div>
                      <b>{val.toFixed(3)}</b>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Side-by-side Pairs Selection Card */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 18 }}>
        <Card title="HARP-PAF Static Selected Pairs" subtitle="Pairs chosen by minimum-weight matching of model costs">
          <div className="selected-pair-grid" style={{ gridTemplateColumns: '1fr' }}>
            {(data.selectedPairs || []).map((p, i) => {
              const pairObj = getPair(p[0], p[1]);
              return (
                <div
                  key={i}
                  className={'selected-pair-card ' + (selected === pairObj ? 'selected' : '')}
                  onClick={() => pairObj && setSelected(pairObj)}
                >
                  <span className="selected-pair-top">
                    <span>PAIR {i + 1}</span>
                    <ChevronRight size={15}/>
                  </span>
                  <span className="selected-pair-names">
                    <b>{p[0]} ({tasksMap[p[0]]?.filename || ''})</b>
                    <span>+</span>
                    <b>{p[1]} ({tasksMap[p[1]]?.filename || ''})</b>
                  </span>
                  <span className="selected-pair-bottom">
                    <span>Predicted slowdown: <b>+{((pairObj?.predictedSlowdown || 0) * 100).toFixed(1)}%</b></span>
                    <span>Pair cost: <b>{pairObj?.finalPairCost?.toFixed(3)}</b></span>
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="PORT Selected Pairs" subtitle="Pairs chosen by execution-port contention heuristic">
          <div className="selected-pair-grid" style={{ gridTemplateColumns: '1fr' }}>
            {(data.portPairs || []).map((p, i) => {
              const pairObj = getPair(p[0], p[1]);
              return (
                <div
                  key={i}
                  className={'selected-pair-card ' + (selected === pairObj ? 'selected' : '')}
                  onClick={() => pairObj && setSelected(pairObj)}
                >
                  <span className="selected-pair-top">
                    <span>PORT PAIR {i + 1}</span>
                    <ChevronRight size={15}/>
                  </span>
                  <span className="selected-pair-names">
                    <b>{p[0]} ({tasksMap[p[0]]?.filename || ''})</b>
                    <span>+</span>
                    <b>{p[1]} ({tasksMap[p[1]]?.filename || ''})</b>
                  </span>
                  <span className="selected-pair-bottom">
                    <span>Predicted slowdown: <b>+{((pairObj?.predictedSlowdown || 0) * 100).toFixed(1)}%</b></span>
                    <span>Pair cost: <b>{pairObj?.finalPairCost?.toFixed(3)}</b></span>
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Top Matchings Card */}
      <Card
        title="Top 10 Complete Matchings"
        subtitle={`Showing top 10 out of ${data.matchingsEvaluated || 105} total evaluated matchings · Ranked by total predicted cost`}
        style={{ marginTop: 18 }}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>RANK</th>
                <th>MATCHING PLAN</th>
                <th>PAIRINGS</th>
                <th>TOTAL PAIR COST</th>
              </tr>
            </thead>
            <tbody>
              {(data.allMatchings || []).slice(0, 10).map((m, idx) => (
                <tr key={m.matching || idx}>
                  <td><b>#{idx + 1}</b></td>
                  <td><span className="task-id">{m.matching}</span></td>
                  <td>{m.pairs.map(p => `${p[0]}+${p[1]}`).join('  |  ')}</td>
                  <td><b style={{ color: idx === 0 ? '#4bd6d2' : '#cbd5e1' }}>{m.totalCost.toFixed(4)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}

// ==========================================
// TASK 4: TASK METRICS (LiveTaskMetrics)
// ==========================================
function LiveTaskMetrics() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [selectedTask, setSelectedTask] = useState(null);

  useEffect(() => {
    let active = true;
    const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';
    getResults(targetId)
      .then(res => {
        if (!active) return;
        setData(res);
        setSelectedTask(res.tasks?.[0] || null);
      })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [id]);

  if (error) return <Page title="Task metrics"><div className="form-error"><AlertTriangle size={16}/>{error}</div></Page>;
  if (!data) return <Page title="Task metrics"><Card title="Loading task metrics"><p>Fetching task telemetry...</p></Card></Page>;

  const tasks = data.tasks || [];

  const download = () => csvDownload(
    `${id}-task-metrics.csv`,
    tasks.map(t => ({
      taskId: t.id,
      filename: t.filename,
      soloSeconds: t.solo,
      coRunSeconds: t.coRun,
      slowdownPercent: t.slowdown ? (t.slowdown * 100).toFixed(2) : '',
      ipc: t.ipc,
      instructions: t.instructions,
      cycles: t.cycles,
      cacheMisses: t.cacheMisses,
      branchMisses: t.branchMisses
    }))
  );

  // Radar/bar data for stressor sensitivity
  const sensitivityData = selectedTask?.sensitivity ? [
    { subject: 'Integer ALU', value: Number((selectedTask.sensitivity.int ?? 0).toFixed(2)) },
    { subject: 'Scalar FP', value: Number((selectedTask.sensitivity.fp ?? 0).toFixed(2)) },
    { subject: 'Memory Stream', value: Number((selectedTask.sensitivity.stream ?? 0).toFixed(2)) },
    { subject: 'Cache', value: Number((selectedTask.sensitivity.cache ?? 0).toFixed(2)) },
    { subject: 'Branch Heavy', value: Number((selectedTask.sensitivity.branch ?? 0).toFixed(2)) }
  ] : [];

  // Instruction mix pie data
  const instructionMix = selectedTask?.staticProfile?.instructionMix || {};
  const mixPieData = [
    { name: 'Integer ALU', value: Number((instructionMix.int_alu || 0).toFixed(3)), fill: '#4bd6d2' },
    { name: 'Multiply / Divide', value: Number((instructionMix.mul_div || 0).toFixed(3)), fill: '#8a7cf6' },
    { name: 'FP & SIMD', value: Number((instructionMix.fp_simd || 0).toFixed(3)), fill: '#eebc65' },
    { name: 'Load / Store', value: Number((instructionMix.load_store || 0).toFixed(3)), fill: '#63d4a1' },
    { name: 'Branch', value: Number((instructionMix.branch || 0).toFixed(3)), fill: '#ed7c86' }
  ].filter(d => d.value > 0);

  const phaseColors = ['#4bd6d2', '#8a7cf6', '#eebc65', '#63d4a1'];

  return (
    <Page
      title="Task metrics"
      eyebrow="ANALYSIS / WORKLOAD PROFILES"
      subtitle="Measured solo/co-run execution times, IPC, hardware counters, and sensitivity probes."
      actions={
        <button className="btn btn-secondary" onClick={download}>
          <Download size={15}/> Export CSV
        </button>
      }
    >
      <AnalysisNavTabs id={id || '609315c9a54f4a64b733cb9ff93e5478'} activeTab="tasks"/>
      {/* Task Profile Table */}
      <Card title="Task Profile Table" subtitle="All 8 workloads measured on hardware · Click any row to inspect sensitivity & phase timeline">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>TASK ID</th>
                <th>FILENAME</th>
                <th>SOLO TIME</th>
                <th>CO-RUN TIME</th>
                <th>SLOWDOWN</th>
                <th>IPC</th>
                <th>INSTRUCTIONS</th>
                <th>CYCLES</th>
                <th>CACHE MISSES</th>
                <th>BRANCH MISSES</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map(t => {
                const isSelected = selectedTask?.id === t.id;
                return (
                  <tr
                    key={t.id}
                    className={'click-row ' + (isSelected ? 'chosen' : '')}
                    onClick={() => setSelectedTask(t)}
                    style={isSelected ? { background: '#132130' } : {}}
                  >
                    <td><span className="task-id">{t.id}</span></td>
                    <td><b>{t.filename}</b></td>
                    <td>{fmtSec(t.solo)}</td>
                    <td>{fmtSec(t.coRun)}</td>
                    <td><b style={{ color: t.slowdown > 0.3 ? '#f2a65a' : '#57d6d1' }}>{fmtPct(t.slowdown)}</b></td>
                    <td><span className="task-id" style={{ background: '#1c283c', color: '#90b4ff', border: '1px solid #324765' }}>{t.ipc ? t.ipc.toFixed(2) : '—'}</span></td>
                    <td>{t.instructions ? t.instructions.toLocaleString() : '—'}</td>
                    <td>{t.cycles ? t.cycles.toLocaleString() : '—'}</td>
                    <td>{t.cacheMisses ? t.cacheMisses.toLocaleString() : '—'}</td>
                    <td>{t.branchMisses ? t.branchMisses.toLocaleString() : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Selected Task Detailed Diagnostics */}
      {selectedTask && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 18 }}>
          {/* Sensitivity Chart */}
          <Card
            title={`Interference Sensitivity: ${selectedTask.id} (${selectedTask.filename})`}
            subtitle="Slowdown factor when co-running against 5 resource-specific stressor kernels"
          >
            <div className="chart-wrap" style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sensitivityData} margin={{ top: 10, right: 10, bottom: 4, left: -10 }}>
                  <CartesianGrid stroke="#223247" strokeDasharray="3 4" vertical={false}/>
                  <XAxis dataKey="subject" tick={{ fill: '#96a4bc', fontSize: 10 }} axisLine={false} tickLine={false}/>
                  <YAxis tick={{ fill: '#8493aa', fontSize: 11 }} axisLine={false} tickLine={false}/>
                  <Tooltip {...chartTip} formatter={v => [`${v}× slowdown`, 'Sensitivity']}/>
                  <Bar dataKey="value" fill="#8a7cf6" radius={[4, 4, 0, 0]}>
                    {sensitivityData.map((e, idx) => (
                      <Cell key={idx} fill={e.value > 1.0 ? '#eebc65' : '#4bd6d2'}/>
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-legend">
              <span><i style={{ background: '#4bd6d2' }}/> Low/moderate interference (&le; 1.0)</span>
              <span><i style={{ background: '#eebc65' }}/> Severe interference (&gt; 1.0)</span>
            </div>
          </Card>

          {/* Static Instruction Mix Pie */}
          <Card
            title={`Static Instruction Mix: ${selectedTask.id}`}
            subtitle="Extracted via objdump disassembly with loop weighting"
          >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 150px', alignItems: 'center' }}>
              <div className="chart-wrap" style={{ height: 210 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={mixPieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={3}
                    >
                      {mixPieData.map((e, i) => (
                        <Cell key={i} fill={e.fill}/>
                      ))}
                    </Pie>
                    <Tooltip {...chartTip} formatter={v => [`${(v * 100).toFixed(1)}%`, 'Share']}/>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div style={{ fontSize: 10, color: '#93a4bc', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {mixPieData.map(m => (
                  <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <i style={{ width: 8, height: 8, borderRadius: 2, background: m.fill }}/>
                    <span>{m.name}: <b>{(m.value * 100).toFixed(1)}%</b></span>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Phase Timeline */}
          <Card
            title={`Phase Segments: ${selectedTask.id}`}
            subtitle={`${selectedTask.phases?.length || 1} distinct execution phases across runtime`}
            className="span-2"
          >
            <div className="phase-segment-bar">
              {(selectedTask.phaseSegments || []).map((seg, i) => {
                const widthPct = ((seg.end - seg.start) * 100).toFixed(1);
                const color = phaseColors[seg.phase % phaseColors.length];
                return (
                  <div
                    key={i}
                    className="phase-segment-slice"
                    style={{ width: `${widthPct}%`, background: color }}
                    title={`Phase ${seg.phase}: ${(seg.start * 100).toFixed(0)}% – ${(seg.end * 100).toFixed(0)}%`}
                  >
                    Phase {seg.phase} ({widthPct}%)
                  </div>
                );
              })}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#7a8ba3', marginTop: 4 }}>
              <span>0% Start of Execution</span>
              <span>Mean Confidence: {selectedTask.meanConfidence ? (selectedTask.meanConfidence * 100).toFixed(1) + '%' : '—'}</span>
              <span>100% Completion</span>
            </div>
          </Card>
        </div>
      )}

      {/* Task Telemetry & Execution Output */}
      {data && (
        <CodeOutputViewer
          outputs={data.outputByTask}
          compilationResults={data.compilationResults}
          tasks={data.tasks}
          title="Workload Telemetry & Execution Output"
          subtitle="Inspect program standard output, verification status, and compiler diagnostics for each task"
        />
      )}
    </Page>
  );
}

// ==========================================
// TASK 5: PREDICTION ANALYSIS (LivePredictionAnalysis)
// ==========================================
function LivePredictionAnalysis() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';
    getResults(targetId)
      .then(res => { if (active) setData(res); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [id]);

  if (error) return <Page title="Prediction analysis"><div className="form-error"><AlertTriangle size={16}/>{error}</div></Page>;
  if (!data) return <Page title="Prediction analysis"><Card title="Loading model"><p>Fetching model data...</p></Card></Page>;

  const model = data.model || {};
  const prediction = data.prediction || {};
  const points = (prediction.points || []).map((pt, i) => ({
    id: `Pair ${i + 1}`,
    predictedPairSeconds: Number((pt.predictedPairSeconds ?? 0).toFixed(3)),
    measuredPairSeconds: Number((pt.measuredPairSeconds ?? 0).toFixed(3)),
    predictedSlowdown: Number((pt.predicted ?? 0).toFixed(3)),
    measuredSlowdown: Number((pt.measured ?? 0).toFixed(3))
  }));

  return (
    <Page
      title="Prediction analysis"
      eyebrow="EVALUATION / CALIBRATED SLOWDOWN MODEL"
      subtitle="Evaluation of the calibrated bottleneck sensitivity × aggressiveness model."
      actions={<span className="job-id-chip">{id}</span>}
    >
      <AnalysisNavTabs id={id || '609315c9a54f4a64b733cb9ff93e5478'} activeTab="predictions"/>
      {/* 5 Model Metric Cards */}
      <div className="metric-grid">
        <MetricCard
          label="Model architecture"
          value="Sensitivity × Aggr."
          unit=""
          detail={`Status: ${model.source || 'calibrated'}`}
          icon={Gauge}
        />
        <MetricCard
          label="Held-out error (MAE)"
          value={fmt(model.heldOutMae, 3)}
          unit=""
          detail="On held-out validation pairs"
          icon={Activity}
        />
        <MetricCard
          label="Training error (MAE)"
          value={fmt(model.trainingMae, 3)}
          unit=""
          detail="On calibrated pairs"
          icon={Check}
        />
        <MetricCard
          label="Calibration samples"
          value={model.sampleCount ?? 55}
          unit="pairs"
          detail="Measured calibration co-runs"
          icon={GitBranch}
        />
        <MetricCard
          label="Fitted coefficients"
          value={`b0=${fmt(model.coefficients?.intercept, 3)}`}
          unit=""
          detail={`Slope b=${fmt(model.coefficients?.H, 3)}`}
          icon={Layers3}
        />
      </div>

      <div className="dashboard-grid">
        {/* Model Comparison Table */}
        <Card
          title="Slowdown Model Accuracy Comparison"
          subtitle="Held-out accuracy comparison against previous equations and baseline heuristics"
        >
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>MODEL FORMULATION</th>
                  <th>HELD-OUT MAE</th>
                  <th>RANK CORRELATION (SPEARMAN)</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Always-average baseline (guess mean)</td>
                  <td>0.133</td>
                  <td>—</td>
                  <td><span className="status status-neutral">Baseline</span></td>
                </tr>
                <tr>
                  <td>Original Equations 1–8 (uncalibrated)</td>
                  <td>0.129</td>
                  <td>0.33</td>
                  <td><span className="status status-error">Deprecated</span></td>
                </tr>
                <tr style={{ background: '#122530' }}>
                  <td><b style={{ color: '#4bd6d2' }}>Bottleneck sensitivity × aggressiveness (calibrated)</b></td>
                  <td><b style={{ color: '#4bd6d2' }}>0.069</b></td>
                  <td><b style={{ color: '#4bd6d2' }}>0.84</b></td>
                  <td><span className="status status-success"><Check size={12}/> Calibrated</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="job-footnote">
            The bottleneck sensitivity × aggressiveness model cuts held-out error almost in half compared with Equations 1–8 and raises rank correlation from 0.33 to 0.84.
          </p>
        </Card>

        {/* Scatter plot */}
        <Card
          title="Predicted vs Measured Pair Execution Time"
          subtitle="Observed co-run pairs in benchmark experiment · Note: only 4 static pairs observed per trial"
        >
          <div className="chart-wrap chart-tall">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 12, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid stroke="#223247" strokeDasharray="3 4"/>
                <XAxis dataKey="predictedPairSeconds" name="Predicted" unit=" s" tick={{ fill: '#96a4bc', fontSize: 11 }} label={{ value: 'Predicted (s)', position: 'insideBottom', offset: -5, fill: '#8493aa', fontSize: 10 }}/>
                <YAxis dataKey="measuredPairSeconds" name="Measured" unit=" s" tick={{ fill: '#8493aa', fontSize: 11 }} label={{ value: 'Measured (s)', angle: -90, position: 'insideLeft', fill: '#8493aa', fontSize: 10 }}/>
                <Tooltip {...chartTip} cursor={{ strokeDasharray: '3 3' }}/>
                <ReferenceLine x={0.7} y={0.7} stroke="#4bd6d2" strokeDasharray="3 3"/>
                <Scatter name="Observed Pairs" data={points} fill="#4bd6d2"/>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            <span><i className="legend-cyan"/> Observed static pair co-runs (N={points.length})</span>
          </div>
        </Card>
      </div>
    </Page>
  );
}

// ==========================================
// TASK 7: SYSTEM INFORMATION (SystemInfo)
// ==========================================
function SystemInfo() {
  const [system, setSystem] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getSystem()
      .then(data => { if (active) setSystem(data); })
      .catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) {
    return (
      <Page title="System information">
        <Card title="Loading environment details"><p>Fetching hardware and system topology...</p></Card>
      </Page>
    );
  }

  if (error) {
    return (
      <Page title="System information">
        <div className="form-error"><AlertTriangle size={16}/>{error}</div>
      </Page>
    );
  }

  const cores = system.cores || [];
  const activeCpuPair = system.taskCpuPairs?.[0] || [0, 1];
  const harnessCpu = system.harnessCpu ?? 11;

  const rows = [
    ['CPU Model', system.cpuModel],
    ['Counter Tool & Status', `${system.counterTool?.toUpperCase() || 'EMON'} (${system.hardwareCountersAvailable ? 'Available' : 'Unavailable'})`],
    ['Counter Details / Reason', system.counterUnavailableReason || 'Hardware counters available'],
    ['Profiling Mode', system.profilingMode || 'probe'],
    ['Slowdown Model', `Bottleneck sensitivity × aggressiveness (${system.model?.source || 'calibrated'}, held-out MAE: ${system.model?.heldOutMae ?? '0.069'})`],
    ['Optimization Objective', system.objective || 'makespan'],
    ['SMT Cores Utilized', `${system.smtCoresUsed || 1} physical core (2 sibling threads)`],
    ['GCC Compiler', system.compilerGcc || 'Unavailable'],
    ['G++ Compiler', system.compilerGpp || 'Unavailable'],
    ['Operating System', `${system.operatingSystem} (${system.executionEnvironment || 'Windows / Linux'})`],
    ['SMT Sibling Verification', system.verifiedSmtSiblingMapping ? 'Verified hardware siblings' : 'Virtual / unverified']
  ];

  return (
    <Page
      title="System information"
      eyebrow="ENVIRONMENT / HARDWARE TOPOLOGY"
      subtitle="Physical CPU topology, hybrid core architecture, and measurement tool configuration."
    >
      <div className="system-grid">
        {/* Core Map Card */}
        <Card
          title="Physical CPU Core Map"
          subtitle={`12 logical CPUs across 10 physical cores · Active SMT pair and harness CPU highlighted`}
          className="span-2"
        >
          <div className="core-map-grid">
            {cores.map((c, i) => {
              const isP = c.efficiencyClass === 1;
              const isActiveSMT = c.cpus.some(id => activeCpuPair.includes(id));
              const isHarness = c.cpus.includes(harnessCpu);

              return (
                <div
                  key={i}
                  className={
                    'core-box-card ' +
                    (isActiveSMT ? 'active-smt ' : '') +
                    (isHarness ? 'harness-core' : '')
                  }
                >
                  <div className="core-box-head">
                    <b>Core {i}</b>
                    <span className={'core-box-type ' + (isP ? 'p-core-badge' : 'e-core-badge')}>
                      {isP ? 'P-Core (SMT)' : 'E-Core'}
                    </span>
                  </div>
                  <div className="core-cpus-list">
                    {c.cpus.map(cpuId => (
                      <span key={cpuId} className="core-cpu-pill">
                        CPU {cpuId}
                      </span>
                    ))}
                  </div>
                  {isActiveSMT && (
                    <span className="core-badge-tag tag-smt">
                      <Zap size={11}/> Active SMT Core
                    </span>
                  )}
                  {isHarness && (
                    <span className="core-badge-tag tag-harness">
                      <Server size={11}/> Harness CPU
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          <div className="chart-legend" style={{ marginTop: 16 }}>
            <span><i className="legend-cyan"/> Active SMT Core: CPUs {activeCpuPair.join(', ')}</span>
            <span><i style={{ background: '#ba9cfc' }}/> Harness CPU: {harnessCpu}</span>
            <span><i style={{ background: '#54d5d0' }}/> P-Core (Efficiency class 1)</span>
            <span><i style={{ background: '#8fa0ba' }}/> E-Core (Efficiency class 0)</span>
          </div>
        </Card>

        {/* Environment Details Card */}
        <Card title="Execution Environment" subtitle="System details reported by FastAPI backend" className="span-2">
          <div className="system-info-list">
            {rows.map(([label, value]) => (
              <div key={label}>
                <span className="system-info-icon"><Cpu size={15}/></span>
                <span>{label}</span>
                <b>{String(value)}</b>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </Page>
  );
}

// ==========================================
// TASK 8: HISTORY
// ==========================================
function History() {
  const [query, setQuery] = useState('');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function loadJobs() {
      try {
        const response = await listJobs();
        if (!active) return;
        setJobs(response || []);
        setError('');
      } catch (err) {
        if (!active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadJobs();
    return () => { active = false; };
  }, []);

  const filtered = jobs.filter(job =>
    [job.jobId, ...(job.filenames || []), job.status].join(' ').toLowerCase().includes(query.toLowerCase())
  );

  return (
    <Page
      title="History & reports"
      eyebrow="WORKSPACE / JOB HISTORY"
      subtitle="Previously benchmarked jobs saved by the HARP-PAF backend."
      actions={
        <Link className="btn btn-primary" to="/upload">
          <Plus size={16}/> New analysis
        </Link>
      }
    >
      {error && <div className="form-error"><AlertTriangle size={16}/>{error}</div>}

      <Card title="Analysis Jobs" subtitle={`${jobs.length} saved benchmark jobs`}>
        <div className="table-toolbar">
          <label className="search-field">
            <Search size={16}/>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search job ID or workload filename"
              aria-label="Search jobs"
            />
          </label>
          <span className="result-count">Showing {filtered.length} of {jobs.length}</span>
        </div>

        {loading ? (
          <div className="empty-inline centered">Loading saved jobs...</div>
        ) : filtered.length ? (
          <div className="table-scroll">
            <table className="data-table history-table">
              <thead>
                <tr>
                  <th>JOB ID</th>
                  <th>WORKLOAD FILES</th>
                  <th>STATUS</th>
                  <th>BASELINE</th>
                  <th>MAKESPAN</th>
                  <th>SPEEDUP</th>
                  <th>SUBMITTED</th>
                  <th>REPORTS</th>
                  <th/>
                </tr>
              </thead>
              <tbody>
                {filtered.map(job => (
                  <tr key={job.jobId}>
                    <td>
                      <Link to={`/results/${job.jobId}`} className="job-link">
                        {job.jobId.slice(0, 12)}...
                      </Link>
                    </td>
                    <td>{(job.filenames || []).join(', ')}</td>
                    <td>
                      <Status tone={job.status === 'completed' ? 'success' : job.status === 'failed' ? 'error' : 'info'}>
                        {job.status}
                      </Status>
                    </td>
                    <td><span className="comp-badge" style={{ background: '#252033', color: '#f2a65a' }}>{job.baselineName || 'Random'}</span></td>
                    <td><b>{fmtSec(job.selectedMakespan)}</b></td>
                    <td><b className="speedup-pill">{job.speedup ? `${job.speedup.toFixed(2)}×` : '—'}</b></td>
                    <td>{job.createdAt ? new Date(job.createdAt).toLocaleString() : 'Unavailable'}</td>
                    <td>
                      <div className="report-actions">
                        <button
                          onClick={() => csvDownload(`${job.jobId}.csv`, [{
                            jobId: job.jobId,
                            status: job.status,
                            baselineName: job.baselineName || 'Random',
                            makespanSeconds: job.selectedMakespan,
                            speedup: job.speedup
                          }])}
                          title="Download summary CSV"
                        >
                          <Download size={14}/> CSV
                        </button>
                        <button
                          onClick={() => jsonDownload(`${job.jobId}-summary.json`, job)}
                          title="Download summary JSON"
                        >
                          <Download size={14}/> JSON
                        </button>
                      </div>
                    </td>
                    <td>
                      <Link to={`/results/${job.jobId}`} className="icon-btn" aria-label="Open job">
                        <ChevronRight size={16}/>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-inline centered">No matching jobs found.</div>
        )}
      </Card>
    </Page>
  );
}

function NotFound() {
  return (
    <Page title="Page not found" eyebrow="404">
      <div className="empty-state">
        <h2>This page isn’t available</h2>
        <p>Use the workspace navigation to return to an analysis page.</p>
        <Link className="btn btn-primary" to="/">Go to home</Link>
      </div>
    </Page>
  );
}

// ==========================================
// CODE & STDOUT VIEW
// ==========================================
function LiveCodeOutput() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';
    getResults(targetId)
      .then(res => { if (active) setData(res); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [id]);

  const targetId = id || '609315c9a54f4a64b733cb9ff93e5478';

  return (
    <Page
      title="Code execution & standard output"
      eyebrow="EXECUTION / WORKLOAD STDOUT"
      subtitle="Inspect standard output (stdout), stderr, checksum verification, and compiler diagnostics."
      actions={
        <div style={{ display: 'flex', gap: 10 }}>
          <Link className="btn btn-primary" to={`/schedule/${targetId}`}>
            <Clock3 size={15}/> View Schedule
          </Link>
          <Link className="btn btn-secondary" to={`/results/${targetId}`}>
            <BarChart3 size={15}/> View Results Dashboard
          </Link>
        </div>
      }
    >
      <AnalysisNavTabs id={targetId} activeTab="output"/>

      {error && <div className="form-error"><AlertTriangle size={16}/>{error}</div>}

      <CodeOutputViewer
        outputs={data?.outputByTask}
        compilationResults={data?.compilationResults}
        tasks={data?.tasks}
        title="Workload Standard Output (stdout) & Diagnostics"
        subtitle="Full console stream, loop completion logs, and checksums for all submitted programs"
      />
    </Page>
  );
}

// ==========================================
// MAIN APP ROUTER
// ==========================================
export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Home/>}/>
        <Route path="/upload" element={<UploadCode/>}/>
        <Route path="/jobs/:id" element={<JobProgress/>}/>
        <Route path="/results" element={<LatestJobRedirect destination="results"/>}/>
        <Route path="/results/:id" element={<LiveResults/>}/>
        <Route path="/schedule" element={<LatestJobRedirect destination="schedule"/>}/>
        <Route path="/schedule/:id" element={<LiveSchedule/>}/>
        <Route path="/output" element={<LatestJobRedirect destination="output"/>}/>
        <Route path="/output/:id" element={<LiveCodeOutput/>}/>
        <Route path="/pairs" element={<LatestJobRedirect destination="pairs"/>}/>
        <Route path="/pairs/:id" element={<LivePairAnalysis/>}/>
        <Route path="/tasks" element={<LatestJobRedirect destination="tasks"/>}/>
        <Route path="/tasks/:id" element={<LiveTaskMetrics/>}/>
        <Route path="/predictions" element={<LatestJobRedirect destination="predictions"/>}/>
        <Route path="/predictions/:id" element={<LivePredictionAnalysis/>}/>
        <Route path="/history" element={<History/>}/>
        <Route path="/system" element={<SystemInfo/>}/>
        <Route path="*" element={<NotFound/>}/>
      </Routes>
    </AppLayout>
  );
}

