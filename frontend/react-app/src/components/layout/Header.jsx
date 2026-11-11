import { useState, useEffect } from 'react';
import styles from './Header.module.css';

const ROLES = ['Client (Buyer)', 'Freelancer (Contractor)', 'Merchant (Billing Admin)', 'Risk Officer / Admin'];

export function Header({ title, subtitle }) {
  const [role, setRole] = useState(() => localStorage.getItem('proofpay_role') ?? ROLES[3]);

  useEffect(() => {
    localStorage.setItem('proofpay_role', role);
    window.dispatchEvent(new CustomEvent('roleChanged', { detail: role }));
  }, [role]);

  return (
    <header className={styles.header}>
      <div className={styles.breadcrumb}>
        {subtitle && <div className={styles.subtitle}>{subtitle} /</div>}
        <div className={styles.title}>{title}</div>
      </div>

      <div className={styles.search}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={styles.searchIcon} aria-hidden="true">
          <path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5" />
        </svg>
        <label htmlFor="global-search" className="sr-only">Global search</label>
        <input id="global-search" className={styles.searchInput} placeholder="Search projects, cases, hashes (Ctrl+K)..." />
      </div>

      <div className={styles.actions}>
        <label htmlFor="role-select" className={styles.roleLabel}>Role</label>
        <select
          id="role-select"
          className={styles.roleSelect}
          value={role}
          onChange={e => setRole(e.target.value)}
        >
          {ROLES.map(r => <option key={r}>{r}</option>)}
        </select>

        <span className={styles.statusPill}>
          <span className={styles.statusDot} />
          PayPal Sandbox: Connected
        </span>

        <div className={styles.avatar}>S</div>
      </div>
    </header>
  );
}

