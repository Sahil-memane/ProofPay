import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ToastContainer } from './components/ui/Toast';

// Pages
import Landing          from './pages/Landing';
import Dashboard        from './pages/Dashboard';
import Projects         from './pages/Projects';
import ProjectDetails   from './pages/ProjectDetails';
import Milestones       from './pages/Milestones';
import Submissions      from './pages/Submissions';
import Approvals        from './pages/Approvals';
import Cases            from './pages/Cases';
import RecoveryOverview from './pages/RecoveryOverview';
import Reconciliation   from './pages/Reconciliation';
import MandateGuard     from './pages/MandateGuard';
import Analytics        from './pages/Analytics';
import Audit            from './pages/Audit';
import Reputation       from './pages/Reputation';
import Ledger           from './pages/Ledger';
import {
  Agents, Assistant, Disputes, Invoices, Pay,
  PaymentAttempts, Integrations, Settings, Help, CreateProjectWizard,
} from './pages/StubPages';

const ROUTES = [
  { path: '/dashboard',          el: <Dashboard />,        title: 'Dashboard',              sub: 'Escrow Prevent' },
  { path: '/projects',           el: <Projects />,          title: 'Projects & Contracts',   sub: 'Escrow Prevent' },
  { path: '/project-details',    el: <ProjectDetails />,    title: 'Project Details',        sub: 'Escrow Prevent' },
  { path: '/milestones',         el: <Milestones />,        title: 'Milestones',             sub: 'Escrow Prevent' },
  { path: '/submissions',        el: <Submissions />,       title: 'Submissions & Verification', sub: 'Escrow Prevent' },
  { path: '/ledger',             el: <Ledger />,            title: 'Escrow Ledger',          sub: 'Escrow Prevent' },
  { path: '/recovery-overview',  el: <RecoveryOverview />,  title: 'Recovery Overview',      sub: 'Revenue Recover' },
  { path: '/cases',              el: <Cases />,             title: 'Recovery Cases',         sub: 'Revenue Recover' },
  { path: '/invoices',           el: <Invoices />,          title: 'Invoices',               sub: 'Revenue Recover' },
  { path: '/payment-attempts',   el: <PaymentAttempts />,   title: 'Payment Attempts',       sub: 'Revenue Recover' },
  { path: '/reconciliation',     el: <Reconciliation />,    title: 'Reconciliation (3-Way)', sub: 'Trust & Governance' },
  { path: '/disputes',           el: <Disputes />,          title: 'Disputes',               sub: 'Trust & Governance' },
  { path: '/mandate-guard',      el: <MandateGuard />,      title: 'Mandate Guard',          sub: 'Trust & Governance' },
  { path: '/reputation',         el: <Reputation />,        title: 'Reputation Ledger',      sub: 'Trust & Governance' },
  { path: '/approvals',          el: <Approvals />,         title: 'Approvals Queue (HITL)', sub: 'Trust & Governance' },
  { path: '/agents',             el: <Agents />,            title: 'AI Agent Center',        sub: 'Intelligence' },
  { path: '/analytics',          el: <Analytics />,         title: 'Analytics & Reports',    sub: 'Intelligence' },
  { path: '/audit',              el: <Audit />,             title: 'Audit Trail (SHA-256)',   sub: 'Intelligence' },
  { path: '/assistant',          el: <Assistant />,         title: 'AI Assistant',           sub: 'Intelligence' },
  { path: '/pay',                el: <Pay />,               title: 'Pay',                    sub: 'System' },
  { path: '/integrations',       el: <Integrations />,      title: 'Integrations',           sub: 'System' },
  { path: '/settings',           el: <Settings />,          title: 'Settings',               sub: 'System' },
  { path: '/help',               el: <Help />,              title: 'Help & Support',         sub: 'System' },
  { path: '/create-project-wizard', el: <CreateProjectWizard />, title: 'Create Project',   sub: 'Escrow Prevent' },
];

function ShellRoute({ title, sub, children }) {
  return (
    <Routes>
      <Route element={<AppShell title={title} subtitle={sub} />}>
        <Route index element={children} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        {/* Landing — no shell */}
        <Route path="/" element={<Landing />} />

        {/* Shell routes */}
        <Route element={<AppShell title="ProofPay" subtitle="" />}>
          {ROUTES.map(r => (
            <Route
              key={r.path}
              path={r.path}
              element={
                // Pass title/subtitle via context — AppShell uses them from route
                // Simple approach: just render with AppShell, header gets updated per nav
                r.el
              }
            />
          ))}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
