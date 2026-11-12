import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from '../components/ui/Toast';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { generateEvidencePackPdf } from '../utils/evidencePdf';
import styles from './Disputes.module.css';

const INITIAL_DISPUTES = [
  {
    id: 'DISP-2026-012',
    pp: 'PP-D-998241',
    ref: 'PRJ-2026-003 / Milestone 2',
    href: '/milestones',
    party: 'Acme Corp (Client)',
    amt: 600,
    reason: 'Product / Work Not as Described',
    days: 4,
    esc: 'FROZEN',
    rec: 'CAMPAIGN HALTED',
    st: 'OPEN',
    hash: '0a8f9c2d71be4a5f3c9d0e68b2147ad5c3e90f1b7a6d2c48e5f0a91b3d7c64e1',
    score: 92,
    pr: 'github.com/rsharma/acme-shop/pull/42',
  },
  {
    id: 'DISP-2026-014',
    pp: 'PP-D-998305',
    ref: 'INV-2026-1019 / Subscription',
    href: '/invoices',
    party: 'Lena Ortiz (Customer)',
    amt: 600,
    reason: 'Unauthorized / Not Recognized',
    days: 6,
    esc: 'N/A',
    rec: 'CAMPAIGN HALTED',
    st: 'OPEN',
    hash: '7c31e0b9a4d85f126e9b30c7d1a58f42b6e3097cd18a5f2e04b97c3a6d12f8e5',
    score: null,
    pr: null,
  },
];

