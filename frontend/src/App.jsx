import { getSystem } from './services/api.js';
import LatestJobRedirect from './LatestJobRedirect.jsx';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, NavLink, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { Activity, ArrowDownRight, ArrowRight, BarChart3, Check, ChevronDown, ChevronRight, CircleHelp, Clock3, Cpu, Download, FileCode2, FileText, Gauge, GitBranch, History as HistoryIcon, Home as HomeIcon, Layers3, Menu, Microscope, Network, Plus, Search, Server, ShieldCheck, Sparkles, Upload, X, AlertTriangle, PanelLeftClose } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ErrorBar, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';
import { createDemoJob, csvDownload, getDashboardData, getJob, getJobs, getPairData, getPredictions, getRunDistribution, jsonDownload } from './services/dataProvider.js';
import {
  createJob,
  getJob as getLiveJob,
  getResults,
  listJobs
} from './services/api.js';
const nav = [
  {to:'/',label:'Home',icon:HomeIcon,end:true}, {to:'/upload',label:'New analysis',icon:Plus},
  {section:'Workspace'}, {to:'/results',label:'Results dashboard',icon:BarChart3}, {to:'/pairs',label:'Pair analysis',icon:Network},
  {to:'/tasks',label:'Task metrics',icon:Activity}, {to:'/predictions',label:'Prediction analysis',icon:Gauge},
  {section:'Manage'}, {to:'/history',label:'History & reports',icon:HistoryIcon}, {to:'/system',label:'System information',icon:Server}
];
function Brand({compact=false}) { return <Link to="/" className={'brand '+(compact?'brand-compact':'')}><span className="brand-mark"><Cpu size={20}/><i/></span><span><b>HARP<span className="brand-accent">·</span>PAF</b><small>RESEARCH PLATFORM</small></span></Link>; }
function Sidebar({open,onClose}) { return <><div className={'sidebar-scrim '+(open?'show':'')} onClick={onClose}/><aside className={'sidebar '+(open?'sidebar-open':'')}><div className="sidebar-top"><Brand/><button className="icon-btn mobile-close" onClick={onClose} aria-label="Close navigation"><X size={17}/></button></div><div className="workspace-switch"><span className="workspace-icon"><Microscope size={16}/></span><span><b>HARP-PAF Lab</b><small>Research workspace</small></span><ChevronDown size={14}/></div><nav aria-label="Main navigation">{nav.map((item,i)=>item.section?<div className="nav-section" key={i}>{item.section}</div>:<NavLink key={item.to} to={item.to} end={item.end} onClick={onClose} className={({isActive})=>'nav-link '+(isActive?'active':'')}><item.icon size={17}/><span>{item.label}</span>{item.to==='/upload'&&<span className="nav-new">NEW</span>}</NavLink>)}</nav><div className="sidebar-bottom"><div className="system-health"><span className="health-dot"/><div><b>Local WSL environment</b><small>FastAPI integration enabled</small></div></div><button className="help-link" onClick={()=>window.alert('HARP-PAF frontend demo. Metrics shown in this workspace are illustrative.') }><CircleHelp size={16}/> Help & documentation <ArrowRight size={14}/></button><div className="sidebar-user"><div className="avatar">RL</div><div><b>Research Lab</b><small>Local research prototype</small></div><ChevronDown size={15}/></div></div></aside></>; }
function AppLayout({children}) { const [open,setOpen]=useState(false);return <div className="app-shell"><Sidebar open={open} onClose={()=>setOpen(false)}/><main className="main-shell"><header className="topbar"><button className="icon-btn mobile-menu" aria-label="Open navigation" onClick={()=>setOpen(true)}><Menu size={19}/></button><div className="breadcrumb"><span>HARP-PAF</span><ChevronRight size={13}/><b>{children.props?.title || 'Workspace'}</b></div><div className="topbar-right"><span className="connection"><i/> Local prototype</span><button className="top-help" aria-label="Help" title="Frontend demonstration"><CircleHelp size={17}/></button><div className="avatar avatar-small">RL</div></div></header><div className="page-wrap">{children}</div></main></div>; }
function Page({title,eyebrow,subtitle,actions,children}) {return <div className="page" title={title}><div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{subtitle&&<p>{subtitle}</p>}</div>{actions&&<div className="page-actions">{actions}</div>}</div>{children}</div>;}
function Status({children,tone='neutral'}) {return <span className={'status status-'+tone}><i/>{children}</span>;}
function DemoBanner({children='Values on this page are illustrative and have not been measured.'}) {return <div className="demo-banner"><Sparkles size={15}/><span><b>Local prototype</b> · {children}</span><button title="About illustrative data" aria-label="About illustrative data"><CircleHelp size={15}/></button></div>;}
function MetricCard({label,value,unit,detail,icon:Icon,trend}) {return <article className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={17}/></span></div><div className="metric-value">{value}<small>{unit}</small></div><div className="metric-foot">{trend&&<span className="metric-trend"><ArrowDownRight size={14}/>{trend}</span>}{detail}</div></article>;}
function Card({title,subtitle,actions,children,className=''}) {return <section className={'card '+className}><div className="card-heading"><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div>{actions}</div>{children}</section>;}
const fmt=(v,n=2)=>v==null?'—':Number(v).toFixed(n);
const chartTip={contentStyle:{background:'#111a2b',border:'1px solid #28364e',borderRadius:9,color:'#eef3ff'},itemStyle:{color:'#b8c5dd'},labelStyle:{color:'#f2f6ff'}};

