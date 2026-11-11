import { useAuth } from '../../hooks/useAuth';
import styles from './Header.module.css';

export function Header({ title, subtitle }) {
  const { user, role, logout } = useAuth();

  const getRoleLabel = () => {
    switch (role) {
      case 'admin':
        return 'Risk Officer / Admin';
      case 'freelancer':
        return 'Freelancer';
      case 'merchant':
        return 'Merchant';
      case 'client':
      default:
        return 'Client (Buyer)';
    }
  };

  const getRoleBadgeClass = () => {
    switch (role) {
      case 'admin':
        return `${styles.roleBadge} ${styles.roleBadgeAdmin}`;
      case 'freelancer':
        return `${styles.roleBadge} ${styles.roleBadgeFreelancer}`;
      case 'merchant':
        return `${styles.roleBadge} ${styles.roleBadgeMerchant}`;
      case 'client':
      default:
        return styles.roleBadge;
    }
  };

  const displayName = user?.name || user?.email?.split('@')[0] || 'User';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <header className={styles.header}>
      <div className={styles.breadcrumb}>
        {subtitle && <div className={styles.subtitle}>{subtitle} /</div>}
        <div className={styles.title}>{title}</div>
      </div>

      <div className={styles.search}>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={styles.searchIcon}
          aria-hidden="true"
        >
          <path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5" />
        </svg>
        <label htmlFor="global-search" className="sr-only">
          Global search
        </label>
        <input
          id="global-search"
          className={styles.searchInput}
          placeholder="Search projects, cases, hashes (Ctrl+K)..."
        />
      </div>

      <div className={styles.actions}>
        {/* Role Badge (Fixed based on logged in user) */}
        <span className={getRoleBadgeClass()} title={`Active role: ${getRoleLabel()}`}>
          {getRoleLabel()}
        </span>

        {/* PayPal Sandbox Status Pill */}
        <span className={styles.statusPill}>
          <span className={styles.statusDot} />
          PayPal Sandbox: Connected
        </span>

        {/* User profile & Sign Out */}
        <div className={styles.userProfile}>
          <div className={styles.avatar} title={user?.email || displayName}>
            {initial}
          </div>
          <span className={styles.userName} title={user?.email || displayName}>
            {displayName}
          </span>
          <button
            type="button"
            className={styles.signOutBtn}
            onClick={logout}
            title="Sign out of ProofPay"
          >
            Sign Out
          </button>
        </div>
      </div>
    </header>
  );
}
