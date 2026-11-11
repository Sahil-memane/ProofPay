import { useLocation } from 'react-router-dom';

const PAGE_META = {
  '/dashboard':          { title: 'Dashboard',              sub: 'Escrow Prevent' },
  '/projects':           { title: 'Projects & Contracts',   sub: 'Escrow Prevent' },
  '/project-details':    { title: 'Project Details',        sub: 'Escrow Prevent' },
  '/milestones':         { title: 'Milestones',             sub: 'Escrow Prevent' },
  '/submissions':        { title: 'Submissions & Verification', sub: 'Escrow Prevent' },
  '/ledger':             { title: 'Escrow Ledger',          sub: 'Escrow Prevent' },
  '/recovery-overview':  { title: 'Recovery Overview',      sub: 'Revenue Recover' },
  '/cases':              { title: 'Recovery Cases',         sub: 'Revenue Recover' },
  '/invoices':           { title: 'Invoices',               sub: 'Revenue Recover' },
  '/payment-attempts':   { title: 'Payment Attempts',       sub: 'Revenue Recover' },
  '/reconciliation':     { title: 'Reconciliation (3-Way)', sub: 'Trust & Governance' },
  '/disputes':           { title: 'Disputes',               sub: 'Trust & Governance' },
  '/mandate-guard':      { title: 'Mandate Guard',          sub: 'Trust & Governance' },
  '/reputation':         { title: 'Reputation Ledger',      sub: 'Trust & Governance' },
  '/approvals':          { title: 'Approvals Queue (HITL)', sub: 'Trust & Governance' },
  '/agents':             { title: 'AI Agent Center',        sub: 'Intelligence' },
  '/analytics':          { title: 'Analytics & Reports',    sub: 'Intelligence' },
  '/audit':              { title: 'Audit Trail (SHA-256)',   sub: 'Intelligence' },
  '/assistant':          { title: 'AI Assistant',           sub: 'Intelligence' },
  '/pay':                { title: 'Pay',                    sub: 'System' },
  '/integrations':       { title: 'Integrations',           sub: 'System' },
  '/settings':           { title: 'Settings',               sub: 'System' },
  '/help':               { title: 'Help & Support',         sub: 'System' },
  '/create-project-wizard': { title: 'Create Project',      sub: 'Escrow Prevent' },
};

export function usePageMeta() {
  const { pathname } = useLocation();
  return PAGE_META[pathname] ?? { title: 'ProofPay', sub: '' };
}

