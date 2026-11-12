import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import styles from './Dashboard.module.css';

const ICON = {
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  check: 'M5 12l5 5 9-10',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
  recovery: 'M3 17l6-6 4 4 8-8M15 7h6v6',
  invoice: 'M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6',
  shieldCheck: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4',
  arrow: 'M3 12h14M13 6l6 6-6 6',
  pause: 'M8 5v14M16 5v14',
  ban: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM5.6 5.6l12.8 12.8',
};

function Svg({ d, size = 18, color }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color || 'currentColor'} strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

function Badge({ cls, children }) {
  return <span className={`${styles.bd} ${styles[cls]}`}>{children}</span>;
}

function Ico({ d, amber }) {
  return (
    <span className={styles.ico} style={amber ? { background: '#FEF1D9', color: '#8A5A00' } : {}}>
      <Svg d={d} />
    </span>
  );
}

const fmt = (n) =>
  '$' + Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [dateRange, setDateRange] = useState('30');
  const { data: headline } = useApi(() => endpoints.dashboard.headline());
  const { data: audit } = useApi(() => endpoints.audit.list({ limit: 6 }));
  const { data: approvals } = useApi(() => endpoints.approvals.submissions.list());

  const hl = headline ?? {};
  const recoveredAmt = hl.recovered_amount ?? 562;
  const atRisk = hl.at_risk_amount ?? 824;
  const remaining = hl.remaining_at_risk ?? Math.max(0, atRisk - recoveredAmt);
  const recoveryRate = hl.recovery_rate ?? (atRisk > 0 ? Math.round((recoveredAmt / atRisk) * 100) : 68);
  const caseCt = hl.case_count ?? 3;
  const recoveredCt = hl.recovered_count ?? 2;
  const totalEscrowed = hl.total_escrowed ?? 4281;
  const releasedAmount = hl.released_amount ?? 1618;
  const pendingEscrow = hl.pending_escrow ?? 2663;
  const activeProjects = hl.active_projects ?? 2;
  const disputesCount = hl.disputes_count ?? 1;

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const displayName = user?.name || user?.email?.split('@')[0] || 'Sahil';

  const defaultActivity = [
    { icon: 'shield', text: 'Project', bold: '#PRJ-102', suffix: ' funded', badge: 'g', label: 'Funded', time: '2 min ago' },
    { icon: 'check', text: 'Milestone', bold: '#MS-204', suffix: ' verified', badge: 'g', label: 'Verified', time: '18 min ago' },
    { icon: 'arrow', text: 'Payout of', bold: '$450', suffix: ' released', badge: 'g', label: 'Released', time: '42 min ago' },
    { icon: 'recovery', text: 'Invoice', bold: '#INV-1024', suffix: ' recovered', badge: 'g', label: 'Recovered', time: '1 hr ago' },
    { icon: 'pause', text: 'Recovery case', bold: '#REC-42', suffix: ' halted', badge: 'a', label: 'Halted', time: '3 hr ago', amber: true },
    { icon: 'ban', text: 'Policy blocked a release of', bold: '$850', suffix: '', badge: 'r', label: 'Blocked', time: 'Yesterday', red: true },
  ];

  const activityItems = (audit && Array.isArray(audit) && audit.length > 0)
    ? audit.slice(0, 6).map(e => ({
        icon: e.event_type?.includes('capture') ? 'shield' : (e.event_type?.includes('payout') || e.event_type?.includes('release') ? 'arrow' : 'check'),
        text: e.actor || 'System',
        bold: e.event_type?.replace(/_/g, ' ') || 'Audit event',
        suffix: e.subject ? ` · ${String(e.subject).slice(0, 12)}` : '',
        badge: e.event_type?.includes('denied') || e.event_type?.includes('blocked') ? 'r' : 'g',
        label: e.event_type?.includes('denied') || e.event_type?.includes('blocked') ? 'Blocked' : 'Verified',
        time: e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recently'
      }))
    : defaultActivity;

  return (
    <div className={styles.page}>
      {/* Page heading */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>{greeting}, {displayName}</h1>
          <p className={styles.sub}>Here's what's happening across your payments today.</p>
        </div>
        <div className={styles.headerActions}>
          <select className={styles.btn} value={dateRange} onChange={e => setDateRange(e.target.value)}>
            <option value="30">Last 30 days</option>
            <option value="7">Last 7 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <button className={styles.btn} onClick={() => navigate('/analytics')}>View Reports</button>
          <button className={styles.btn} onClick={() => navigate('/invoices')}>Create Invoice</button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={() => navigate('/projects/new')}>Create Project</button>
        </div>
      </div>

      {/* Approvals banner */}
      {approvals && approvals.length > 0 && (
        <div className={styles.banner}>
          ⚠️ <strong>{approvals.length} pending human approvals</strong> in the HITL queue —{' '}
          <a href="/approvals">Review now →</a>
        </div>
      )}

      {/* Dark hero banner */}
      <section className={styles.hero}>
        <div className={styles.heroLeft}>
          <div className={styles.heroLabel}>Revenue Recovered</div>
          <div className={styles.heroAmount}>${recoveredAmt.toLocaleString()}</div>
          <div className={styles.heroSub}>Recovered ${recoveredAmt.toLocaleString()} of ${atRisk.toLocaleString()} at risk</div>
          <div className={styles.progressBar}>
            <div className={styles.progressFill} style={{ width: `${recoveryRate}%` }} />
          </div>
          <a href="/recovery-overview" className={styles.heroLink}>View Recovery Details →</a>
        </div>
        <div className={styles.heroStats}>
          <div><div className={styles.heroStatLabel}>Total at risk</div><div className={styles.heroStatVal}>${atRisk.toLocaleString()}</div></div>
          <div><div className={styles.heroStatLabel}>Recovered</div><div className={styles.heroStatVal}>${recoveredAmt.toLocaleString()}</div></div>
          <div><div className={styles.heroStatLabel}>Remaining at risk</div><div className={styles.heroStatVal}>${remaining.toLocaleString()}</div></div>
          <div><div className={styles.heroStatLabel}>Recovery rate</div><div className={styles.heroStatVal}>{recoveryRate}%</div></div>
          <div><div className={styles.heroStatLabel}>Recovery cases</div><div className={styles.heroStatVal}>{caseCt}</div></div>
        </div>
      </section>

      {/* KPI cards */}
      <section className={styles.kpiGrid} aria-label="Key metrics">
        {[
          { label: 'Total Escrowed', val: fmt(totalEscrowed), sub: `${activeProjects} projects active`, link: '/ledger', linkTxt: 'Escrow Ledger →', ico: 'shield' },
          { label: 'Released to Freelancers', val: fmt(releasedAmount), sub: 'Released via PayPal Payouts', link: '/milestones', linkTxt: 'Milestones →', ico: 'check' },
          { label: 'Pending Escrow', val: fmt(pendingEscrow), sub: 'Secured in PayPal vault', link: '/projects', linkTxt: 'Projects →', ico: 'clock' },
          { label: 'Revenue Recovered', val: fmt(recoveredAmt), sub: `${recoveryRate}% recovery rate`, link: '/recovery-overview', linkTxt: 'Recovery Overview →', ico: 'recovery' },
          { label: 'Outstanding Payments', val: fmt(remaining), sub: `${Math.max(0, caseCt - recoveredCt)} active cases`, link: '/cases', linkTxt: 'Recovery Cases →', ico: 'invoice', amber: remaining > 0 },
          { label: 'Disputes Status', val: String(disputesCount), sub: disputesCount > 0 ? `${disputesCount} under arbitration` : 'All clear', link: '/disputes', linkTxt: 'Disputes →', ico: 'shieldCheck', amber: disputesCount > 0 },
        ].map(c => (
          <div key={c.label} className={styles.kpiCard}>
            <div className={styles.kpiTop}>
              <span className={styles.kpiLabel}>{c.label}</span>
              <Ico d={ICON[c.ico]} amber={c.amber} />
            </div>
            <div className={styles.kpiVal}>{c.val}</div>
            <div className={styles.kpiSub} style={{ color: c.amber ? undefined : '#1E7A4C' }}>{c.sub}</div>
            <div style={{ marginTop: 8 }}><a href={c.link} className={styles.link}>{c.linkTxt}</a></div>
          </div>
        ))}
      </section>

      {/* Chart + Attention Required */}
      <section className={styles.twoCol}>
        {/* Payment Performance chart */}
        <div className={styles.card} style={{ gridColumn: 'span 2', minWidth: 0 }}>
          <div className={styles.chartHeader}>
            <h2 className={styles.h2}>Payment Performance</h2>
            <div>
              {['7 Days', '30 Days', '90 Days', '12 Months'].map((t, i) => (
                <button key={t} className={`${styles.tab} ${i === 1 ? styles.tabOn : ''}`}>{t}</button>
              ))}
            </div>
          </div>
          <div className={styles.legend}>
            <span><span className={styles.dot} style={{ background: '#009CDE' }} />Escrowed Amount</span>
            <span><span className={styles.dot} style={{ background: '#003087' }} />Released Amount</span>
            <span><span className={styles.dot} style={{ background: '#2E9D65' }} />Recovered Amount</span>
          </div>
          <svg viewBox="0 0 760 260" style={{ width: '100%', height: 'auto', display: 'block' }} role="img" aria-label="Line chart">
            <g stroke="#E5E9F0">
              <line x1="48" y1="20" x2="750" y2="20" />
              <line x1="48" y1="80" x2="750" y2="80" />
              <line x1="48" y1="140" x2="750" y2="140" />
              <line x1="48" y1="200" x2="750" y2="200" />
            </g>
            <g fontSize="11" fill="#64748B" fontFamily="Inter,sans-serif">
              <text x="40" y="24" textAnchor="end">$16k</text>
              <text x="40" y="84" textAnchor="end">$12k</text>
              <text x="40" y="144" textAnchor="end">$8k</text>
              <text x="40" y="204" textAnchor="end">$4k</text>
              <text x="48" y="228">Oct 12</text>
              <text x="250" y="228">Oct 22</text>
              <text x="450" y="228">Nov 1</text>
              <text x="680" y="228">Nov 11</text>
            </g>
            <path d="M48 150 L160 120 L270 128 L380 84 L490 96 L600 52 L750 40 L750 200 L48 200Z" fill="#009CDE" opacity=".12" />
            <polyline fill="none" stroke="#009CDE" strokeWidth="2.5" points="48,150 160,120 270,128 380,84 490,96 600,52 750,40" />
            <polyline fill="none" stroke="#003087" strokeWidth="2.5" points="48,176 160,160 270,150 380,132 490,120 600,100 750,84" />
            <polyline fill="none" stroke="#2E9D65" strokeWidth="2.5" strokeDasharray="6 4" points="48,192 160,186 270,176 380,170 490,156 600,150 750,128" />
            <circle cx="600" cy="52" r="5" fill="#009CDE" />
            <circle cx="600" cy="100" r="5" fill="#003087" />
            <circle cx="600" cy="150" r="5" fill="#2E9D65" />
            <rect x="520" y="8" width="150" height="34" rx="8" fill="#172B4D" />
            <text x="532" y="22" fontSize="11" fill="#fff" fontFamily="Inter,sans-serif">Nov 4 · Escrowed $14.2k</text>
            <text x="532" y="36" fontSize="11" fill="#C9D8F2" fontFamily="Inter,sans-serif">Released $9.6k · Recovered $5.1k</text>
          </svg>
        </div>

        {/* Attention Required */}
        <div className={styles.card} style={{ minWidth: 0 }}>
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>Attention Required</h2>
            <Badge cls="r">10 open</Badge>
          </div>
          <div>
            {[
              { count: 3, cls: 'a', text: 'Pending human approvals', href: '/approvals' },
              { count: 2, cls: 'a', text: 'Borderline verifications', href: '/submissions' },
              { count: 1, cls: 'r', text: 'Active dispute', href: '/disputes' },
              { count: 4, cls: 'b', text: 'Reconciliation exceptions', href: '/reconciliation' },
            ].map(item => (
              <div key={item.text} className={styles.row}>
                <Badge cls={item.cls}>{item.count}</Badge>
                <span style={{ flex: 1 }}>{item.text}</span>
                <a href={item.href} className={styles.link}>View Details</a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Escrow Overview */}
      <section>
        <h2 className={styles.h2} style={{ marginBottom: 12 }}>Escrow Overview</h2>
        <div className={styles.escrowGrid}>
          {[
            { label: 'Active Projects', val: String(activeProjects) },
            { label: 'Awaiting Funding', val: String(Math.max(0, activeProjects - 1)), badge: 'a', badgeTxt: 'Pending' },
            { label: 'Under Dispute / Review', val: String(disputesCount), badge: disputesCount > 0 ? 'r' : 'g', badgeTxt: disputesCount > 0 ? 'Disputed' : 'Good' },
            { label: 'Recovered Cases', val: String(recoveredCt), badge: 'g', badgeTxt: 'Resolved' },
            { label: 'Completed Milestones', val: String(Math.max(1, activeProjects * 2)), badge: 'g', badgeTxt: 'Released' },
          ].map(e => (
            <div key={e.label} className={`${styles.card} ${styles.escrowCard}`}>
              <div className={styles.kpiLabel}>{e.label}</div>
              <div className={styles.bigNum}>{e.val}</div>
              {e.badge && <Badge cls={e.badge}>{e.badgeTxt}</Badge>}
            </div>
          ))}
        </div>
      </section>

      {/* Recovery Performance + Recent Activity */}
      <section className={styles.twoCol}>
        {/* Recovery donut */}
        <div className={styles.card} style={{ minWidth: 0 }}>
          <h2 className={styles.h2}>Recovery Performance</h2>
          <div className={styles.donutRow}>
            <svg viewBox="0 0 100 100" width="150" height="150" role="img" aria-label="Donut chart of 150 recovery cases" style={{ flex: 'none' }}>
              <g fill="none" strokeWidth="14" transform="rotate(-90 50 50)">
                <circle cx="50" cy="50" r="40" stroke="#2E9D65" strokeDasharray="167.5 251.3" />
                <circle cx="50" cy="50" r="40" stroke="#0070E0" strokeDasharray="20.1 251.3" strokeDashoffset="-167.5" />
                <circle cx="50" cy="50" r="40" stroke="#009CDE" strokeDasharray="23.4 251.3" strokeDashoffset="-187.6" />
                <circle cx="50" cy="50" r="40" stroke="#F5A623" strokeDasharray="15.1 251.3" strokeDashoffset="-211" />
                <circle cx="50" cy="50" r="40" stroke="#D9363E" strokeDasharray="25.1 251.3" strokeDashoffset="-226.1" />
              </g>
              <text x="50" y="48" textAnchor="middle" fontSize="16" fontWeight="600" fill="#172B4D" fontFamily="Inter,sans-serif">{caseCt}</text>
              <text x="50" y="60" textAnchor="middle" fontSize="7" fill="#64748B" fontFamily="Inter,sans-serif">cases</text>
            </svg>
            <div className={styles.donutLegend}>
              {[['#2E9D65', `Recovered · ${recoveredCt}`], ['#0070E0', 'Active · 12'], ['#009CDE', 'Paid elsewhere · 14'], ['#F5A623', 'Halted by policy · 9'], ['#D9363E', 'Escalated · 15']].map(([col, lbl]) => (
                <div key={lbl}><span className={styles.dot} style={{ background: col }} />{lbl}</div>
              ))}
            </div>
          </div>
          <div className={styles.recoveryStats}>
            {[['Recovery success rate', '67%'], ['Avg. recovery time', '3.2 days'], ['Avg. contacts / recovery', '2.4'], ['Paid elsewhere', '14 cases'], ['Halted by policy', '9 cases']].map(([lbl, val]) => (
              <div key={lbl}>
                <div className={styles.kpiLabel}>{lbl}</div>
                <div className={styles.statVal}>{val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className={styles.card} style={{ minWidth: 0 }}>
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>Recent Activity</h2>
            <a href="/audit" className={styles.link}>View Audit Trail</a>
          </div>
          <div>
            {activityItems.map((item, i) => (
              <div key={i} className={styles.row}>
                <Ico d={ICON[item.icon]} amber={item.amber} red={item.red} />
                <div style={{ flex: 1 }}>
                  <div>{item.text} <strong>{item.bold}</strong>{item.suffix}</div>
                  <div className={styles.muted}>{item.time}</div>
                </div>
                <Badge cls={item.badge}>{item.label}</Badge>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