function Home(){const features=[['Automatic analysis','Static estimates and dynamic profiles come together in one clear view.',Microscope],['Intelligent pairing','Compare predicted pair costs and inspect the resource features behind each match.',Network],['Performance insights','Review makespan, slowdown, and run variability from supplied results.',BarChart3],['Research-driven','A transparent interface built around the HARP-PAF research model.',ShieldCheck]];return <Page title="Smarter task pairing for better performance" eyebrow="PHASE-AWARE SCHEDULING" subtitle="Explore heuristic workload pairing and measured execution times under WSL2. This prototype combines reviewed workload profiles, heuristic pairing and measured local execution times." actions={<Link className="btn btn-primary" to="/upload"><Upload size={16}/> Upload code <ArrowRight size={16}/></Link>}><DemoBanner>Explore the frontend with sample data. Approved C++ demonstration workloads are compiled, executed and benchmarked by the local backend.</DemoBanner><div className="hero-grid"><div className="hero-copy"><span className="hero-kicker"><span className="pulse-dot"/> VIRTUAL CPU RESOURCE AWARENESS</span><h2>Explore workload pairing<br/>with <span>measured runtimes.</span></h2><p>HARP-PAF evaluates four approved C++ workloads using transparent heuristic costs and repeated local WSL benchmarks. Physical SMT sibling relationships and phase-level resource behavior are not verified.</p><div className="hero-actions"><Link to="/upload" className="btn btn-primary"><Upload size={16}/> Upload code</Link><a href="#workflow" className="btn btn-secondary">Explore the workflow <ArrowRight size={15}/></a></div><div className="hero-proof"><span><Check size={14}/> Heuristic resource profiles</span><span><Check size={14}/> Estimated pair costs</span></div></div><div className="core-visual"><div className="core-visual-head"><span>VIRTUAL CPU PLACEMENT</span><span className="live-pill"><i/> 2 virtual CPU sets</span></div><div className="core-pair"><div className="core-box"><div className="core-label"><Cpu size={15}/> CORE 0</div><div className="thread-slot"><small>LOGICAL CPU 0</small><b><Activity size={14}/> Task 01</b></div><div className="thread-slot"><small>LOGICAL CPU 1</small><b><Activity size={14}/> Task 02</b></div></div><div className="pair-connector"><span>SHARED<br/>RESOURCES</span><div>↔</div></div><div className="core-box"><div className="core-label"><Cpu size={15}/> CORE 1</div><div className="thread-slot"><small>LOGICAL CPU 2</small><b><Activity size={14}/> Task 03</b></div><div className="thread-slot"><small>LOGICAL CPU 3</small><b><Activity size={14}/> Task 04</b></div></div></div><div className="core-visual-foot"><span><i className="legend-cyan"/> complementary demand</span><span><i className="legend-violet"/> heuristic pairing</span></div></div></div><div className="feature-grid">{features.map(([title,desc,Icon])=><article className="feature-card" key={title}><span className="feature-icon"><Icon size={18}/></span><h3>{title}</h3><p>{desc}</p><Link to={title==='Intelligent pairing'?'/pairs':'/results'} aria-label={'Explore '+title}><ArrowRight size={16}/></Link></article>)}</div><section id="workflow" className="workflow card"><div className="workflow-head"><div><div className="eyebrow">THE HARP-PAF PIPELINE</div><h2>From source to insight</h2></div><Link to="/upload" className="text-link">Start an analysis <ArrowRight size={14}/></Link></div><div className="workflow-steps">{[['01','Source code','Upload workloads'],['02','Profile fusion','Reviewed workload profiles'],['03','Pair prediction','Heuristic pair costs'],['04','Scheduling','Minimum-weight match'],['05','Evaluation','Compare results']].map(([n,title,sub],i)=><div className="workflow-step" key={n}><span className="step-num">{n}</span><b>{title}</b><small>{sub}</small>{i<4&&<span className="step-line"/>}</div>)}</div></section><div className="formula-note"><span className="feature-icon"><Layers3 size={17}/></span><div><b>Static and dynamic feature fusion</b><code>x(i,k) = q(i,k) × d(i,k) + [1 − q(i,k)] × s(i,k)</code></div><span className="formula-caption">Displayed model reference</span></div></Page>;}

function UploadCode(){
  const [busy, setBusy] = useState(false);
  const [files,setFiles]=useState([]),[code,setCode]=useState(''),[tab,setTab]=useState('files'),[error,setError]=useState(''),[drag,setDrag]=useState(false),[language,setLanguage]=useState('cpp');
  const input=useRef(null),navigate=useNavigate(),extension=language==='c'?'.c':'.cpp';
  const add=incoming=>{setError('');const accepted=[];for(const f of incoming){const ext='.'+(f.name.split('.').pop()||'').toLowerCase();if(ext!==extension){setError(`${f.name}: ${language==='c'?'C':'C++'} mode accepts ${extension} program files only.`);continue;}if(files.some(x=>x.name===f.name)||accepted.some(x=>x.name===f.name))continue;accepted.push(f);}setFiles(a=>[...a,...accepted]);};
  const remove=i=>setFiles(a=>a.filter((_,n)=>n!==i));

  const submit = async () => {
    if (busy) return;

    setError('');

    if (tab !== 'files') {
      setError('Paste mode is not available for live execution.');
      return;
    }

    if (language !== 'cpp') {
      setError('Currently only the four approved C++ demo files are supported.');
      return;
    }

    if (files.length !== 4) {
      setError('Please select exactly four C++ source files.');
      return;
    }

    if (files.some(file => !file.name.toLowerCase().endsWith('.cpp'))) {
      setError('All four files must have the .cpp extension.');
      return;
    }

    if (files.some(file => file.size === 0 || file.size > 102400)) {
      setError('Each file must be nonempty and no larger than 100 KB.');
      return;
    }

    try {
      setBusy(true);

      const job = await createJob(files, 'cpp');

      if (!job.jobId) {
        throw new Error('The backend did not return a job ID.');
      }

      navigate(`/jobs/${job.jobId}`);
    } catch (err) {
      setError(err.message || 'The analysis could not be completed.');
    } finally {
      setBusy(false);
    }
  };

  const total=files.reduce((n,f)=>n+f.size,0),sample=language==='c'?'#include <stdio.h>\n\nint main(void) {\n  printf("Hello from C\\n");\n  return 0;\n}':'#include <iostream>\n\nint main() {\n  std::cout << "Hello from C++\\n";\n  return 0;\n}';
  return <Page title="New analysis" eyebrow="WORKSPACE / NEW ANALYSIS" subtitle="Upload four approved C++ programs for local analysis."><DemoBanner>Upload exactly four approved C++ demonstration files for real local compilation, execution, pairing and benchmarking.</DemoBanner><div className="upload-layout"><div className="upload-main card"><div className="card-heading"><div><h2>Add source code</h2><p>Select C++ and upload exactly four approved demonstration source files.</p></div><label className="language-picker"><span>PROGRAM LANGUAGE</span><select value={language} onChange={e=>{setLanguage(e.target.value);setError('');}} aria-label="Program language"><option value="cpp">C++</option></select></label></div><div className="tabs"><button className={tab==='files'?'selected':''} onClick={()=>setTab('files')}><FileCode2 size={15}/> Upload files</button></div>{tab==='files'?<><input ref={input} type="file" hidden multiple accept={extension} onChange={e=>{add([...e.target.files]);e.target.value='';}}/><div className={'dropzone '+(drag?'dragging':'')} onDragOver={e=>{e.preventDefault();setDrag(true)}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);add([...e.dataTransfer.files]);}}><span className="drop-icon"><Upload size={20}/></span><b>Drag {language==='c'?'C':'C++'} source files here</b><span>or <button className="inline-button" onClick={()=>input.current?.click()}>browse your files</button></span><small>Supported extension for {language==='c'?'C':'C++'}: {extension}</small></div>{files.length>0&&<div className="file-list"><div className="file-list-head"><span>UPLOADED FILES <b>{files.length}</b></span><span>{(total/1024).toFixed(1)} KB total</span></div>{files.map((f,i)=><div className="file-row" key={f.name+i}><span className="file-icon"><FileCode2 size={16}/></span><span className="file-name"><b>{f.name}</b><small>{f.size<1024?`${f.size} B`:`${(f.size/1024).toFixed(1)} KB`}</small></span><span className="file-valid"><Check size={13}/> Ready</span><button className="icon-btn remove-file" aria-label={`Remove ${f.name}`} onClick={()=>remove(i)}><X size={15}/></button></div>)}</div>}</>:<div className="editor-wrap"><div className="editor-bar"><span><i/> source{extension}</span><span>Plain text · local only</span></div><textarea aria-label={`Paste ${language==='c'?'C':'C++'} code`} spellCheck="false" placeholder={sample} value={code} onChange={e=>setCode(e.target.value)}/><div className="editor-foot"><span>{code.length} characters</span><span>Paste mode unavailable for live execution</span></div></div>}{error&&<div className="form-error"><AlertTriangle size={15}/>{error}</div>}<div className="upload-note"><AlertTriangle size={16}/><p>HARP-PAF analyzes independent workloads. Your source must follow the supported task format. A single arbitrary <code>main()</code> function does not automatically represent multiple independent tasks.</p></div><div className="upload-footer"><span><ShieldCheck size={15}/> Local FastAPI execution</span><button className="btn btn-primary" onClick={submit} disabled={busy}>
  <Sparkles size={15}/>
  {busy ? 'Compiling and benchmarking...' : 'Analyze & Optimize'}
  <ArrowRight size={15}/>
