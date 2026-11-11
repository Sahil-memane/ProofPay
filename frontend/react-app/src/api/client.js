/**
 * ProofPay API Client
 * Thin fetch wrapper around FastAPI backend.
 */
const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

function qs(params) {
  if (!params) return '';
  const s = new URLSearchParams(params).toString();
  return s ? '?' + s : '';
}

async function handleResponse(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get:   (path, params) => fetch(BASE + path + qs(params)).then(handleResponse),
  post:  (path, body)   => fetch(BASE + path, { method: 'POST',  headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) }).then(handleResponse),
  patch: (path, body)   => fetch(BASE + path, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) }).then(handleResponse),
  delete:(path)         => fetch(BASE + path, { method: 'DELETE' }).then(handleResponse),
  base: BASE,
};

