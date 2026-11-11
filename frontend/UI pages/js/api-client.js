/**
 * ProofPay API Client
 * Thin fetch wrapper. Falls back to window.MOCK_DATA when backend is unreachable.
 */
(function (global) {
  'use strict';

  const API_BASE = 'http://localhost:8000';

  /**
   * GET request with JSON response.
   * Falls back to MOCK_DATA[path] on network failure.
   */
  async function apiGet(path, params) {
    let url = API_BASE + path;
    if (params && Object.keys(params).length > 0) {
      url += '?' + new URLSearchParams(params).toString();
    }
    try {
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn(`[ProofPayAPI] GET ${path} failed (${err.message}), using mock data`);
      if (global.MOCK_DATA && global.MOCK_DATA[path]) return global.MOCK_DATA[path];
      return null;
    }
  }

  /**
   * POST request with JSON body and response.
   */
  async function apiPost(path, body) {
    try {
      const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body || {}),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn(`[ProofPayAPI] POST ${path} failed:`, err.message);
      throw err;
    }
  }

  /**
   * PATCH request with JSON body and response.
   */
  async function apiPatch(path, body) {
    try {
      const res = await fetch(API_BASE + path, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body || {}),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn(`[ProofPayAPI] PATCH ${path} failed:`, err.message);
      throw err;
    }
  }

  global.ProofPayAPI = { get: apiGet, post: apiPost, patch: apiPatch, base: API_BASE };
})(window);

