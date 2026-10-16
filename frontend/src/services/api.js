
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
  return apiRequest('/health');
}

export function createJob(files, language = 'cpp') {
  if (!Array.isArray(files) || files.length !== 4) {
    throw new Error('Exactly four source files are required.');
  }

  if (!['c', 'cpp'].includes(language)) {
    throw new Error('Language must be c or cpp.');
  }

  const formData = new FormData();
  formData.append('language', language);

  files.forEach((file) => {
    formData.append('files', file);
  });

  return apiRequest('/api/jobs', {
    method: 'POST',
    body: formData
  });
}

export function getJob(id) {
  if (!id) {
    throw new Error('Job ID is required.');
  }

  return apiRequest(
    `/api/jobs/${encodeURIComponent(id)}`
  );
}
export function getResults(id) {
  if (!id) {
    throw new Error('Job ID is required.');
  }

  return apiRequest(
    `/api/jobs/${encodeURIComponent(id)}/results`
  );
}

export function listJobs() {
  return apiRequest('/api/jobs');
}

export function getSystem() {
  return apiRequest('/api/system');
}