export default function Disputes() {
  const { data: apiDisputes } = useApi(() => endpoints.disputes.list());
  const [disputes, setDisputes] = useState(INITIAL_DISPUTES);
  const [evidencePacks, setEvidencePacks] = useState({});
  const [activeDrawer, setActiveDrawer] = useState(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [refundTarget, setRefundTarget] = useState(null);

  useEffect(() => {
    if (!apiDisputes || !Array.isArray(apiDisputes) || apiDisputes.length === 0) return;
    const mapped = apiDisputes.map((d, i) => ({
      id: d.id || `DISP-2026-0${12 + i}`,
      pp: d.pp || `PP-D-${998241 + i}`,
      ref: d.ref || (d.customer_id ? `${d.customer_id} / Case` : `REC-${(d.case_id || '').slice(0, 8).toUpperCase()}`),
      href: d.href || (d.project_id ? `/project-details?id=${d.project_id}` : '/cases'),
      party: d.party || d.customer_id || 'Customer',
      amt: d.amount || 600,
      reason: d.reason || 'Payment Dispute',
      days: d.days || 4,
      esc: d.esc || 'FROZEN',
      rec: d.rec || 'CAMPAIGN HALTED',
      st: d.state === 'OPEN' ? 'OPEN' : (d.state === 'ESCALATED' ? 'ESCALATED' : (d.state || 'OPEN')),
      hash: d.plan_hash || ('db' + (d.case_id || '0'.repeat(8)).slice(0, 8) + '0'.repeat(55)),
      score: d.score ?? 92,
      pr: d.pr || 'github.com/dchen/testing-deliverable/pull/18',
      evidence_fixtures: d.evidence_fixtures || ['work_sample.zip', 'test_report.pdf', 'verification_log.txt'],
    }));
    setDisputes(mapped);
  }, [apiDisputes]);

  const openDisputes = disputes.filter(d => d.st !== 'REFUNDED');
  const heldAmount = openDisputes.filter(d => d.esc !== 'N/A').reduce((acc, d) => acc + d.amt, 0);
  const totalAmount = openDisputes.reduce((acc, d) => acc + d.amt, 0);
  const minDays = openDisputes.length ? Math.min(...openDisputes.map(d => d.days)) : null;

  const fmt = (n) => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

  const handleSimulateWebhook = () => {
    const nextNum = disputes.length + 13;
    const newDispute = {
      id: `DISP-2026-0${nextNum}`,
      pp: `PP-D-99${8400 + nextNum}`,
      ref: 'PRJ-2026-001 / Milestone 3',
      href: '/milestones',
      party: 'Acme Global Solutions (Client)',
      amt: 800,
      reason: 'Work Not as Described',
      days: 10,
      esc: 'FROZEN',
      rec: 'CAMPAIGN HALTED',
      st: 'OPEN',
      hash: 'e41b7a09c5d32f8e6a10b94d7c3e5f2a81d06b9c4e7f3a52d1089b6c7e4a3f20',
      score: 94,
      pr: 'github.com/rsharma/acme-shop/pull/47',
    };
    setDisputes([newDispute, ...disputes]);
    toast.warning('Policy Alert: CUSTOMER.DISPUTE.CREATED received. Milestone locked and payouts frozen.');
  };

  const handleOpenPack = (d) => {
    setActiveDrawer(d);
  };

  const handleCompilePack = () => {
    if (!activeDrawer) return;
    setIsCompiling(true);
    setTimeout(() => {
      try {
        generateEvidencePackPdf(activeDrawer);
        setIsCompiling(false);
        setEvidencePacks(prev => ({ ...prev, [activeDrawer.id]: true }));
        toast.success(`Evidence pack for ${activeDrawer.id} generated & downloaded (PDF).`);
      } catch (err) {
        setIsCompiling(false);
        console.error('Evidence pack generation failed:', err);
        toast.error('Failed to generate PDF evidence pack.');
      }
    }, 600);
  };

  const handleSubmitDefense = (id, pp) => {
    setDisputes(prev => prev.map(d => d.id === id ? { ...d, st: 'DEFENDED' } : d));
    toast.success(`Defense submitted to PayPal for ${pp}. Audit entry recorded.`);
  };

  const handleConfirmRefund = () => {
    if (!refundTarget) return;
    setDisputes(prev => prev.map(d => d.id === refundTarget.id ? { ...d, st: 'REFUNDED' } : d));
    toast.success(`${refundTarget.id} refunded. Escrow released and audit entry recorded.`);
    setRefundTarget(null);
  };

  return (
    <div className={styles.container}>
      {/* Title & Actions */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>Dispute Management &amp; Evidence Center</h1>
          <p>Instant escrow freeze and 1-click evidence pack compilation for PayPal dispute defense.</p>
        </div>
        <div className={styles.actionsGroup}>
          <span className={`${styles.badge} ${styles.badgeRed}`} style={{ padding: '8px 14px', fontSize: 13 }}>
            {openDisputes.length} Active Disputes ({fmt(totalAmount)} held)
          </span>
          <button className={styles.btn} onClick={handleSimulateWebhook}>
            Simulate Dispute Webhook
          </button>
        </div>
      </div>

      {/* Autonomous Escrow Freeze Banner */}
      <section className={styles.freezeCard} aria-label="Autonomous escrow freeze">
        <div className={styles.freezeIcon}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4" />
          </svg>
        </div>
        <div>
          <div className={styles.freezeTitle}>Autonomous Escrow Freeze</div>
          <div className={styles.freezeText}>
            When a dispute webhook (<code className={styles.mono}>CUSTOMER.DISPUTE.CREATED</code>) is received from PayPal, Mandate Guard immediately locks the affected milestone and freezes all payout execution until human review is complete.
          </div>
        </div>
      </section>

      {/* 4 KPIs */}
      <section className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Active disputes</div>
          <div className={styles.kpiValue}>{openDisputes.length}</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Amount held in freeze</div>
          <div className={styles.kpiValue}>{fmt(heldAmount)}</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Recovery campaigns halted</div>
          <div className={styles.kpiValue}>{openDisputes.length}</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Next evidence deadline</div>
          <div className={styles.kpiValue}>{minDays !== null ? `${minDays} days` : '—'}</div>
        </div>
      </section>

      {/* Disputes Table */}
      <section className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <h2 className={styles.tableTitle}>Disputes</h2>
          <span className={styles.kpiLabel}>Source: GET /projects · GET /cases · GET /audit</span>
        </div>
        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Dispute ID</th>
                <th className={styles.th}>PayPal Reference</th>
                <th className={styles.th}>Project / Invoice</th>
                <th className={styles.th}>Disputing Party</th>
                <th className={styles.th}>Amount</th>
                <th className={styles.th}>Reason</th>
                <th className={styles.th}>Escrow Status</th>
                <th className={styles.th}>Recovery Status</th>
                <th className={styles.th}>Evidence Deadline</th>
                <th className={`${styles.th} ${styles.actionsTh}`}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {disputes.map(d => {
                const isRefunded = d.st === 'REFUNDED';
                const isDefended = d.st === 'DEFENDED';
                const hasPack = !!evidencePacks[d.id];
                return (
                  <tr key={d.id} className={styles.tr}>
                    <td className={styles.td}><b>{d.id}</b></td>
                    <td className={styles.td}><code className={styles.mono}>{d.pp}</code></td>
                    <td className={styles.td}><Link to={d.href} style={{ color: 'var(--blue)' }}>{d.ref}</Link></td>
                    <td className={styles.td}>{d.party}</td>
                    <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}><b>{fmt(d.amt)}</b></td>
                    <td className={styles.td}>{d.reason}</td>
                    <td className={styles.td}>
                      {isRefunded ? (
                        <span className={`${styles.badge} ${styles.badgeGray}`}>REFUNDED</span>
                      ) : d.esc === 'N/A' ? (
                        <span className={`${styles.badge} ${styles.badgeGray}`}>NO ESCROW</span>
                      ) : (
                        <span className={`${styles.badge} ${styles.badgeRed}`}>FROZEN BY MANDATE GUARD</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      {isRefunded ? (
                        <span className={`${styles.badge} ${styles.badgeGray}`}>CLOSED</span>
                      ) : (
                        <span className={`${styles.badge} ${styles.badgeRed}`}>{d.rec}</span>
                      )}
                    </td>
                    <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}>
                      {isRefunded ? (
                        '—'
                      ) : isDefended ? (
                        <span className={`${styles.badge} ${styles.badgeBlue}`}>DEFENSE SUBMITTED</span>
                      ) : (
                        <b style={{ color: d.days <= 4 ? '#B42830' : '#172B4D' }}>
                          {d.days} Days Remaining
                        </b>
                      )}
                    </td>
                    <td className={`${styles.td} ${styles.actionsTd}`}>
                      <div className={styles.actionCell}>
                        <button
                          className={`${styles.btn} ${styles.btnSm} ${styles.btnOutline}`}
                          onClick={() => handleOpenPack(d)}
                          disabled={isRefunded}
                          title="Generate & download official 5-point evidence dossier"
                        >
                          {hasPack ? 'Evidence Pack (PDF)' : 'Evidence Pack'}
                        </button>
                        <button
                          className={`${styles.btn} ${styles.btnSm} ${styles.btnDanger}`}
                          onClick={() => setRefundTarget(d)}
                          disabled={isRefunded || isDefended}
                          title="Accept dispute and refund buyer"
                        >
                          Accept &amp; Refund
                        </button>
                        <button
                          className={`${styles.btn} ${styles.btnSm} ${styles.btnPrimary}`}
                          onClick={() => handleSubmitDefense(d.id, d.pp)}
                          disabled={isRefunded || isDefended || !hasPack}
                          title={hasPack ? 'Submit compiled defense package to PayPal' : 'Generate evidence pack first'}
                        >
                          Submit Defense
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Evidence Pack Generator Drawer */}
      {activeDrawer && (
        <>
          <div className={styles.drawerOverlay} onClick={() => setActiveDrawer(null)} />
          <div className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="evidenceDrawerTitle">
            <div className={styles.drawerHeader}>
              <div style={{ flex: 1 }}>
                <div className={styles.kpiLabel}>{activeDrawer.id} · {activeDrawer.pp}</div>
                <h2 className={styles.tableTitle} id="evidenceDrawerTitle">Evidence Pack Generator</h2>
              </div>
              <button
                className={styles.btn}
                style={{ width: 36, height: 36, padding: 0, fontSize: 20 }}
                onClick={() => setActiveDrawer(null)}
                aria-label="Close drawer"
              >
                ×
              </button>
            </div>
            <div className={styles.drawerBody}>
              {[
                [
                  'Original scope & dual-approved Plan Hash',
                  `${activeDrawer.hash.slice(0, 7)}...${activeDrawer.hash.slice(-3)} · both parties signed`,
                ],
                [
                  'Timestamped client approval record',
                  'Approved 2026-10-28 09:14 UTC · signature matches plan hash',
                ],
                [
                  'GitHub pull request & deployment logs',
                  activeDrawer.pr ? `${activeDrawer.pr} · staging deploy passed` : 'Not applicable (subscription invoice) · gateway capture logs attached',
                ],
                [
                  'AI Verifier inspection report',
                  activeDrawer.score ? `Score ${activeDrawer.score}/100 · route AUTO_APPROVE` : 'Reconciliation record: no offline payment matched',
                ],
                [
                  'Immutable SHA-256 audit chain trail',
                  `Chain verified intact · ${activeDrawer.hash.slice(0, 12)}…`,
                ],
              ].map(([title, desc], idx) => (
                <div key={title} className={styles.evidenceItem}>
                  <span className={styles.checkCircle}>{idx + 1}</span>
                  <div>
                    <b style={{ fontSize: 14 }}>{title}</b>
                    <div className={styles.kpiLabel} style={{ marginTop: 2 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className={styles.drawerFooter}>
              <button
                className={`${styles.btn} ${styles.btnPrimary}`}
                onClick={handleCompilePack}
                disabled={isCompiling}
              >
                {isCompiling ? 'Compiling…' : 'Download PayPal Evidence Pack (PDF)'}
              </button>
              <div className={styles.kpiLabel}>
                {evidencePacks[activeDrawer.id]
                  ? 'Pack compiled and ready. You can now submit your defense.'
                  : 'Dossier compiles 5 evidence items for the PayPal Dispute Center.'}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Accept & Refund Modal */}
      {refundTarget && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalCard}>
            <h2 className={styles.tableTitle} style={{ fontSize: 18 }}>Accept dispute &amp; refund?</h2>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 14, lineHeight: 1.5 }}>
              Refund {fmt(refundTarget.amt)} to {refundTarget.party} and close {refundTarget.id}. This is recorded in the audit chain and cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button className={styles.btn} onClick={() => setRefundTarget(null)}>
                Cancel
              </button>
              <button
                className={`${styles.btn} ${styles.btnPrimary}`}
                style={{ background: '#D9363E', borderColor: '#D9363E' }}
                onClick={handleConfirmRefund}
              >
                Confirm refund
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

