import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { listJobs } from './services/api.js';

const BENCHMARK_JOB_ID = '609315c9a54f4a64b733cb9ff93e5478';

function getInitialTargetId() {
  try {
    const raw = localStorage.getItem('harp_custom_jobs_v1');
    const rawRes = localStorage.getItem('harp_custom_results_v1');
    const resultsMap = rawRes ? JSON.parse(rawRes) : {};
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const completed = parsed.find(j => j.status === 'completed' && resultsMap[j.jobId]);
        if (completed?.jobId) return completed.jobId;
      }
    }
  } catch {}
  return BENCHMARK_JOB_ID;
}

export default function LatestJobRedirect({ destination }) {
  const [targetId, setTargetId] = useState(getInitialTargetId);

  useEffect(() => {
    let active = true;

    listJobs()
      .then(jobs => {
        if (!active) return;
        const completed = (jobs || []).find(job => job.status === 'completed');
        const anyJob = (jobs || [])[0];
        const chosen = completed?.jobId || anyJob?.jobId || BENCHMARK_JOB_ID;
        setTargetId(chosen);
      })
      .catch(() => {
        if (!active) return;
        setTargetId(BENCHMARK_JOB_ID);
      });

    return () => {
      active = false;
    };
  }, []);

  return <Navigate to={`/${destination}/${targetId}`} replace />;
}

