import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from '../components/ui/Toast';
import styles from './Agents.module.css';

const INITIAL_AGENTS = [
  {
    id: 'scoping',
    n: 'AI Scoping Agent',
    r: 'Analyzes project briefs, extracts acceptance criteria, drafts milestone allocations.',
    lat: '1.4s',
    m: ['Model', 'Gemini / Claude Sonnet'],
    ic: 'M5 8h14v10H5zM12 8V4M9 13h.01M15 13h.01',
    bar: 35,
    paused: false,
  },
  {
    id: 'verify',
    n: 'Milestone Verification Agent',
    r: 'Inspects GitHub PRs, runs test suites, queries deployed URLs, scores deliverables.',
    lat: '3.2s',
    m: ['Accuracy', '96.8%'],
    ic: 'M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM9 14l2 2 4-4',
    bar: 80,
    paused: false,
  },
  {
    id: 'diag',
    n: 'Recovery Diagnosis Agent',
    r: 'Classifies payment failure codes, identifies card expiration vs. insufficient funds.',
    lat: '1.1s',
    m: ['Accuracy', '98.2%'],
    ic: 'M3 17l6-6 4 4 8-8M15 7h6v6',
    bar: 28,
    paused: false,
  },
  {
    id: 'ladder',
    n: 'Contact Ladder Orchestrator',
    r: 'Schedules 3-stage reminders, enforces 48h ladder timeouts and quiet hours (21:00–08:00).',
    lat: '0.8s',
    m: ['Quiet-hour violations', '0'],
    ic: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
    bar: 20,
    paused: false,
  },
  {
    id: 'recon',
    n: 'Reconciliation Matching Agent',
    r: 'Executes 3-way matching between PayPal, bank statements, and ERP.',
    lat: '2.1s',
    m: ['Match rate', '98.5%'],
    ic: 'M4 8h14l-3-3M20 16H6l3 3',
    bar: 52,
    paused: false,
  },
  {
    id: 'guard',
    n: 'Mandate Guard Policy Evaluator',
    r: 'Strictly evaluates proposals against deterministic Python safety rules. No LLM in the loop.',
    lat: '< 5ms',
    m: ['Limits', '$200 / txn · $5,000 / day'],
    ic: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
    bar: 3,
    det: true,
    paused: false,
  },
];

const INITIAL_LOGS = [
  { time: '14:28:41', agent: 'Milestone Verification', prop: 'M2 score 0.94 → AUTO_APPROVE', outColor: 'r', outMain: 'BLOCKED', outSub: 'over $200 limit, sent to Approvals #APP-104', hash: '9f3a…c1e2' },
  { time: '14:21:07', agent: 'Recovery Diagnosis', prop: 'REC-2026-0042 → EXPIRED_CARD', outColor: 'g', outMain: 'ALLOWED', outSub: 'Stage 1 update link', hash: 'b7d0…44aa' },
  { time: '14:09:52', agent: 'Reconciliation Matching', prop: 'Michael Anderson $450.00 wire found', outColor: 'g', outMain: 'PAID_ELSEWHERE', outSub: 'outreach halted', hash: '2c85…e910' },
  { time: '13:57:30', agent: 'Contact Ladder', prop: 'Stage 2 reminder queued', outColor: 'a', outMain: 'QUIET_HOURS_PAUSED', outSub: 'until 08:00', hash: '51ef…0b3d' },
  { time: '13:40:15', agent: 'AI Scoping', prop: 'PRJ-2026-001 → 4 milestones', outColor: 'g', outMain: 'ALLOWED', outSub: 'awaiting dual approval', hash: 'e04b…7a96' },
];

