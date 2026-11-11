import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ToastContainer } from './components/ui/Toast';
import { PageLoader } from './components/ui/Spinner';

// ── Lazy-loaded pages (code splitting → small initial bundle) ─────────────
const Landing             = lazy(() => import('./pages/Landing'));
const Login               = lazy(() => import('./pages/Login'));
const Dashboard           = lazy(() => import('./pages/Dashboard'));
const Projects            = lazy(() => import('./pages/Projects'));
const ProjectDetails      = lazy(() => import('./pages/ProjectDetails'));
const Milestones          = lazy(() => import('./pages/Milestones'));
const Submissions         = lazy(() => import('./pages/Submissions'));
const Approvals           = lazy(() => import('./pages/Approvals'));
const Cases               = lazy(() => import('./pages/Cases'));
const RecoveryOverview    = lazy(() => import('./pages/RecoveryOverview'));
const Reconciliation      = lazy(() => import('./pages/Reconciliation'));
const MandateGuard        = lazy(() => import('./pages/MandateGuard'));
const Analytics           = lazy(() => import('./pages/Analytics'));
const Audit               = lazy(() => import('./pages/Audit'));
const Reputation          = lazy(() => import('./pages/Reputation'));
const Ledger              = lazy(() => import('./pages/Ledger'));
const Disputes            = lazy(() => import('./pages/Disputes'));
const Pay                 = lazy(() => import('./pages/Pay'));
const Invoices            = lazy(() => import('./pages/Invoices'));
const PaymentAttempts     = lazy(() => import('./pages/PaymentAttempts'));
const Agents              = lazy(() => import('./pages/Agents'));
const Assistant           = lazy(() => import('./pages/Assistant'));
const Integrations        = lazy(() => import('./pages/Integrations'));
const Settings            = lazy(() => import('./pages/Settings'));
const Help                = lazy(() => import('./pages/Help'));
const CreateProjectWizard = lazy(() => import('./pages/CreateProjectWizard'));

// Fallback while a chunk loads
function Loading() { return <PageLoader />; }

export default function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        {/* Public pages — no shell */}
        <Route path="/" element={
          <Suspense fallback={<Loading />}><Landing /></Suspense>
        } />
        <Route path="/login" element={
          <Suspense fallback={<Loading />}><Login /></Suspense>
        } />
        <Route path="/register" element={
          <Suspense fallback={<Loading />}><Login /></Suspense>
        } />

        {/* All app pages inside AppShell */}
        <Route element={<AppShell />}>
          <Route path="/dashboard"             element={<Suspense fallback={<Loading />}><Dashboard /></Suspense>} />
          <Route path="/projects"              element={<Suspense fallback={<Loading />}><Projects /></Suspense>} />
          <Route path="/project-details"       element={<Suspense fallback={<Loading />}><ProjectDetails /></Suspense>} />
          <Route path="/milestones"            element={<Suspense fallback={<Loading />}><Milestones /></Suspense>} />
          <Route path="/submissions"           element={<Suspense fallback={<Loading />}><Submissions /></Suspense>} />
          <Route path="/ledger"                element={<Suspense fallback={<Loading />}><Ledger /></Suspense>} />
          <Route path="/recovery-overview"     element={<Suspense fallback={<Loading />}><RecoveryOverview /></Suspense>} />
          <Route path="/cases"                 element={<Suspense fallback={<Loading />}><Cases /></Suspense>} />
          <Route path="/invoices"              element={<Suspense fallback={<Loading />}><Invoices /></Suspense>} />
          <Route path="/payment-attempts"      element={<Suspense fallback={<Loading />}><PaymentAttempts /></Suspense>} />
          <Route path="/reconciliation"        element={<Suspense fallback={<Loading />}><Reconciliation /></Suspense>} />
          <Route path="/disputes"              element={<Suspense fallback={<Loading />}><Disputes /></Suspense>} />
          <Route path="/mandate-guard"         element={<Suspense fallback={<Loading />}><MandateGuard /></Suspense>} />
          <Route path="/reputation"            element={<Suspense fallback={<Loading />}><Reputation /></Suspense>} />
          <Route path="/approvals"             element={<Suspense fallback={<Loading />}><Approvals /></Suspense>} />
          <Route path="/agents"                element={<Suspense fallback={<Loading />}><Agents /></Suspense>} />
          <Route path="/analytics"             element={<Suspense fallback={<Loading />}><Analytics /></Suspense>} />
          <Route path="/audit"                 element={<Suspense fallback={<Loading />}><Audit /></Suspense>} />
          <Route path="/assistant"             element={<Suspense fallback={<Loading />}><Assistant /></Suspense>} />
          <Route path="/pay"                   element={<Suspense fallback={<Loading />}><Pay /></Suspense>} />
          <Route path="/integrations"          element={<Suspense fallback={<Loading />}><Integrations /></Suspense>} />
          <Route path="/settings"              element={<Suspense fallback={<Loading />}><Settings /></Suspense>} />
          <Route path="/help"                  element={<Suspense fallback={<Loading />}><Help /></Suspense>} />
          <Route path="/create-project-wizard" element={<Suspense fallback={<Loading />}><CreateProjectWizard /></Suspense>} />
        </Route>

        {/* Catch-all → dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
