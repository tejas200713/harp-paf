const USE_SAMPLES = import.meta.env.VITE_USE_SAMPLES === '1';

async function sample(name) {
  const response = await fetch(`/samples/${name}.json`);
  return response.json();
}

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '');

async function apiRequest(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (error) {
    throw new Error(
      `Cannot connect to HARP-PAF backend at ${API_BASE_URL}. ` +
      `Check that FastAPI is running. ${error.message}`
    );
  }

  const contentType = response.headers.get('content-type') || '';

  let data;

  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status})`;

    if (typeof data === 'object' && data !== null) {
      const detail = data.detail || data.error;

      message = typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : message;
    } else if (typeof data === 'string' && data.trim()) {
      message = data.slice(0, 300);
    }

    throw new Error(message);
  }

  return data;
}

export function checkHealth() {
  if (USE_SAMPLES) return sample('health');
  return apiRequest('/health');
}

export function createJob(files, language = 'cpp', repetitions = 5) {
  if (USE_SAMPLES) {
    return Promise.resolve({
      jobId: '609315c9a54f4a64b733cb9ff93e5478',
      status: 'running'
    });
  }

  if (!Array.isArray(files) || files.length < 2 || files.length > 16) {
    throw new Error('Between 2 and 16 source files are required.');
  }

  if (!['c', 'cpp'].includes(language)) {
    throw new Error('Language must be c or cpp.');
  }

  const formData = new FormData();
  formData.append('language', language);
  formData.append('repetitions', String(repetitions));

  files.forEach((file) => {
    formData.append('files', file);
  });

  return apiRequest('/api/jobs', {
    method: 'POST',
    body: formData
  });
}

export function getJob(id) {
  if (USE_SAMPLES) return sample('job');

  if (!id) {
    throw new Error('Job ID is required.');
  }

  return apiRequest(
    `/api/jobs/${encodeURIComponent(id)}`
  );
}

export function getResults(id) {
  if (USE_SAMPLES) return sample('results');

  if (!id) {
    throw new Error('Job ID is required.');
  }

  return apiRequest(
    `/api/jobs/${encodeURIComponent(id)}/results`
  );
}

export function listJobs() {
  if (USE_SAMPLES) return sample('jobs');
  return apiRequest('/api/jobs');
}

export function getSystem() {
  if (USE_SAMPLES) return sample('system');
  return apiRequest('/api/system');
}

export function getWorkloads() {
  if (USE_SAMPLES) return sample('workloads');
  return apiRequest('/api/workloads');
}
