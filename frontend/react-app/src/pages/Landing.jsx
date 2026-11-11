import { useNavigate } from 'react-router-dom';
import styles from './Landing.module.css';

export default function Landing() {
  const navigate = useNavigate();
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4" />
            </svg>
          </div>
          <span className={styles.logoText}>ProofPay</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            style={{
              background: 'transparent',
              border: 'none',
              color: '#BFD3F2',
              fontSize: 14,
              fontWeight: 500,
              cursor: 'pointer',
              padding: '8px 12px',
            }}
            onClick={() => navigate('/login')}
          >
            Sign In
          </button>
          <button className={styles.ctaBtn} onClick={() => navigate('/dashboard')}>Open Dashboard →</button>
        </div>
      </header>

      <main className={styles.hero}>
        <div className={styles.badge}>🏆 PayPal AI Hackathon 2026</div>
        <h1 className={styles.heroTitle}>AI-Powered Escrow &amp;<br />Revenue Recovery</h1>
        <p className={styles.heroSub}>
          ProofPay combines autonomous failed-payment recovery with cryptographic freelance escrow —
          all powered by LangGraph agents and PayPal APIs.
        </p>
        <div className={styles.heroBtns}>
          <button className={styles.primaryBtn} onClick={() => navigate('/dashboard')}>View Dashboard</button>
          <button className={styles.secondaryBtn} onClick={() => navigate('/analytics')}>See Benchmark Results</button>
        </div>

        {/* Stats */}
        <div className={styles.stats}>
          {[
            ['28.67%', 'Agent Recovery Rate', 'vs 8% baseline'],
            ['3.58×', 'More Revenue Recovered', '$11,010 vs $2,560'],
            ['0%', 'Wrongful Contacts', '100% precision'],
            ['$200', 'Mandate Guard Cap', 'Human-in-the-Loop above'],
          ].map(([v, l, s]) => (
            <div key={l} className={styles.stat}>
              <div className={styles.statValue}>{v}</div>
              <div className={styles.statLabel}>{l}</div>
              <div className={styles.statSub}>{s}</div>
            </div>
          ))}
        </div>
      </main>

      {/* Engines */}
      <section className={styles.engines}>
        <div className={styles.engine}>
          <div className={styles.engineTag}>Engine 1 — PREVENT</div>
          <h2>Freelance Escrow</h2>
          <ul>
            <li>Dual cryptographic plan approval (SHA-256)</li>
            <li>Milestone-based payment release</li>
            <li>AI work verification (LangGraph verifier)</li>
            <li>Mandate Guard policy gating</li>
            <li>PayPal Orders v2 + Payouts</li>
          </ul>
        </div>
        <div className={styles.engine}>
          <div className={styles.engineTag} style={{ background: '#FFF8E1', color: '#8A5A00' }}>Engine 2 — RECOVER</div>
          <h2>Revenue Recovery</h2>
          <ul>
            <li>3-stage autonomous contact ladder</li>
            <li>Root-cause diagnosis (LangGraph)</li>
            <li>3-way reconciliation (ProofPay ↔ PayPal ↔ Bank)</li>
            <li>Quiet-hours & TCPA compliance</li>
            <li>28.67% recovery vs 8% baseline</li>
          </ul>
        </div>
      </section>

      <footer className={styles.footer}>
        <span>AI recommends. Policy decides. PayPal executes. Every action is auditable.</span>
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API Docs →</a>
      </footer>
    </div>
  );
}