</button></div></div><aside className="upload-aside"><Card title="What happens next" subtitle="Local execution workflow"><div className="mini-steps">{[['1','Source validation'],['2','Static analysis'],['3','Pair predictions'],['4','Results dashboard']].map(([n,l],i)=><div className="mini-step" key={n}><span className={'mini-step-num '+(i===0?'on':'')}>{n}</span><span><b>{l}</b><small>{i===0?'Backend source validation':'Processed by FastAPI'}</small></span></div>)}</div><div className="aside-separator"/><div className="aside-callout"><CircleHelp size={16}/><p>Connected to the local FastAPI backend. Only the four approved C++ demonstration programs are permitted.</p></div></Card><Card title="Supported program files"><div className="ext-list">{['.cpp'].map(x=><span key={x}>{x}</span>)}</div><p className="aside-muted">Header files (.h and .hpp) are not accepted as program inputs. Approved sources are submitted to the local WSL backend.</p></Card></aside></div></Page>;
}

const pipeline=[
  'Approved source validation',
  'C++ compilation',
  'Compilation verification',
  'Solo execution and output verification',
  'Heuristic pair-cost calculation',
  'Minimum-cost task matching',
  'Repeated benchmark execution',
  'Results saved and available'
];
function ProgramOutput({title='Program output',subtitle='Output for this job, when supplied by the execution service'}){const [stream,setStream]=useState('stdout');return <Card title={title} subtitle={subtitle} actions={<Status>Not available in demo</Status>}><div className="output-tabs" role="tablist" aria-label="Program output stream"><button role="tab" aria-selected={stream==='stdout'} className={stream==='stdout'?'selected':''} onClick={()=>setStream('stdout')}>Standard output</button><button role="tab" aria-selected={stream==='stderr'} className={stream==='stderr'?'selected':''} onClick={()=>setStream('stderr')}>Standard error</button></div><div className="output-console" role="tabpanel"><div className="console-heading"><span><i/>{stream==='stdout'?'stdout':'stderr'}</span><span>PLAIN TEXT</span></div><div className="console-empty"><span className="console-prompt">$</span><div><b>{stream==='stdout'?'No program output available':'No error output available'}</b><p>This frontend demo does not compile or execute uploaded code. {stream==='stdout'?'Standard output':'Standard error'} will appear here when the backend supplies it for this job.</p></div></div></div><p className="output-safety-note"><CircleHelp size={14}/> Output will be displayed as plain text; source code is never run in the browser.</p></Card>;}


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
          timer = setTimeout(loadJob, 1500);
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
  const stage = Math.max(0, Math.min(8, Number(job?.stageIndex ?? 0)));
  const historicalStageCounts = {
    queued: 1,
    compiled: 3,
    measured: 4,
    paired: 6,
    completed: 8
  };
  const displayStage = historicalStageCounts[job?.status] ?? stage;
  const percent = Math.round(displayStage / 8 * 100);
  const benchmark = job?.benchmark;
  const outputs = job?.executionResults || [];

  return (
    <Page
      title="Analysis progress"
      eyebrow="WORKSPACE / LIVE JOB"
      subtitle="Actual backend job information and measured results."
      actions={<span className="job-id-chip">{id}</span>}
    >
      {loading && <Card title="Loading job"><p>Fetching backend results...</p></Card>}

      {error && (
        <div className="form-error">
          <AlertTriangle size={16}/>
          {error}
        </div>
      )}

      {job && (
        <>
          <div className="job-summary card">
            <div className="job-summary-icon"><FileCode2 size={21}/></div>
            <div className="job-summary-name">
              <small>SUBMITTED SOURCE</small>
              <b>{(job.files || []).map(f => f.originalName).join(', ')}</b>
              <span>{job.language?.toUpperCase()} · {job.createdAt}</span>
            </div>
            <div className="job-status">
              <small>STATUS</small>
              <Status tone={failed ? 'error' : completed ? 'success' : 'info'}>
                {job.status}
              </Status>
            </div>
          </div>

          <Card
            title="Pipeline stages"
            subtitle="Reported by the actual FastAPI backend"
            actions={<b className="progress-percent">{percent}%</b>}
          >
            <div className="progress-track">
              <span style={{width: `${percent}%`}}/>
            </div>

            <div className="pipeline-list">
              {pipeline.map((label, i) => {
                const completedStages = {
                  queued: 1,
                  compiled: 3,
                  measured: 4,
                  paired: 6,
                  completed: 8
                };
                const done = !failed && (
                  completed ||
                  i < (completedStages[job?.status] ?? stage)
                );
                const current = job?.status === 'running' && i === stage;

                return (
                  <div className={'pipeline-row ' + (current ? 'current' : '')} key={label}>
                    <span className={'pipeline-icon ' + (done ? 'done' : current ? 'active' : '')}>
                      {done ? <Check size={14}/> : current ? <span className="spinner"/> : String(i + 1).padStart(2, '0')}
                    </span>
                    <span className="pipeline-name">
                      <b>{label}</b>
                      <small>{done ? 'Backend stage passed' : current ? job.stage : 'Pending'}</small>
                    </span>
                    <span className="pipeline-state">
                      {done ? 'COMPLETED' : current ? 'RUNNING' : 'PENDING'}
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
          </Card>

          {completed && benchmark && (
            <Card title="Real benchmark results" subtitle="Measured locally under WSL">
              <div className="stats-list">
                {[
                  ['Baseline median', `${(benchmark.baselineMedianSeconds * 1000).toFixed(4)} ms`],
                  ['Selected median', `${(benchmark.selectedMedianSeconds * 1000).toFixed(4)} ms`],
                  ['Observed speedup', `${benchmark.speedup.toFixed(4)}×`],
                  ['Runtime reduction', `${benchmark.runtimeReductionPercent.toFixed(3)}%`],
                  ['Repetitions per plan', benchmark.repetitions],
                  ['Selected pairs', (job.selectedPairs || []).map(p => p.join(' + ')).join(' | ')]
                ].map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <b>{value}</b>
                  </div>
                ))}
              </div>
              <div className="complete-box">
                <Check size={17}/>
                <div>
                  <b>Measured analysis complete</b>
                  <small>Results are genuine local measurements, not statistically proven speedups.</small>
                </div>
              </div>
            </Card>
          )}

          <Card title="Verified program output" subtitle="Captured from the four executables">
            <div className="output-console">
              <pre style={{whiteSpace: 'pre-wrap', padding: 16}}>
                {outputs.map(item =>
                  `${item.taskId} (${item.filename})\n` +
                  `Verified: ${item.verified}\n` +
                  `stdout: ${item.stdout || ''}\n` +
                  `stderr: ${item.stderr || ''}\n`
                ).join('\n')}
              </pre>
            </div>
          </Card>

          <div className="job-footnote">
            WSL virtual CPU affinity only. Physical SMT topology and
            hardware counters are not verified.
          </div>
        </>
      )}
    </Page>
  );
}

function Results(){const d=getDashboardData(),s=d.summary;return <Page title="Results dashboard" eyebrow="ANALYSIS / HPA-2026-041" subtitle="Performance overview across the selected evaluation methods." actions={<><button className="btn btn-secondary" onClick={()=>csvDownload('harp-paf-results.csv',d.makespan)}><Download size={15}/> Export CSV</button><select aria-label="Select baseline" className="select"><option>Baseline: Linux Default</option><option>Baseline: Random Pairing</option></select></>}><DemoBanner/><div className="metric-grid"><MetricCard label="HARP-PAF makespan" value={fmt(s.harpMakespan)} unit="s" detail="Frontend sample" icon={Clock3}/><MetricCard label="Baseline makespan" value={fmt(s.baselineMakespan)} unit="s" detail="Linux Default" icon={Clock3}/><MetricCard label="Speedup" value={fmt(s.speedup)} unit="×" detail="Baseline / HARP-PAF" icon={Gauge}/><MetricCard label="Runtime reduction" value={fmt(s.runtimeReductionPercent,1)} unit="%" detail="Illustrative comparison" icon={ArrowDownRight} trend="15.8%"/><MetricCard label="Worst-task slowdown" value={fmt(s.worstTaskSlowdown*100,1)} unit="%" detail="Per-task excess runtime" icon={Activity}/></div><div className="dashboard-grid"><Card title="Makespan by scheduling method" subtitle="Lower is better · wall-clock seconds" className="span-2"><div className="chart-wrap chart-tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={d.makespan} margin={{top:12,right:10,bottom:4,left:0}}><CartesianGrid stroke="#243149" strokeDasharray="3 4" vertical={false}/><XAxis dataKey="name" tick={{fill:'#96a4bc',fontSize:11}} axisLine={false} tickLine={false}/><YAxis unit=" s" tick={{fill:'#8493aa',fontSize:11}} axisLine={false} tickLine={false}/><Tooltip {...chartTip} formatter={v=>[`${v} s`,'Makespan']}/><Bar dataKey="value" name="Makespan" radius={[5,5,0,0]}>{d.makespan.map((row,i)=><Cell key={row.name} fill={i===3?'#4bd6d2':'#415273'}/>)}</Bar></BarChart></ResponsiveContainer></div><div className="chart-legend"><span><i className="legend-cyan"/> HARP-PAF</span><span><i className="legend-muted"/> Other methods</span></div></Card><Card title="Per-task slowdown" subtitle="Excess runtime by workload · lower is better"><div className="chart-wrap chart-tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={d.tasks} margin={{top:12,right:6,bottom:2,left:-16}}><CartesianGrid stroke="#243149" strokeDasharray="3 4" vertical={false}/><XAxis dataKey="id" tick={{fill:'#96a4bc',fontSize:11}} axisLine={false} tickLine={false}/><YAxis unit="%" tick={{fill:'#8493aa',fontSize:11}} axisLine={false} tickLine={false}/><Tooltip {...chartTip} formatter={v=>[`${(v*100).toFixed(1)}%`,'Slowdown']}/><Bar dataKey="slowdown" fill="#8a7cf6" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div><div className="chart-legend"><span><i className="legend-violet"/> HARP-PAF task slowdown</span></div></Card><Card title="Repeated-run distribution" subtitle="Summary ranges · seconds"><div className="range-list">{getRunDistribution().map(r=><div className="range-row" key={r.name}><div><b>{r.name}</b><small>min {r.min.toFixed(1)} · median {r.median.toFixed(1)} · max {r.max.toFixed(1)}</small></div><div className="range-bar"><span style={{left:`${(r.min-7)*20}%`,width:`${(r.max-r.min)*20}%`}}/><i style={{left:`${(r.median-7)*20}%`}}/></div></div>)}</div><div className="distribution-foot">Illustrative min, median, and max across repeated runs.</div></Card><Card title="Run statistics" subtitle="Available evaluation summary"><div className="stats-list">{[['Repetitions',`${s.repetitions} runs`],['Mean runtime',`${s.meanRuntime.toFixed(2)} s`],['Median runtime',`${s.medianRuntime.toFixed(2)} s`],['Standard deviation',`${s.standardDeviation.toFixed(2)} s`],['95% confidence interval',`${s.confidenceInterval[0]}–${s.confidenceInterval[1]} s`],['Scheduling overhead',`${s.schedulingOverhead.toFixed(2)} s`]].map(([l,v])=><div key={l}><span>{l}</span><b>{v}</b></div>)}</div></Card></div><ProgramOutput title="Final program output" subtitle="Final stdout and stderr for this analysis, when supplied by the backend" /><div className="formula-note compact-note"><span className="feature-icon"><Gauge size={16}/></span><div><b>Metric definitions</b><code>Speedup = baseline makespan ÷ HARP-PAF makespan · Runtime reduction = (baseline − HARP-PAF) ÷ baseline × 100</code></div><span className="formula-caption">Sample values only</span></div></Page>;}

function LiveResults() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    getResults(id)
      .then(result => {
        if (active) setData(result);
      })
      .catch(err => {
        if (active) setError(err.message);
      });

    return () => { active = false; };
  }, [id]);

  if (error) {
    return (
      <Page title="Results dashboard">
        <div className="form-error">
          <AlertTriangle size={16}/>
          {error}
        </div>
      </Page>
    );
  }

  if (!data) {
    return (
      <Page title="Results dashboard">
        <Card title="Loading measured results">
          <p>Fetching benchmark data from FastAPI...</p>
        </Card>
      </Page>
    );
  }

  const s = data.summary;
  const toMs = value => value * 1000;

  const chartData = data.makespan.map(item => ({
    name: item.name,
    value: toMs(item.value)
  }));

  const trials = data.rawRuns.baseline.map((value, i) => ({
    run: i + 1,
    baseline: toMs(value),
    selected: toMs(data.rawRuns.selected[i])
  }));

  return (
    <Page
      title="Results dashboard"
      eyebrow="ANALYSIS / MEASURED RESULTS"
      subtitle="Real local WSL benchmark measurements."
      actions={
        <button
          className="btn btn-secondary"
          onClick={() => jsonDownload(`${id}-results.json`, data)}
        >
          <Download size={15}/> Export JSON
        </button>
      }
    >
      <div className="metric-grid">
        <MetricCard label="Selected makespan" value={fmt(toMs(s.harpMakespan), 4)} unit="ms" detail="Median measured runtime" icon={Clock3}/>
        <MetricCard label="Baseline makespan" value={fmt(toMs(s.baselineMakespan), 4)} unit="ms" detail="Fixed baseline" icon={Clock3}/>
        <MetricCard label="Observed speedup" value={fmt(s.speedup, 4)} unit="×" detail="Baseline / selected" icon={Gauge}/>
        <MetricCard label="Runtime reduction" value={fmt(s.runtimeReductionPercent, 3)} unit="%" detail="Measured, not statistically validated" icon={ArrowDownRight}/>
        <MetricCard label="Repetitions" value={s.repetitions} unit="runs" detail="Per configuration" icon={Activity}/>
      </div>

      <div className="dashboard-grid">
        <Card title="Makespan comparison" subtitle="Measured median wall time in milliseconds" className="span-2">
          <div className="chart-wrap chart-tall">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid stroke="#243149" strokeDasharray="3 4" vertical={false}/>
                <XAxis dataKey="name" tick={{fill:'#96a4bc',fontSize:11}}/>
                <YAxis unit=" ms" tick={{fill:'#8493aa',fontSize:11}}/>
                <Tooltip {...chartTip} formatter={v => [`${Number(v).toFixed(4)} ms`, 'Makespan']}/>
                <Bar dataKey="value" radius={[5,5,0,0]}>
                  {chartData.map((row, i) => (
                    <Cell key={row.name} fill={i === 1 ? '#4bd6d2' : '#415273'}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Repeated benchmark runs" subtitle="Actual execution times in milliseconds" className="span-2">
          <div className="chart-wrap chart-tall">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trials}>
                <CartesianGrid stroke="#243149" strokeDasharray="3 4"/>
                <XAxis dataKey="run" tick={{fill:'#96a4bc',fontSize:11}}/>
                <YAxis unit=" ms" tick={{fill:'#8493aa',fontSize:11}}/>
                <Tooltip {...chartTip} formatter={v => [`${Number(v).toFixed(4)} ms`, 'Runtime']}/>
                <Line type="monotone" dataKey="baseline" name="Fixed baseline" stroke="#8a7cf6" strokeWidth={2}/>
                <Line type="monotone" dataKey="selected" name="Heuristic selected" stroke="#4bd6d2" strokeWidth={2}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Selected task pairs" subtitle="Minimum-cost heuristic matching">
        <div className="stats-list">
          {data.selectedPairs.map((pair, i) => (
            <div key={i}>
              <span>Pair {i + 1}</span>
              <b>{pair.join(' + ')}</b>
            </div>
          ))}
        </div>
      </Card>

      <p className="job-footnote">
        Measurements include process-launch overhead.
        WSL virtual logical CPUs are not verified SMT siblings.
        Performance improvement is not statistically established.
      </p>
    </Page>
  );
}

function LivePairAnalysis() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');
    setSelected(null);

    getResults(id)
      .then(result => {
        if (active) {
          setData(result);
          setSelected(result.pairs[0] || null);
        }
      })
      .catch(err => {
        if (active) setError(err.message);
      });

    return () => { active = false; };
  }, [id]);

  if (error) return <Page title="Pair analysis">
    <div className="form-error"><AlertTriangle size={16}/>{error}</div>
  </Page>;

  if (!data) return <Page title="Pair analysis">
    <Card title="Loading pair costs"><p>Fetching backend results...</p></Card>
  </Page>;

  const pairs = data.pairs || [];
  const ids = [...new Set(pairs.flatMap(p => [p.taskA, p.taskB]))];
  const getPair = (a, b) => pairs.find(p =>
    (p.taskA === a && p.taskB === b) ||
    (p.taskA === b && p.taskB === a)
  );
  const selectedPairs = (data.selectedPairs || [])
    .map(([a,b]) => getPair(a,b))
    .filter(Boolean);
  const features = [
    ['Integer arithmetic', 'integer'],
    ['Floating-point', 'floating_point'],
    ['Memory activity', 'memory'],
    ['Modulo activity', 'modulo']
  ];

  return <Page
    title="Pair analysis"
    eyebrow="ANALYSIS / HEURISTIC PAIR COSTS"
    subtitle="Six estimated pair costs and exact four-task matching."
    actions={<span className="job-id-chip">{id}</span>}
  >
    <div className="demo-banner">
      <CircleHelp size={15}/>
      <span>These costs are illustrative heuristics, not measured contention or predicted slowdown.</span>
    </div>

    <div className="pair-layout">
      <Card title="Pair-cost heatmap" subtitle="Lower heuristic cost is preferred" className="heatmap-card">
        <div className="heatmap-wrap">
          <div className="heatmap-grid">
            <span className="heatmap-axis empty"/>
            {ids.map(t => <span className="heatmap-axis" key={t}>{t}</span>)}
            {ids.map(row => <React.Fragment key={row}>
              <span className="heatmap-axis row-axis">{row}</span>
              {ids.map(col => {
                const p = row === col ? null : getPair(row,col);
                return <button
                  key={col}
                  className={'heat-cell ' + (!p ? 'diagonal' : '') + (p && selected === p ? ' chosen' : '')}
                  disabled={!p}
                  onClick={() => setSelected(p)}
                  title={p ? `${row} + ${col}: ${p.finalPairCost}` : 'Same task'}
                >
                  {p ? p.finalPairCost.toFixed(3) : '—'}
                </button>;
              })}
            </React.Fragment>)}
          </div>
          <p className="heat-help">Click a cell to inspect its heuristic components.</p>
        </div>
      </Card>

      <Card title="Pair details" subtitle={selected ? `${selected.taskA} + ${selected.taskB}` : 'No pair'} className="pair-detail">
        {selected && <>
          <div className="pair-highlight">
            <span className="pair-nodes">
              <b>{selected.taskA}</b><span>↔</span><b>{selected.taskB}</b>
            </span>
          </div>
          <div className="pair-metrics">
            <div><small>HEURISTIC PAIR COST</small><b>{selected.finalPairCost.toFixed(4)}</b></div>
            <div><small>PREDICTED SLOWDOWN</small><b>Unavailable</b></div>
          </div>
          <div className="feature-bars">
            {features.map(([label,key]) => {
              const value = selected.features?.[key] ?? 0;
              return <div className="feature-bar-row" key={key}>
                <span className="feature-label">{label}</span>
                <div className="feature-track">
                  <i style={{width:`${Math.min(100,value/1.5*100)}%`}}/>
                </div>
                <b>{value.toFixed(3)}</b>
              </div>;
            })}
          </div>
          <p className="pair-note">Weighted resource-overlap estimates; not hardware measurements.</p>
        </>}
      </Card>
    </div>

    <div className="selected-pairs">
      <div className="section-header">
        <div>
          <h2>Selected task pairs</h2>
          <p>Four distinct tasks, each assigned exactly once</p>
        </div>
      </div>
      <div className="selected-pair-grid">
        {selectedPairs.map((p,i) =>
          <button
            className={'selected-pair-card ' + (selected === p ? 'selected' : '')}
            key={`${p.taskA}-${p.taskB}`}
            onClick={() => setSelected(p)}
          >
            <span className="selected-pair-top">
              <span>PAIR {i+1} · VIRTUAL CPU SET {(data.system?.cpuSets?.[i] || []).join(', ')}</span>
              <ChevronRight size={15}/>
            </span>
            <span className="selected-pair-names">
              <b>{p.taskA}</b><span>+</span><b>{p.taskB}</b>
            </span>
            <span className="selected-pair-bottom">
              <span>Heuristic cost <b>{p.finalPairCost.toFixed(4)}</b></span>
            </span>
          </button>
        )}
      </div>
    </div>

    <Card title="All three matching combinations" subtitle="Minimum total heuristic cost determines selection">
      <div className="stats-list">
        {(data.allMatchings || []).map(m =>
          <div key={m.matching}>
            <span>{m.matching}: {m.pairs.map(p => p.join('+')).join(' | ')}</span>
            <b>{m.totalCost.toFixed(4)}</b>
          </div>
        )}
      </div>
      <p className="job-footnote">
        Equal minimum costs use deterministic first-matching tie breaking.
        CPU sets are WSL virtual logical CPUs, not verified SMT sibling cores.
      </p>
    </Card>
  </Page>;
}


