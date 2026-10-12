import { jobs, summary, makespan, tasks, pairs, predictions, runDistribution, demoLabel } from '../data/mockData.js';

const STORAGE_KEY = 'harp-paf-demo-jobs';
export function getJobs() {
  try { return [...JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'), ...jobs]; }
  catch { return jobs; }
}
export function createDemoJob(files, language = 'c') {
  const job = { jobId: `DEMO-${Date.now().toString().slice(-6)}`, filenames: files.map(f => f.name), language: language === 'cpp' ? 'C++' : 'C', status: 'Running', createdAt: new Date().toLocaleString(), progressStage: 0, demo: true };
  const old = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  localStorage.setItem(STORAGE_KEY, JSON.stringify([job, ...old]));
  return job;
}
export function getJob(id) { return getJobs().find(j => j.jobId === id) || jobs[0]; }
export function getDashboardData() { return { summary, makespan, tasks, demoLabel }; }
export function getPairData() { return pairs; }
export function getPredictions() { return predictions; }
export function getRunDistribution() { return runDistribution; }
export function csvDownload(filename, rows) {
  const keys = Object.keys(rows[0] || {}); const escape = v => `"${String(v ?? '').replaceAll('"', '""')}"`;
  const csv = [keys.map(escape).join(','), ...rows.map(r => keys.map(k => escape(r[k])).join(','))].join('\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'})); a.download = filename; a.click(); URL.revokeObjectURL(a.href);
}
export function jsonDownload(filename, data) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)], {type:'application/json'})); a.download = filename; a.click(); URL.revokeObjectURL(a.href);
}
