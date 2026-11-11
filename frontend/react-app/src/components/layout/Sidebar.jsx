import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';

function NavIcon({ d }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

function NavGroup({ label }) {
  return <div className={styles.group}>{label}</div>;
}

function NavItem({ to, icon, label, badge }) {
  return (
    <NavLink to={to} className={({ isActive }) => `${styles.item} ${isActive ? styles.active : ''}`}>
      <NavIcon d={icon} />
      <span className={styles.label}>{label}</span>
      {badge != null && <span className={styles.badge}>{badge}</span>}
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      {/* Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4" />
          </svg>
        </div>
        <span className={styles.logoText}>ProofPay</span>
      </div>

      <nav aria-label="Main" className={styles.nav}>
        <NavGroup label="ESCROW PREVENT" />
        <NavItem to="/dashboard"      icon="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"  label="Dashboard" />
        <NavItem to="/projects"       icon="M3 6a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" label="Projects" />
        <NavItem to="/project-details" icon="M4 4h16v16H4zM8 9h8M8 13h5" label="Project Details" />
        <NavItem to="/milestones"     icon="M5 21V4M5 4h12l-2 4 2 4H5" label="Milestones" />
        <NavItem to="/submissions"    icon="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM9 14l2 2 4-4" label="Submissions" />
        <NavItem to="/ledger"         icon="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19a2 2 0 0 0 2 2h13" label="Escrow Ledger" />

        <NavGroup label="REVENUE RECOVER" />
        <NavItem to="/recovery-overview"  icon="M3 17l6-6 4 4 8-8M15 7h6v6" label="Recovery Overview" />
        <NavItem to="/cases"              icon="M3 8h18v12H3zM9 8V5h6v3"    label="Recovery Cases" />
        <NavItem to="/invoices"           icon="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" label="Invoices" />
        <NavItem to="/payment-attempts"   icon="M3 6h18v12H3zM3 10h18"       label="Payment Attempts" />

        <NavGroup label="TRUST & GOVERNANCE" />
        <NavItem to="/reconciliation" icon="M4 8h14l-3-3M20 16H6l3 3"      label="Reconciliation" />
        <NavItem to="/disputes"       icon="M12 3l10 18H2zM12 10v5M12 18h.01" label="Disputes" />
        <NavItem to="/mandate-guard"  icon="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" label="Mandate Guard" />
        <NavItem to="/reputation"     icon="M12 3l2.8 5.8 6.2.9-4.5 4.4 1 6.2-5.5-3-5.5 3 1-6.2L3 9.7l6.2-.9z" label="Reputation Ledger" />
        <NavItem to="/approvals"      icon="M9 4h6v3H9zM6 5H5v16h14V5h-1M9 14l2 2 4-4" label="Approvals Queue (HITL)" />

        <NavGroup label="INTELLIGENCE" />
        <NavItem to="/agents"    icon="M5 8h14v10H5zM12 8V4M9 13h.01M15 13h.01" label="AI Agent Center" />
        <NavItem to="/analytics" icon="M5 21V10M12 21V4M19 21v-8"               label="Analytics & Reports" />
        <NavItem to="/audit"     icon="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" label="Audit Trail (SHA-256)" />
        <NavItem to="/assistant" icon="M4 5h16v11H9l-5 4z"                       label="AI Assistant" />

        <NavGroup label="SYSTEM" />
        <NavItem to="/pay"          icon="M3 6h18v12H3zM3 10h18"             label="Pay" />
        <NavItem to="/integrations" icon="M9 3v5M15 3v5M6 8h12v4a6 6 0 0 1-12 0zM12 18v3" label="Integrations" />
        <NavItem to="/settings"     icon="M4 7h10M18 7h2M4 17h2M10 17h10M14 5v4M6 15v4"   label="Settings" />
        <NavItem to="/help"         icon="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.7M12 17h.01" label="Help & Support" />
      </nav>
    </aside>
  );
}

