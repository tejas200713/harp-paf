import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { listJobs } from './services/api.js';

const BENCHMARK_JOB_ID = '609315c9a54f4a64b733cb9ff93e5478';

export default function LatestJobRedirect({ destination }) {
  const [targetId, setTargetId] = useState(null);

  useEffect(() => {
    let active = true;

    listJobs()
      .then(jobs => {
        if (!active) return;
        // 1. Prefer a completed job (custom user job first, or benchmark)
        const completed = (jobs || []).find(job => job.status === 'completed');
        // 2. Fall back to any available job in the system
        const anyJob = (jobs || [])[0];
        // 3. Absolute fallback to the benchmark reference dataset
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

  if (!targetId) {
    return (
      <div style={{ padding: 32, color: '#8898ae' }}>
        Loading {destination} view...
      </div>
    );
  }

  return <Navigate to={`/${destination}/${targetId}`} replace />;
}