export default function Agents() {
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [logs] = useState(INITIAL_LOGS);
  const [isKillModalOpen, setIsKillModalOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState('Live API');

  const onlineCount = agents.filter(a => !a.paused).length;
  const isFleetPaused = agents.slice(0, 5).every(a => a.paused);

  const toggleAgent = (idx) => {
    const updated = [...agents];
    updated[idx].paused = !updated[idx].paused;
    setAgents(updated);
    toast.info(`${updated[idx].n} ${updated[idx].paused ? 'paused.' : 'resumed.'}`);
  };

  const handlePauseAll = () => {
    setAgents(agents.map((a, i) => i < 5 ? { ...a, paused: true } : a));
    setIsKillModalOpen(false);
    toast.warning('Kill-switch engaged: 5 autonomous agents paused. Mandate Guard is blocking all payouts.');
  };

  const handleResumeAll = () => {
    setAgents(agents.map(a => ({ ...a, paused: false })));
    toast.success('All agents resumed.');
  };

  const handleRefreshHealth = () => {
    setHealthStatus('Checking…');
    setTimeout(() => {
      setHealthStatus('Live API');
      toast.success('Agent fleet health verified: 6/6 operational.');
    }, 600);
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>AI Agent Control Center</h1>
          <p>Fleet observability, execution latency, model configurations, and kill-switch controls.</p>
        </div>
        <div className={styles.actionsGroup}>
          <button className={styles.btn} onClick={handleRefreshHealth}>Refresh health</button>
          <button className={`${styles.btn} ${styles.btnDanger}`} onClick={() => setIsKillModalOpen(true)}>
            Pause all autonomous agents
          </button>
        </div>
      </div>

      {/* Paused Banner */}
      {isFleetPaused && (
        <div className={styles.pauseBanner} role="status">
          <div style={{ flex: 1, minWidth: 240, fontSize: 14 }}>
            <b>Autonomous agents are paused.</b>{' '}
            <span style={{ color: '#172B4D' }}>
              No new scoping, verification, diagnosis, outreach, or matching will run. Mandate Guard keeps enforcing policy and blocks every payout while the fleet is paused.
            </span>
          </div>
          <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={handleResumeAll}>
            Resume all agents
          </button>
        </div>
      )}

      {/* Fleet Summary Dark Hero Card */}
      <section className={styles.fleetCard} aria-label="Fleet summary">
        <div>
          <div className={styles.fleetLabel}>Fleet status</div>
          <div className={styles.fleetValue}>{onlineCount} / 6 online</div>
        </div>
        <div>
          <div className={styles.fleetLabel}>Median agent latency</div>
          <div className={styles.fleetValue}>1.4s</div>
        </div>
        <div>
          <div className={styles.fleetLabel}>Proposals today</div>
          <div className={styles.fleetValue}>214</div>
        </div>
        <div>
          <div className={styles.fleetLabel}>Blocked by Mandate Guard</div>
          <div className={styles.fleetValue} style={{ color: '#F8C46A' }}>9</div>
        </div>
        <div>
          <div className={styles.fleetLabel}>Health source</div>
          <div style={{ marginTop: 8 }}>
            <span className={`${styles.badge} ${styles.badgeGreen}`}>{healthStatus}</span>
          </div>
        </div>
      </section>

      {/* Agents Section */}
      <section aria-label="Agents">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>
            Specialized Agents
          </h2>
          <span className={styles.fleetLabel} style={{ color: 'var(--muted)' }}>
            AI proposes. Only deterministic code can execute.
          </span>
        </div>

        <div className={styles.agentsGrid}>
          {agents.map((a, idx) => (
            <article
              key={a.id}
              className={`${styles.agentCard} ${a.det ? styles.agentCardDeterministic : ''}`}
            >
              <div className={styles.agentHeader}>
                <div className={styles.agentIcon}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d={a.ic} />
                  </svg>
                </div>
                <h3 className={styles.agentTitle}>{a.n}</h3>
                <span className={`${styles.badge} ${a.paused ? styles.badgeAmber : styles.badgeGreen}`}>
                  {a.paused ? 'PAUSED' : 'ONLINE'}
                </span>
              </div>

              <p className={styles.agentDesc}>{a.r}</p>

              <div className={styles.agentMetricsGrid}>
                <div>
                  <div className={styles.fleetLabel} style={{ color: 'var(--muted)' }}>Latency</div>
                  <div style={{ fontWeight: 600, fontSize: 18, color: 'var(--text)', fontVariantNumeric: 'tabular-nums', marginTop: 2 }}>
                    {a.lat}
                  </div>
                </div>
                <div>
                  <div className={styles.fleetLabel} style={{ color: 'var(--muted)' }}>{a.m[0]}</div>
                  <div style={{
                    fontWeight: 600,
                    fontSize: a.m[1].length > 12 ? 13 : 18,
                    paddingTop: a.m[1].length > 12 ? 4 : 0,
                    color: 'var(--text)',
                    fontVariantNumeric: 'tabular-nums',
                    marginTop: 2,
                  }}>
                    {a.m[1]}
                  </div>
                </div>
              </div>

              <div className={styles.latencyBarTrack} role="img" aria-label="Relative latency">
                <div
                  className={styles.latencyBarFill}
                  style={{
                    width: `${a.bar}%`,
                    background: a.det ? 'var(--blue-dark)' : 'var(--blue)',
                  }}
                />
              </div>

              <div className={styles.agentFooter}>
                {a.det ? (
                  <>
                    <span className={`${styles.badge} ${styles.badgeBlue}`}>Deterministic · always on</span>
                    <span style={{ flex: 1 }} />
                    <Link to="/mandate-guard" style={{ color: 'var(--blue)', fontSize: 13, textDecoration: 'none' }}>
                      Open policies →
                    </Link>
                  </>
                ) : (
                  <>
                    <button
                      className={`${styles.btn} ${styles.btnSm}`}
                      onClick={() => toggleAgent(idx)}
                    >
                      {a.paused ? 'Resume agent' : 'Pause agent'}
                    </button>
                    <span style={{ flex: 1 }} />
                    <Link to="/audit" style={{ color: 'var(--blue)', fontSize: 13, textDecoration: 'none' }}>
                      View logs →
                    </Link>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Recent Agent Decisions Table */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>
            Recent Agent Decisions
          </h2>
          <Link to="/audit" style={{ color: 'var(--blue)', fontSize: 13, textDecoration: 'none' }}>
            Open audit trail →
          </Link>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Time (UTC)</th>
                <th className={styles.th}>Agent</th>
                <th className={styles.th}>Proposal</th>
                <th className={styles.th}>Policy outcome</th>
                <th className={styles.th}>Audit hash</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((row, idx) => (
                <tr key={idx} className={styles.tr}>
                  <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}>{row.time}</td>
                  <td className={styles.td}><b>{row.agent}</b></td>
                  <td className={styles.td}>{row.prop}</td>
                  <td className={styles.td}>
                    <span className={`${styles.badge} ${row.outColor === 'r' ? styles.badgeRed : row.outColor === 'a' ? styles.badgeAmber : styles.badgeGreen}`}>
                      {row.outMain}
                    </span>{' '}
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>{row.outSub}</span>
                  </td>
                  <td className={styles.td}>
                    <Link to="/audit" className={styles.mono}>{row.hash}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Kill Switch Confirmation Modal */}
      {isKillModalOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalCard}>
            <h2 style={{ fontSize: 18, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
              Pause all autonomous agents?
            </h2>
            <p style={{ margin: 0, fontSize: 14, color: '#172B4D', lineHeight: 1.5 }}>
              The 5 AI agents stop immediately. In-flight proposals are held, and scheduled recovery outreach and retries are suspended. Mandate Guard stays online and blocks all payouts until you resume.
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button className={styles.btn} onClick={() => setIsKillModalOpen(false)}>
                Keep running
              </button>
              <button
                className={`${styles.btn} ${styles.btnDanger}`}
                style={{ background: '#D9363E', color: '#fff', borderColor: '#D9363E' }}
                onClick={handlePauseAll}
              >
                Pause all agents
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className={styles.footerTagline}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </footer>
    </div>
  );
}

