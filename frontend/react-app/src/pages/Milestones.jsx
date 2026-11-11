import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { showToast } from '../components/ui/Toast';
import styles from './Milestones.module.css';

const DEMO_MILESTONES = [
  {
    id: 'MS-2026-001-01',
    project: 'E-commerce Web App',
    name: 'UI Design & Figma Tokens',
    amount: 400,
    due: '2026-11-05',
    status: 'PAID',
    score: '96% - AUTO_APPROVE',
    scoreCls: 'g',
    actions: [{ label: 'View Receipt', href: '/receipts' }]
  },
  {
    id: 'MS-2026-001-02',
    project: 'E-commerce Web App',
    name: 'Frontend Integration & API Client',
    amount: 700,
    due: '2026-11-15',
    status: 'PAYOUT_POLICY_DENIED',
    score: '94% - AUTO_APPROVE',
    scoreCls: 'g',
    actions: [
      { label: 'Review Work', href: '/submissions' },
      { label: 'Inspect Mandate Guard Decision', href: '/mandate-guard' }
    ]
  },
  {
    id: 'MS-2026-001-03',
    project: 'E-commerce Web App',
    name: 'Backend & PayPal Checkout',
    amount: 800,
    due: '2026-12-05',
    status: 'FUNDED',
    score: '—',
    scoreCls: 'muted',
    actions: [
      { label: 'Submit Work', href: '/submissions' },
      { label: 'Request Refund', href: '/disputes' }
    ]
  },
  {
    id: 'MS-2026-001-04',
    project: 'E-commerce Web App',
    name: 'QA, Testing & Deployment',
    amount: 500,
    due: '2026-12-20',
    status: 'FUNDED',
    score: '—',
    scoreCls: 'muted',
    actions: [
      { label: 'Submit Work', href: '/submissions' },
      { label: 'Request Refund', href: '/disputes' }
    ]
  },
  {
    id: 'MS-2026-002-01',
    project: 'Mobile App Redesign',
    name: 'Design System Foundations',
    amount: 900,
    due: '2026-11-12',
    status: 'VERIFYING',
    score: 'Scoring...',
    scoreCls: 'x',
    actions: [{ label: 'Review Work', href: '/submissions' }]
  },
  {
    id: 'MS-2026-002-02',
    project: 'Mobile App Redesign',
    name: 'Core Screens (14)',
    amount: 1300,
    due: '2026-11-18',
    status: 'IN_REVIEW',
    score: '72% - HUMAN_REVIEW',
    scoreCls: 'a',
    actions: [
      { label: 'Review Work', href: '/submissions' },
      { label: 'Request Refund', href: '/disputes' }
    ]
  },
  {
    id: 'MS-2026-002-03',
    project: 'Mobile App Redesign',
    name: 'Prototype Handoff',
    amount: 800,
    due: '2026-11-10',
    status: 'DISPUTED',
    score: '88% - AUTO_APPROVE',
    scoreCls: 'g',
    actions: [{ label: 'Inspect Mandate Guard Decision', href: '/mandate-guard' }]
  },
  {
    id: 'MS-2026-005-01',
    project: 'Analytics Dashboard',
    name: 'Data Model & Ingestion',
    amount: 1000,
    due: '2026-11-22',
    status: 'SUBMITTED',
    score: '—',
    scoreCls: 'muted',
    actions: [{ label: 'Review Work', href: '/submissions' }]
  },
  {
    id: 'MS-2026-005-02',
    project: 'Analytics Dashboard',
    name: 'Reporting Views',
    amount: 180,
    due: '2026-11-14',
    status: 'PAYOUT_PROPOSED',
    score: '93% - AUTO_APPROVE',
    scoreCls: 'g',
    actions: [{ label: 'Release Funds', href: '/approvals' }]
  },
  {
    id: 'MS-2026-007-01',
    project: 'API Integration Sprint',
    name: 'CRM Connector',
    amount: 150,
    due: '2026-10-30',
    status: 'PAID',
    score: '91% - AUTO_APPROVE',
    scoreCls: 'g',
    actions: [{ label: 'View Receipt', href: '/receipts' }]
  },
  {
    id: 'MS-2026-004-01',
    project: 'Brand Identity Package',
    name: 'Logo Concepts',
    amount: 300,
    due: '2026-10-25',
    status: 'REFUNDED',
    score: '48% - AUTO_REJECT',
    scoreCls: 'r',
    actions: [{ label: 'View Receipt', href: '/receipts' }]
  },
  {
    id: 'MS-2026-003-01',
    project: 'Data Pipeline Audit',
    name: 'Audit Scope & Findings',
    amount: 600,
    due: '2026-11-28',
    status: 'DRAFT',
    score: '—',
    scoreCls: 'muted',
    actions: [{ label: 'Edit Scope', href: '/projects' }]
  }
];

