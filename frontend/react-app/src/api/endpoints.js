/**
 * Named API endpoint helpers.
 * Import { endpoints } from '@/api/endpoints' and call endpoints.dashboard.headline()
 */
import { api } from './client';

export const endpoints = {
  health: {
    get: () => api.get('/healthz'),
  },
  dashboard: {
    headline: () => api.get('/dashboard/headline'),
  },
  eval: {
    latest: () => api.get('/eval/latest'),
  },
  audit: {
    list: (params) => api.get('/audit', params),
  },
  projects: {
    list:    ()        => api.get('/projects'),
    get:     (id)      => api.get(`/projects/${id}`),
    create:  (body)    => api.post('/projects', body),
    approve: (id, body)=> api.post(`/projects/${id}/approve`, body),
    fund:    (id)      => api.post(`/projects/${id}/fund`, {}),
    capture: (id, body)=> api.post(`/projects/${id}/capture`, body),
  },
  milestones: {
    patch: (id, body) => api.patch(`/milestones/${id}`, body),
  },
  submissions: {
    list:    ()                  => api.get('/submissions'),
    submit:  (milestoneId, body) => api.post(`/milestones/${milestoneId}/submit`, body),
    get:     (milestoneId)       => api.get(`/milestones/${milestoneId}/submission`),
    review:  (milestoneId, body) => api.post(`/milestones/${milestoneId}/review`, body),
    refund:  (milestoneId)       => api.post(`/milestones/${milestoneId}/refund`, {}),
    inject:  (milestoneId, body) => api.post(`/milestones/${milestoneId}/_inject_verification`, body),
  },
  approvals: {
    submissions: {
      list:   () => api.get('/submission-approvals'),
      decide: (taskId, body) => api.post(`/submission-approvals/${taskId}/decide`, body),
    },
    cases: {
      list:   () => api.get('/approvals'),
      decide: (caseId, body) => api.post(`/approvals/${caseId}/decide`, body),
    },
  },
  cases: {
    list:   (params) => api.get('/cases', params),
    get:    (id)     => api.get(`/cases/${id}`),
    reopen: (id)     => api.post(`/cases/${id}/reopen`, {}),
  },
  reconciliation: {
    summary: () => api.get('/reconciliation/summary'),
    outbox:  () => api.get('/outbox'),
  },
  reputation: {
    get: (subject) => api.get(`/reputation/${subject}`),
    all: () => api.get('/reputation'),
  },
  invoices: {
    list: (params) => api.get('/invoices', params),
    create: (body) => api.post('/invoices', body),
  },
  paymentAttempts: {
    list: (params) => api.get('/payment-attempts', params),
  },
  reconciliationRecords: {
    list: (params) => api.get('/reconciliation', params),
  },
  ledger: {
    list: (params) => api.get('/ledger', params),
  },
  customers: {
    list: (params) => api.get('/customers', params),
  },
  milestonesList: {
    list: (params) => api.get('/milestones', params),
  },
  analytics: {
    summary: () => api.get('/analytics/summary'),
  },
  disputes: {
    list: (params) => api.get('/disputes', params),
  },
  recovery: {
    overview: () => api.get('/recovery/overview'),
  },
  auditLog: {
    list: (params) => api.get('/audit-log', params),
  },
  webhookEvents: {
    list: (params) => api.get('/webhook-events', params),
  },
  merchantSales: {
    list: (params) => api.get('/merchant-sales', params),
  },
  settings: {
    policy:  () => api.get('/settings/policy'),
    users:   () => api.get('/settings/users'),
  },
  sim: {
    events: (body) => api.post('/sim/events', body),
  },
  demo: {
    injectFailure:  (body) => api.post('/demo/inject-failure', body),
    advanceClock:   (body) => api.post('/demo/advance-clock', body),
    runSimulator:   (body) => api.post('/demo/run-simulator', body),
    reset:          ()     => api.post('/demo/reset', {}),
  },
  fixtures: {
    customers: () => api.get('/fixtures/customers'),
    invoices:  () => api.get('/fixtures/invoices'),
    escrow:    () => api.get('/fixtures/escrow'),
  },
};
