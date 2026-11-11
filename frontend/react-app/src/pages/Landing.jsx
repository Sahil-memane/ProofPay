import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import styles from './Landing.module.css';

export default function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const handleAuthNavigation = (targetPath = '/dashboard') => {
    if (isAuthenticated) {
      navigate(targetPath);
    } else {
      navigate('/login', { state: { from: { pathname: targetPath } } });
    }
  };

  return (
    <div className={styles.page}>
      {/* ── Top Header ────────────────────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" className={styles.brand}>
            <svg width="30" height="30" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect width="32" height="32" rx="8" fill="#0070E0" />
              <path
                d="M16 6l8 3v6c0 5-3.4 8.6-8 10.5C11.4 23.6 8 20 8 15V9l8-3z"
                stroke="#fff"
                strokeWidth="2"
                strokeLinejoin="round"
              />
              <path
                d="M12.5 15.5l2.5 2.5 4.5-5"
                stroke="#fff"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            ProofPay
          </Link>

          <div className={styles.pby}>
            Powered by <strong>PayPal</strong>
          </div>

          <nav className={styles.nav}>
            <a className={styles.navLink} href="#benchmarks">
              Benchmarks
            </a>
            <a className={styles.navLink} href="#engines">
              Engines
            </a>
            <a className={styles.navLink} href="#trust">
              Trust
            </a>

            {isAuthenticated ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ color: '#C5D3F0', fontSize: 13, fontWeight: 500 }}>
                  {user?.name || user?.email?.split('@')[0]}
                </span>
                <Link
                  to="/dashboard"
                  className={styles.btnOpenDashboard}
                  style={{ textDecoration: 'none' }}
                >
                  Dashboard →
                </Link>
                <button
                  type="button"
                  className={styles.btnSignInNav}
                  onClick={logout}
                  style={{ padding: '6px 12px', fontSize: 13 }}
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Link
                  to="/login"
                  className={styles.btnSignInNav}
                  style={{ textDecoration: 'none' }}
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  className={styles.btnOpenDashboard}
                  style={{ textDecoration: 'none' }}
                >
                  Open Dashboard →
                </Link>
              </div>
            )}
          </nav>
        </div>
      </header>

      {/* ── Hero Section ──────────────────────────────────────────── */}
      <section className={styles.heroSection}>
        <div className={styles.heroInner}>
          <div>
            <h1 className={styles.heroTitle}>AI-Powered Escrow &amp; Revenue Recovery</h1>
            <p className={styles.heroSub}>
              ProofPay combines autonomous failed-payment recovery with cryptographic freelance escrow
              — all powered by LangGraph agents and PayPal APIs.
            </p>
            <div className={styles.heroBtns}>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={() => handleAuthNavigation('/dashboard')}
              >
                View Dashboard
              </button>
              <a className={styles.btnSecondary} href="#benchmarks">
                See Benchmark Results
              </a>
            </div>
            <div className={styles.planHashTag}>
              plan_hash: 9f2c…e41a · SHA-256 verified
            </div>
          </div>

          {/* Mandate Guard Live Decisions Card */}
          <div className={styles.liveCard}>
            <div className={styles.liveCardHeader}>
              <span className={styles.liveCardTitle}>Mandate Guard · Live decisions</span>
              <span className={styles.badgeConnected}>PayPal Sandbox: Connected</span>
            </div>
            <div className={styles.liveCardBody}>
              <div className={styles.liveRow}>
                <div>
                  <div className={styles.rowTitle}>Milestone 1 payout</div>
                  <div className={styles.rowSub}>PRJ-2026-001 · UI Design &amp; Figma Tokens</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className={styles.rowAmount}>$400.00 USD</div>
                  <span className={styles.statusPillPaid}>PAID</span>
                </div>
              </div>

              <div className={styles.liveRow}>
                <div>
                  <div className={styles.rowTitle}>Milestone 2 payout</div>
                  <div className={styles.rowSub}>Over $200.00 limit → Approvals task APP-104</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className={styles.rowAmount}>$700.00 USD</div>
                  <span className={styles.statusPillAwaiting}>AWAITING_APPROVAL</span>
                </div>
              </div>

              <div className={styles.liveRow}>
                <div>
                  <div className={styles.rowTitle}>Recovery REC-2026-0042</div>
                  <div className={styles.rowSub}>Sarah Johnson · EXPIRED_CARD · update link sent</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className={styles.rowAmount}>$350.00 USD</div>
                  <span className={styles.statusPillActive}>ACTIVE</span>
                </div>
              </div>

              <div className={styles.liveRow}>
                <div>
                  <div className={styles.rowTitle}>Michael Anderson</div>
                  <div className={styles.rowSub}>Bank wire matched · outreach halted</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className={styles.rowAmount}>$450.00 USD</div>
                  <span className={styles.statusPillPaidElsewhere}>PAID_ELSEWHERE</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Benchmarks KPI Section ────────────────────────────────── */}
      <section id="benchmarks" className={styles.benchmarksSection}>
        <div className={styles.benchmarksGrid}>
          <div className={styles.benchmarkCard}>
            <div className={styles.metricValue} style={{ color: '#0070E0' }}>
              28.67%
            </div>
            <div className={styles.metricTitle}>Agent Recovery Rate</div>
            <div className={styles.metricSub}>vs 8% baseline</div>
          </div>

          <div className={styles.benchmarkCard}>
            <div className={styles.metricValue} style={{ color: '#0070E0' }}>
              3.58×
            </div>
            <div className={styles.metricTitle}>More Revenue Recovered</div>
            <div className={styles.metricSub}>$11,010 vs $2,560</div>
          </div>

          <div className={styles.benchmarkCard}>
            <div className={styles.metricValue} style={{ color: '#1E7A4C' }}>
              0%
            </div>
            <div className={styles.metricTitle}>Wrongful Contacts</div>
            <div className={styles.metricSub}>100% precision</div>
          </div>

          <div className={styles.benchmarkCard}>
            <div className={styles.metricValue} style={{ color: '#003087' }}>
              $200
            </div>
            <div className={styles.metricTitle}>Mandate Guard Cap</div>
            <div className={styles.metricSub}>Human-in-the-Loop above</div>
          </div>
        </div>
      </section>

      {/* ── Built on PayPal Business APIs Banner ─────────────────── */}
      <section className={styles.apisBannerSection}>
        <div className={styles.apisBanner}>
          <div className={styles.apisLabel}>
            Built on <strong>PayPal</strong> business APIs
          </div>
          <div className={styles.apiChips}>
            <span className={styles.apiChip}>Checkout Orders v2</span>
            <span className={styles.apiChip}>Payouts API</span>
            <span className={styles.apiChip}>Smart Payment Buttons</span>
            <span className={styles.apiChip}>Webhooks &amp; Disputes</span>
          </div>
        </div>
      </section>

      {/* ── Two Engines Section ───────────────────────────────────── */}
      <section id="engines" className={styles.enginesSection}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Two engines. One deterministic trust layer.</h2>
          <p className={styles.sectionSub}>
            Prevent non-payment before it happens. Recover it, safely, when it does.
          </p>
        </div>

        <div className={styles.enginesGrid}>
          {/* Engine 1: Freelance Escrow */}
          <div className={`${styles.engineCard} ${styles.engineCardEscrow}`}>
            <div className={styles.engineCategoryEscrow}>ENGINE 1 · PREVENT</div>
            <h3 className={styles.engineTitle}>Freelance Escrow</h3>
            <div className={styles.featureList}>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E3F2FD" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#0070E0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Dual cryptographic plan approval (SHA-256)</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E3F2FD" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#0070E0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Milestone-based payment release</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E3F2FD" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#0070E0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>AI work verification (LangGraph verifier)</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E3F2FD" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#0070E0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Mandate Guard policy gating</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E3F2FD" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#0070E0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>PayPal Orders v2 + Payouts</span>
              </div>
            </div>
            <button
              type="button"
              className={`${styles.btnExplore} ${styles.btnExploreEscrow}`}
              onClick={() => handleAuthNavigation('/projects')}
            >
              Explore escrow →
            </button>
          </div>

          {/* Engine 2: Revenue Recovery */}
          <div className={`${styles.engineCard} ${styles.engineCardRecovery}`}>
            <div className={styles.engineCategoryRecovery}>ENGINE 2 · RECOVER</div>
            <h3 className={styles.engineTitle}>Revenue Recovery</h3>
            <div className={styles.featureList}>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E1F4FC" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#00709F" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>3-stage autonomous contact ladder</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E1F4FC" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#00709F" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Root-cause diagnosis (LangGraph)</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E1F4FC" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#00709F" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>3-way reconciliation (ProofPay ↔ PayPal ↔ Bank)</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E1F4FC" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#00709F" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Quiet-hours &amp; TCPA compliance</span>
              </div>
              <div className={styles.featureItem}>
                <svg className={styles.featureIcon} width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="8" fill="#E1F4FC" />
                  <path d="M4.5 8.3l2.2 2.2 4.5-4.7" stroke="#00709F" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>28.67% recovery vs 8% baseline</span>
              </div>
            </div>
            <button
              type="button"
              className={`${styles.btnExplore} ${styles.btnExploreRecovery}`}
              onClick={() => handleAuthNavigation('/recovery-overview')}
            >
              Explore recovery →
            </button>
          </div>
        </div>
      </section>

      {/* ── Trust Section ─────────────────────────────────────────── */}
      <section id="trust" className={styles.trustSection}>
        <div className={styles.trustBox}>
          <div className={styles.trustTag}>TRUST &amp; TECHNOLOGY</div>
          <p className={styles.trustQuote}>
            AI recommends. Policy decides. PayPal executes. Every action is auditable.
          </p>
          <div className={styles.trustActions}>
            <a
              className={styles.btnApiDocs}
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
            >
              API Docs →
            </a>
            {!isAuthenticated && (
              <button
                type="button"
                className={styles.btnTrustLogin}
                onClick={() => navigate('/login')}
              >
                Sign In to Workspace
              </button>
            )}
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <span>
            <strong style={{ color: '#172B4D' }}>ProofPay</strong> — Every Payment. Proven. Protected.
          </span>
          <span>
            Secure milestones. Recover revenue. Trust every transaction. · Powered by{' '}
            <strong style={{ color: '#003087' }}>PayPal</strong>
          </span>
        </div>
      </footer>
    </div>
  );
}