const STATUS_BADGE = {
  PAID: 'g',
  PAYOUT_POLICY_DENIED: 'r',
  FUNDED: 'b',
  VERIFYING: 'a',
  IN_REVIEW: 'a',
  DISPUTED: 'r',
  SUBMITTED: 'pu',
  PAYOUT_PROPOSED: 'b',
  REFUNDED: 'x',
  DRAFT: 'x'
};

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

export default function Milestones() {
  const navigate = useNavigate();
  const [milestones] = useState(DEMO_MILESTONES);

  const handleExportCsv = () => {
    const header = ['Milestone ID', 'Project Title', 'Milestone Name', 'Amount', 'Due Date', 'Status', 'AI Score'];
    const rows = milestones.map(m => [m.id, m.project, m.name, m.amount, m.due, m.status, m.score]);
    const csv = [header, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'proofpay-milestones.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Milestones exported as CSV.', 'success');
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Milestones Central Tracker</h1>
          <p className={styles.sub}>
            Track funding status, deliverable submissions, AI verifications, and PayPal payout releases.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btn} onClick={handleExportCsv}>Export CSV</button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={() => navigate('/submissions')}>
            Submit Work
          </button>
        </div>
      </div>

      {/* 6 KPI Cards */}
      <section className={styles.kpiGrid} aria-label="Milestone summary">
        <div className={styles.kpiCard}>
          <div className={styles.muted}>Total Milestones</div>
          <div className={`${styles.bigNum} ${styles.num}`}>32</div>
          <div className={styles.muted}>&nbsp;</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.muted}>Funded in Escrow</div>
          <div className={`${styles.bigNum} ${styles.num}`}>14</div>
          <div className={`${styles.muted} ${styles.num}`}>$17,300</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.muted}>Awaiting Submission</div>
          <div className={`${styles.bigNum} ${styles.num}`}>8</div>
          <div className={styles.muted}>&nbsp;</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.muted}>Under AI Verification</div>
          <div className={`${styles.bigNum} ${styles.num}`}>3</div>
          <div className={styles.muted}>&nbsp;</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.muted}>Pending Release</div>
          <div className={`${styles.bigNum} ${styles.num}`}>2</div>
          <div className={`${styles.muted} ${styles.num}`}>$1,400</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.muted}>Completed &amp; Paid</div>
          <div className={`${styles.bigNum} ${styles.num}`}>18</div>
          <div className={`${styles.muted} ${styles.num}`}>$31,200</div>
        </div>
      </section>

      {/* Table */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }}>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Milestone ID</th>
                <th className={styles.th}>Project Title</th>
                <th className={styles.th}>Milestone Name</th>
                <th className={styles.th}>Amount</th>
                <th className={styles.th}>Due Date</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>AI Score</th>
                <th className={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {milestones.map(m => (
                <tr key={m.id}>
                  <td className={styles.td}>
                    <a className={styles.monoLink} href={`/submissions?milestone_id=${m.id}`}>
                      {m.id}
                    </a>
                  </td>
                  <td className={styles.td} style={{ fontWeight: 500 }}>
                    {m.project}
                  </td>
                  <td className={styles.td} style={{ minWidth: 220, fontWeight: 500 }}>
                    {m.name}
                  </td>
                  <td className={`${styles.td} ${styles.num}`}>
                    {fmt(m.amount)}
                  </td>
                  <td className={`${styles.td} ${styles.num}`}>
                    {m.due}
                  </td>
                  <td className={styles.td}>
                    <span className={`${styles.bd} ${styles[STATUS_BADGE[m.status]] || styles.b}`}>
                      {m.status}
                    </span>
                  </td>
                  <td className={styles.td}>
                    {m.score === '—' ? (
                      <span className={styles.muted}>—</span>
                    ) : (
                      <span className={`${styles.bd} ${styles[m.scoreCls] || styles.b}`}>
                        {m.score}
                      </span>
                    )}
                  </td>
                  <td className={styles.td} style={{ whiteSpace: 'normal', minWidth: 170 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {m.actions.map(act => (
                        <a key={act.label} href={act.href} className={styles.actionLink}>
                          {act.label}
                        </a>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.tableFoot}>
          <span>Showing 12 of 32 milestones</span>
          <span>AUTO_APPROVE ≥ 0.80 · HUMAN_REVIEW 0.60–0.79 · AUTO_REJECT &lt; 0.60</span>
        </div>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
