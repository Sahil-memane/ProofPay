/**
 * ProofPay API Client
 * Thin fetch wrapper around FastAPI backend.
 * Sends Authorization: Bearer mock-token-{email} on every request so the
 * backend can apply per-user data scoping.
 *
 * Production (Render): React SPA is served by the same FastAPI origin,
 * so BASE is '' (relative). Vite dev server proxy handles local dev.
 * Override with VITE_API_BASE env var if you need to point at a separate backend.
 */
const BASE = import.meta.env.VITE_API_BASE ?? '';

function qs(params) {
  if (!params) return '';
  const s = new URLSearchParams(params).toString();
  return s ? '?' + s : '';
}

/** Read the stored session from localStorage or sessionStorage. */
function getSession() {
  try {
    const raw = localStorage.getItem('pp_session') || sessionStorage.getItem('pp_session') || '{}';
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

/** Build auth headers from the current session token. */
function authHeaders() {
  const session = getSession();
  if (session.token) {
    return { Authorization: `Bearer ${session.token}` };
  }
  return {};
}

async function handleResponse(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get: (path, params) =>
    fetch(BASE + path + qs(params), {
      headers: { ...authHeaders() },
    }).then(handleResponse),

  post: (path, body) =>
    fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body ?? {}),
    }).then(handleResponse),

  patch: (path, body) =>
    fetch(BASE + path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body ?? {}),
    }).then(handleResponse),

  delete: (path) =>
    fetch(BASE + path, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    }).then(handleResponse),

  base: BASE,
};