function LiveTaskMetrics() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    setData(null);
    setError('');

    getResults(id)
      .then(result => {
        if (active) setData(result);
      })
      .catch(err => {
        if (active) setError(err.message);
      });

    return () => { active = false; };
  }, [id]);

  if (error) {
    return <Page title="Task metrics">
      <div className="form-error">
        <AlertTriangle size={16}/>{error}
      </div>
    </Page>;
  }

  if (!data) {
    return <Page title="Task metrics">
      <Card title="Loading task data">
        <p>Fetching measured execution data...</p>
      </Card>
    </Page>;
  }

  const tasks = data.tasks || [];

  const columns = [
    'Task ID',
    'Filename',
    'Solo runtime',
    'Co-run runtime',
    'Slowdown',
    'Instructions',
    'CPU cycles',
    'IPC',
    'Cache misses',
    'Memory bandwidth'
  ];

  const formatMs = value =>
    value == null ? 'Unavailable' :
    `${(value * 1000).toFixed(4)} ms`;

  const download = () => csvDownload(
    `${id}-task-metrics.csv`,
    tasks.map(t => ({
      taskId: t.id,
      filename: t.filename,
      soloRuntimeSeconds: t.solo,
      coRunRuntimeSeconds: t.coRun,
      slowdown: t.slowdown,
      instructions: t.instructions,
      cycles: t.cycles
    }))
  );

  return <Page
    title="Task metrics"
    eyebrow="ANALYSIS / MEASURED TASK DATA"
    subtitle="Verified solo execution times and available workload statistics."
    actions={
      <button className="btn btn-secondary" onClick={download}>
        <Download size={15}/> Export CSV
      </button>
    }
  >
    <Card
      title="Task profile table"
      subtitle="Measured values only. Unsupported metrics are explicitly unavailable."
    >
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map(c => <th key={c}>{c}</th>)}
            </tr>
          </thead>

          <tbody>
            {tasks.map(t => (
              <tr key={t.id}>
                <td><span className="task-id">{t.id}</span></td>
                <td>{t.filename}</td>
                <td>{formatMs(t.solo)}</td>
                <td>{formatMs(t.coRun)}</td>
                <td>
                  {t.slowdown == null
                    ? 'Unavailable'
                    : `${(t.slowdown * 100).toFixed(2)}%`}
                </td>
                <td>{t.instructions ?? 'Unavailable'}</td>
                <td>{t.cycles ?? 'Unavailable'}</td>
                <td>Unavailable</td>
                <td>Unavailable</td>
                <td>Unavailable</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>

    <div className="info-note">
      <CircleHelp size={16}/>
      <p>
        Solo runtime was measured by the local backend.
        Co-run task timing, hardware counters, verified SMT
        topology and phase-level measurements are currently
        unavailable. Benchmark makespan is measured separately.
      </p>
    </div>
  </Page>;
}


function LivePredictionAnalysis() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');

    getResults(id)
      .then(result => {
        if (active) setData(result);
      })
      .catch(err => {
        if (active) setError(err.message);
      });

    return () => { active = false; };
  }, [id]);

  if (error) return <Page title="Prediction analysis">
    <div className="form-error">
      <AlertTriangle size={16}/>{error}
    </div>
  </Page>;

  if (!data) return <Page title="Prediction analysis">
    <Card title="Loading analysis">
      <p>Fetching backend data...</p>
    </Card>
  </Page>;

  const pairs = data.pairs || [];
  const matchings = data.allMatchings || [];
  const selected = (data.selectedPairs || []).map(p => p.join(' + '));

  return <Page
    title="Prediction analysis"
    eyebrow="EVALUATION / HEURISTIC MODEL"
    subtitle="Transparent pairing estimates and model limitations."
    actions={<span className="job-id-chip">{id}</span>}
  >
    <div className="metric-grid">
      <MetricCard label="Pair costs evaluated" value={pairs.length} unit="pairs" detail="Estimated heuristic scores" icon={Network}/>
      <MetricCard label="Complete matchings" value={matchings.length} unit="plans" detail="All exact four-task matchings" icon={GitBranch}/>
      <MetricCard label="Measured prediction accuracy" value="Unavailable" unit="" detail="No calibrated evaluation dataset" icon={Gauge}/>
      <MetricCard label="Confidence interval" value="Unavailable" unit="" detail="Not statistically established" icon={Activity}/>
    </div>

    <Card title="Heuristic pair scores" subtitle="Weighted resource-overlap estimates">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>TASK A</th>
              <th>TASK B</th>
              <th>HEURISTIC COST</th>
              <th>PREDICTED SLOWDOWN</th>
              <th>DATA ORIGIN</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map(p => <tr key={`${p.taskA}-${p.taskB}`}>
              <td>{p.taskA}</td>
              <td>{p.taskB}</td>
              <td>{p.finalPairCost.toFixed(4)}</td>
              <td>Unavailable</td>
              <td>Illustrative heuristic</td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </Card>

    <Card title="Matching evaluation" subtitle="Minimum total heuristic cost">
      <div className="stats-list">
        {matchings.map(m => <div key={m.matching}>
          <span>{m.matching}: {m.pairs.map(p => p.join('+')).join(' | ')}</span>
          <b>{m.totalCost.toFixed(4)}</b>
        </div>)}
      </div>
      <p className="job-footnote">
        Selected pairing: {selected.join(' | ')}.
        Equal minimum costs use deterministic tie breaking.
      </p>
    </Card>

    <div className="info-note">
      <CircleHelp size={16}/>
      <p>
        This prototype uses manually assigned workload-resource
        profiles for four reviewed C++ programs. Pair costs are
        reproducible heuristic estimates, not hardware measurements.
        Prediction errors, confidence intervals and phase-aware
        model accuracy have not been established.
        Actual benchmark measurements are available separately
        in the Results Dashboard.
      </p>
    </div>
  </Page>;
}

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
        setJobs(response);
        setError('');
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }

    loadJobs();

    return () => { active = false; };
  }, []);

  const filtered = jobs.filter(job =>
    [
      job.jobId,
      ...(job.filenames || []),
      job.status
    ].join(' ').toLowerCase().includes(query.toLowerCase())
  );

  const ms = value =>
    value == null ? 'Unavailable' :
    `${(value * 1000).toFixed(4)} ms`;

  const speed = value =>
    value == null ? 'Unavailable' :
    `${value.toFixed(4)}×`;

  const downloadSummary = job => {
    csvDownload(`${job.jobId}.csv`, [{
      jobId: job.jobId,
      status: job.status,
      filenames: (job.filenames || []).join('; '),
      baselineMilliseconds:
        job.baselineMakespan == null ? '' :
        job.baselineMakespan * 1000,
      selectedMilliseconds:
        job.selectedMakespan == null ? '' :
        job.selectedMakespan * 1000,
      speedup: job.speedup ?? '',
      runtimeReductionPercent:
        job.runtimeReductionPercent ?? ''
    }]);
  };

  return (
    <Page
      title="History & reports"
      eyebrow="WORKSPACE / LIVE HISTORY"
      subtitle="Previously submitted jobs saved by the FastAPI backend."
      actions={
        <Link className="btn btn-primary" to="/upload">
          <Plus size={16}/> New analysis
        </Link>
      }
    >
      {error && (
        <div className="form-error">
          <AlertTriangle size={16}/>{error}
        </div>
      )}

      <Card
        title="Analysis jobs"
        subtitle={`${jobs.length} saved backend jobs`}
      >
        <div className="table-toolbar">
          <label className="search-field">
            <Search size={16}/>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search job ID or filename"
              aria-label="Search jobs"
            />
          </label>

          <span className="result-count">
            Showing {filtered.length} of {jobs.length}
          </span>
        </div>

        {loading ? (
          <div className="empty-inline centered">
            Loading saved jobs...
          </div>
        ) : filtered.length ? (
          <div className="table-scroll">
            <table className="data-table history-table">
              <thead>
                <tr>
                  <th>JOB ID</th>
                  <th>UPLOADED FILES</th>
                  <th>STATUS</th>
                  <th>SUBMITTED</th>
                  <th>MAKESPAN</th>
                  <th>SPEEDUP</th>
                  <th>REPORTS</th>
                  <th/>
                </tr>
              </thead>

              <tbody>
                {filtered.map(job => (
                  <tr key={job.jobId}>
                    <td>
                      <Link
                        to={`/jobs/${job.jobId}`}
                        className="job-link"
                      >
                        {job.jobId.slice(0, 12)}...
                      </Link>
                    </td>

                    <td>
                      {(job.filenames || []).join(', ')}
                    </td>

                    <td>
                      <Status
                        tone={
                          job.status === 'completed' ? 'success' :
                          job.status === 'failed' ? 'error' : 'info'
                        }
                      >
                        {job.status}
                      </Status>
                    </td>

                    <td>
                      {job.createdAt
                        ? new Date(job.createdAt).toLocaleString()
                        : 'Unavailable'}
                    </td>

                    <td>{ms(job.selectedMakespan)}</td>
                    <td>{speed(job.speedup)}</td>

                    <td>
                      <div className="report-actions">
                        <button
                          onClick={() => downloadSummary(job)}
                          title="Download job summary CSV"
                        >
                          <Download size={14}/> CSV
                        </button>

                        <button
                          onClick={() =>
                            jsonDownload(
                              `${job.jobId}-summary.json`,
                              job
                            )
                          }
                          title="Download job summary JSON"
                        >
                          <Download size={14}/> JSON
                        </button>
                      </div>
                    </td>

                    <td>
                      <Link
                        to={
                          job.status === 'completed'
                            ? `/results/${job.jobId}`
                            : `/jobs/${job.jobId}`
                        }
                        className="icon-btn"
                        aria-label="Open job"
                      >
                        <ChevronRight size={16}/>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-inline centered">
            No matching jobs found.
          </div>
        )}

        <div className="pagination">
          <span>Showing {filtered.length} jobs</span>
        </div>
      </Card>

      <p className="job-footnote">
        Historical jobs that have not completed benchmarking
        have no measured makespan or speedup. CSV and JSON
        downloads contain the job summary.
      </p>
    </Page>
  );
}

function SystemInfo() {
  const [system, setSystem] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    getSystem()
      .then(data => {
        if (active) setSystem(data);
      })
      .catch(err => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);

  if (loading) {
    return <Page title="System information">
      <Card title="Loading environment details">
        <p>Fetching system information from FastAPI...</p>
      </Card>
    </Page>;
  }

  if (error) {
    return <Page title="System information">
      <div className="form-error">
        <AlertTriangle size={16}/>{error}
      </div>
    </Page>;
  }

  const rows = [
    ['Execution environment', system.executionEnvironment],
    ['Operating system', system.operatingSystem],
    ['Architecture', system.architecture],
    ['Python version', system.pythonVersion],
    ['Logical CPU count', system.logicalCpuCount],
    ['Allowed CPU count', system.availableCpuCount],
    ['Allowed CPU IDs', system.allowedCpuIds.join(', ')],
    ['GCC compiler', system.compilerGcc],
    ['G++ compiler', system.compilerGpp],
    ['Clang compiler', system.compilerClang],
    ['Physical core count', system.physicalCoreCount ?? 'Unavailable'],
    ['Verified SMT sibling mapping',
      system.verifiedSmtSiblingMapping ? 'Verified' : 'Unavailable'],
    ['Cache topology', system.cacheTopology ?? 'Unavailable'],
    ['Hardware counters',
      system.hardwareCountersAvailable ? 'Available' : 'Unavailable']
  ];

  return <Page
    title="System information"
    eyebrow="ENVIRONMENT / LIVE SYSTEM"
    subtitle="Actual local execution environment details reported by FastAPI."
  >
    <div className="system-grid">
      <Card
        title="Execution environment"
        subtitle="Information retrieved from Ubuntu WSL"
      >
        <div className="system-info-list">
          {rows.map(([label, value]) =>
            <div key={label}>
              <span className="system-info-icon">
                <Cpu size={15}/>
              </span>
              <span>{label}</span>
              <b>{String(value)}</b>
            </div>
          )}
        </div>
      </Card>

      <Card
        title="SMT and hardware limitations"
        subtitle="Unverified hardware information"
      >
        <div className="empty-state small-empty">
          <span className="empty-icon">
            <Cpu size={22}/>
          </span>
          <h3>Physical SMT topology unavailable</h3>
          <p>
            WSL exposes virtual logical CPU IDs.
            Their physical SMT sibling relationships are
            not verified.
          </p>
          <p>
            Hardware counters, cache topology, memory
            bandwidth measurements and phase-level
            telemetry are unavailable.
          </p>
        </div>
      </Card>
    </div>

    <div className="info-note">
      <CircleHelp size={16}/>
      <p>
        CPU affinity operates on WSL virtual logical CPUs.
        This prototype must not claim verified physical
        core allocation or hardware-calibrated prediction.
      </p>
    </div>
  </Page>;
}


function NotFound(){return <Page title="Page not found" eyebrow="404"><div className="empty-state"><h2>This page isn’t available</h2><p>Use the workspace navigation to return to an analysis page.</p><Link className="btn btn-primary" to="/">Go to home</Link></div></Page>;}
export default function App(){return <AppLayout><Routes><Route path="/" element={<Home/>}/><Route path="/upload" element={<UploadCode/>}/><Route path="/jobs/:id" element={<JobProgress/>}/><Route path="/results" element={<LatestJobRedirect destination="results"/>}/><Route path="/results/:id" element={<LiveResults/>}/><Route path="/pairs" element={<LatestJobRedirect destination="pairs"/>}/><Route path="/pairs/:id" element={<LivePairAnalysis/>}/><Route path="/tasks" element={<LatestJobRedirect destination="tasks"/>}/><Route path="/tasks/:id" element={<LiveTaskMetrics/>}/><Route path="/predictions" element={<LatestJobRedirect destination="predictions"/>}/><Route path="/predictions/:id" element={<LivePredictionAnalysis/>}/><Route path="/history" element={<History/>}/><Route path="/system" element={<SystemInfo/>}/><Route path="*" element={<NotFound/>}/></Routes></AppLayout>;}
