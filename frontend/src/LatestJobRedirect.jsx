import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { listJobs } from './services/api.js';

export default function LatestJobRedirect({ destination }) {
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    listJobs()
      .then(jobs => {
        if (!active) return;

        const latest = jobs.find(
          job => job.status === 'completed'
        );

        setJobId(latest?.jobId || null);
        setLoading(false);
      })
      .catch(err => {
        if (!active) return;
        setError(err.message);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <div style={{ padding: 32 }}>
      Loading latest completed job...
    </div>;
  }

  if (error) {
    return <div style={{ padding: 32 }}>
      Backend error: {error}
    </div>;
  }

  if (!jobId) {
    return <div style={{ padding: 32 }}>
      No completed jobs available.{' '}
      <Link to="/upload">Start an analysis</Link>
    </div>;
  }

  return <Navigate to={`/${destination}/${jobId}`} replace />;
}
