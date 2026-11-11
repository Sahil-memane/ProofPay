import { useState } from 'react';
import { showToast } from '../components/ui/Toast';
import styles from './Approvals.module.css';

const INITIAL_PAYOUTS = [
  {
    id: 'TASK-APP-104',
    ms: 'MS-2026-001-02',
    proj: 'E-commerce Web App',
    rcp: 'freelancer@example.com',
    amt: 700,
    score: 94,
    note: 'Passed all automated criteria',
    flag: 'OVERSIZED_PAYOUT: Amount exceeds $200.00 autonomous threshold',
    at: '2026-11-11 08:12 UTC',
    pr: 'https://github.com/acme/shop/pull/42',
    url: 'https://staging-shop.acme.app',
    m: 'Frontend Integration & API Client'
  },
  {
    id: 'TASK-APP-105',
    ms: 'MS-2026-005-01',
    proj: 'Brand Identity Pack',
    rcp: 'designer@example.com',
    amt: 850,
    score: 88,
    note: 'Passed 7 of 8 criteria',
    flag: 'OVERSIZED_PAYOUT: Amount exceeds $200.00 autonomous threshold',
    at: '2026-11-11 10:47 UTC',
    pr: 'https://github.com/acme/brand/pull/9',
    url: 'https://staging-brand.acme.app',
    m: 'Logo system & guidelines'
  }
];

const INITIAL_RECOVERIES = [
  {
    id: 'REC-2026-0089',
    cust: 'Acme Corp',
    amt: 1850,
    act: 'STAGE_3_SERVICE_SUSPENSION',
    risk: 'HIGH RISK',
    why: 'Amount exceeds $1,000 policy threshold; service suspension requested',
    diag: 'INSUFFICIENT_FUNDS',
    hist: 'Stage 1 link sent 11-04 · Stage 2 firm warning sent 11-08 · no response'
  }
];

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

async function sha256(text) {
  try {
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(b)).map(x => x.toString(16).padStart(2, '0')).join('');
  } catch {
    return 'a91f3c07d2e84b165c0f9a3e7d18b2c45e1b77hn';
  }
}

export default function Approvals() {
  const [tab, setTab] = useState(1);
  const [payouts, setPayouts] = useState(INITIAL_PAYOUTS);
  const [recoveries, setRecoveries] = useState(INITIAL_RECOVERIES);
  const [recentDecisions, setRecentDecisions] = useState([]);

  // Modal state
  const [modalItem, setModalItem] = useState(null);
  const [decision, setDecision] = useState('APPROVE');
  const [notes, setNotes] = useState('');
  const [notesError, setNotesError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successSteps, setSuccessSteps] = useState(null);

  const openModal = (kind, item) => {
    setModalItem({ kind, item });
    setDecision('APPROVE');
    setNotes(kind === 'p'
      ? 'Reviewed PR code quality and live preview. Deliverable satisfies all milestone criteria.'
      : 'Reviewed contact history and customer record.');
    setNotesError('');
    setSuccessSteps(null);
  };

  const closeModal = () => {
    setModalItem(null);
    setSuccessSteps(null);
  };

  const handleDecisionSubmit = async (e) => {
    e.preventDefault();
    if (notes.trim().length < 10) {
      setNotesError('Reviewer notes are required (at least 10 characters).');
      return;
    }
    setNotesError('');
    setSubmitting(true);
    await new Promise(r => setTimeout(r, 800));

    const { kind, item } = modalItem;
    const ok = decision === 'APPROVE';
    const hash = await sha256(JSON.stringify({ id: item.id, decision, notes, t: Date.now() }));
    const batch = 'PAYOUTS-' + hash.slice(0, 10).toUpperCase();

    const steps = [
      ['Decision recorded: ' + decision + ' by Risk Officer', true],
      ['Mandate Guard: human override logged against ' + (kind === 'p' ? 'Rule 1' : 'recovery threshold'), true]
    ];

    if (kind === 'p') {
      steps.push(
        ok
          ? [`PayPal Payout dispatched · batch ${batch} · ${fmt(item.amt)}`, true]
          : ['No funds moved · freelancer notified to revise and resubmit', true]
      );
      steps.push([
        ok ? 'Ledger entry recorded' : 'Ledger unchanged: escrow remains held',
        true
      ]);
      setPayouts(prev => prev.filter(x => x.id !== item.id));
    } else {
      steps.push([
        ok ? 'Action executed: ' + item.act : 'Action cancelled; case returned to Stage 2 contact ladder',
        true
      ]);
      setRecoveries(prev => prev.filter(x => x.id !== item.id));
    }

    steps.push([`Appended to SHA-256 audit chain · ${hash.slice(0, 12)}… ↗`, true]);

    setRecentDecisions(prev => [
      { id: item.id, ok, amt: item.amt, notes, hash },
      ...prev
    ]);

    setSubmitting(false);
    setSuccessSteps({ ok, steps, id: item.id });

    showToast(
      ok && kind === 'p'
        ? `Success: PayPal Payout dispatched for ${item.id}.`
        : `Decision recorded for ${item.id}.`,
      ok ? 'success' : 'warning'
    );
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Human Approvals Queue &amp; Governance Inbox</h1>
          <p className={styles.sub}>
            Human-in-the-Loop decision center for high-value payouts, borderline AI scores, and sensitive recovery interventions.
          </p>
        </div>
      </div>

      {/* Alert banners */}
      <div className={styles.alertsBar}>
        {payouts.length > 0 && (
          <span className={`${styles.bd} ${styles.a}`} style={{ padding: '8px 14px', fontSize: 13 }}>
            ⚠️ {payouts.length} Milestone Payout{payouts.length > 1 ? 's' : ''} Awaiting Review (Oversized &gt; $200.00 Limit)
          </span>
        )}
        {recoveries.length > 0 && (
          <span className={`${styles.bd} ${styles.a}`} style={{ padding: '8px 14px', fontSize: 13 }}>
            ⚠️ {recoveries.length} Recovery Escalation{recoveries.length > 1 ? 's' : ''} Awaiting Sign-off (Stage 3 Account Suspension)
          </span>
        )}
        {payouts.length === 0 && recoveries.length === 0 && (
          <span className={`${styles.bd} ${styles.g}`} style={{ padding: '8px 14px', fontSize: 13 }}>
            ✓ All clear: nothing awaiting review
          </span>
        )}
      </div>

      {/* Main Queues Card */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }}>
        <div className={styles.tabList} role="tablist">
          <button
            className={`${styles.tab} ${tab === 1 ? styles.tabOn : ''}`}
            onClick={() => setTab(1)}
          >
            Escrow Milestone Payout Approvals{' '}
            <span className={`${styles.bd} ${styles.a}`}>{payouts.length}</span>
          </button>
          <button
            className={`${styles.tab} ${tab === 2 ? styles.tabOn : ''}`}
            onClick={() => setTab(2)}
          >
            Recovery Intervention Approvals{' '}
            <span className={`${styles.bd} ${styles.a}`}>{recoveries.length}</span>
          </button>
        </div>

        {tab === 1 && (
          payouts.length > 0 ? (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Task ID</th>
                    <th className={styles.th}>Milestone / Project</th>
                    <th className={styles.th}>Freelancer Recipient</th>
                    <th className={styles.th}>Amount</th>
                    <th className={styles.th}>AI Verification Score</th>
                    <th className={styles.th}>Flag Reason</th>
                    <th className={styles.th}>Submitted</th>
                    <th className={styles.th}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {payouts.map(p => (
                    <tr key={p.id}>
                      <td className={styles.td}>
                        <a className={styles.monoLink} href="/audit">
                          {p.id}
                        </a>
                      </td>
                      <td className={styles.td}>
                        <code className={styles.mono}>{p.ms}</code>
                        <div className={styles.muted}>{p.proj}</div>
                      </td>
                      <td className={styles.td}>{p.rcp}</td>
                      <td className={`${styles.td} ${styles.num}`}>
                        <b>{fmt(p.amt)}</b>
                        <div>
                          <span className={`${styles.bd} ${styles.r}`} style={{ marginTop: 4 }}>
                            Exceeds $200 Cap
                          </span>
                        </div>
                      </td>
                      <td className={styles.td}>
                        <b className={styles.num}>{p.score}%</b> - {p.note}
                      </td>
                      <td className={styles.td}>
                        <code className={styles.mono} style={{ color: '#B42830' }}>
                          {p.flag.split(':')[0]}
                        </code>
                        <div className={styles.muted}>{p.flag.split(': ')[1]}</div>
                      </td>
                      <td className={`${styles.td} ${styles.num}`}>{p.at}</td>
                      <td className={styles.td}>
                        <button
                          className={`${styles.btn} ${styles.btnP}`}
                          style={{ height: 36 }}
                          onClick={() => openModal('p', p)}
                        >
                          Review &amp; Decide
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className={styles.empty}>
              <b>Queue clear</b>
              <div className={styles.muted} style={{ marginTop: 4 }}>
                No items awaiting human review in this queue.
              </div>
            </div>
          )
        )}

        {tab === 2 && (
          recoveries.length > 0 ? (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Case ID</th>
                    <th className={styles.th}>Customer / Company</th>
                    <th className={styles.th}>Amount at Risk</th>
                    <th className={styles.th}>Proposed Action</th>
                    <th className={styles.th}>Risk Level</th>
                    <th className={styles.th}>Reason for Human Review</th>
                    <th className={styles.th}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recoveries.map(r => (
                    <tr key={r.id}>
                      <td className={styles.td}>
                        <a className={styles.monoLink} href="/cases">
                          {r.id}
                        </a>
                      </td>
                      <td className={styles.td}><b>{r.cust}</b></td>
                      <td className={`${styles.td} ${styles.num}`}><b>{fmt(r.amt)}</b></td>
                      <td className={styles.td}><code className={styles.mono}>{r.act}</code></td>
                      <td className={styles.td}><span className={`${styles.bd} ${styles.r}`}>{r.risk}</span></td>
                      <td className={styles.td}>{r.why}</td>
                      <td className={styles.td}>
                        <button
                          className={`${styles.btn} ${styles.btnP}`}
                          style={{ height: 36 }}
                          onClick={() => openModal('r', r)}
                        >
                          Review &amp; Decide
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className={styles.empty}>
              <b>Queue clear</b>
              <div className={styles.muted} style={{ marginTop: 4 }}>
                No items awaiting human review in this queue.
              </div>
            </div>
          )
        )}
      </section>

      {/* Recent Decisions Card */}
      <section className={styles.card}>
        <h2 className={styles.h2}>Recent Decisions</h2>
        <div style={{ marginTop: 8 }}>
          {recentDecisions.length > 0 ? (
            recentDecisions.map(l => (
              <div key={l.id} className={styles.decisionRow}>
                <span className={`${styles.bd} ${l.ok ? styles.g : styles.r}`}>
                  {l.ok ? 'APPROVED' : 'DENIED'}
                </span>
                <b>{l.id}</b>
                <span className={`${styles.num} ${styles.muted}`}>{fmt(l.amt)}</span>
                <span className={styles.muted} style={{ flex: 1, minWidth: 0 }}>
                  {l.notes}
                </span>
                <a className={styles.monoLink} href="/audit">
                  {l.hash.slice(0, 8)}… ↗
                </a>
              </div>
            ))
          ) : (
            <div className={styles.muted} style={{ padding: '12px 0' }}>
              No decisions yet this session.
            </div>
          )}
        </div>
      </section>

      {/* Decision Modal */}
      {modalItem && (
        <div className={styles.modalBackdrop}>
          <div className={styles.modalCard}>
            <div className={styles.modalHead}>
              <div>
                <div className={styles.muted}>
                  {modalItem.kind === 'p' ? `${modalItem.item.id} · ${modalItem.item.ms}` : modalItem.item.id}
                </div>
                <h2 className={styles.h2} style={{ marginTop: 2 }}>
                  {modalItem.kind === 'p' ? 'Review Milestone Payout' : 'Review Recovery Intervention'}
                </h2>
              </div>
              <button className={styles.closeBtn} onClick={closeModal}>×</button>
            </div>

            {successSteps ? (
              <div style={{ marginTop: 16 }}>
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: 8,
                    background: successSteps.ok ? '#F3FBF6' : '#FEF6F6',
                    fontWeight: 600,
                    color: successSteps.ok ? '#1E7A4C' : '#B42830'
                  }}
                >
                  {successSteps.id}: {successSteps.ok ? 'APPROVED' : 'DENIED'}
                </div>

                <div style={{ marginTop: 8 }}>
                  {successSteps.steps.map((s, idx) => (
                    <div key={idx} className={styles.stepRow}>
                      <span style={{ color: '#2E9D65', fontWeight: 700 }}>✓</span>
                      <span>{s[0]}</span>
                    </div>
                  ))}
                </div>

                <div style={{ textAlign: 'right', marginTop: 16 }}>
                  <button className={`${styles.btn} ${styles.btnP}`} onClick={closeModal}>
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div>
                {/* 3 Metrics */}
                <div className={styles.modalTopMetrics}>
                  {modalItem.kind === 'p' ? (
                    <>
                      <div className={styles.topMetricBox}>
                        <div className={styles.muted}>Milestone Amount</div>
                        <b className={styles.num}>{fmt(modalItem.item.amt)}</b>
                      </div>
                      <div className={styles.topMetricBox}>
                        <div className={styles.muted}>Recipient</div>
                        <b>{modalItem.item.rcp}</b>
                      </div>
                      <div className={styles.topMetricBox}>
                        <div className={styles.muted}>Project</div>
                        <b>{modalItem.item.proj}</b>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className={styles.topMetricBox}>
                        <div className={styles.muted}>Amount at Risk</div>
                        <b className={styles.num}>{fmt(modalItem.item.amt)}</b>
                      </div>
                      <div className={styles.topMetricBox}>
                        <div className={styles.muted}>Customer</div>
                        <b>{modalItem.item.cust}</b>
                      </div>
                      <div className={styles.topMetricBox}>
                        <div className={styles.muted}>Proposed Action</div>
                        <code className={styles.mono}>{modalItem.item.act}</code>
                      </div>
                    </>
                  )}
                </div>

                {/* Mandate Guard Flag Warning */}
                <div className={styles.mandateFlagBox}>
                  <b style={{ color: '#B42830' }}>Mandate Guard Flag</b>
                  <div>
                    {modalItem.kind === 'p'
                      ? `Policy blocked autonomous payout because amount (${fmt(modalItem.item.amt)}) exceeds $200.00 cap. Human confirmation required.`
                      : `Policy blocked autonomous action: ${modalItem.item.why}. Human sign-off required.`}
                  </div>
                </div>

                {/* Evidence Summary */}
                <div style={{ marginTop: 16 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px' }}>Evidence Summary</h3>
                  {modalItem.kind === 'p' ? (
                    <div style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                      <div>
                        <span className={styles.muted}>GitHub PR: </span>
                        <a href={modalItem.item.pr} target="_blank" rel="noreferrer" className={styles.link}>
                          {modalItem.item.pr}
                        </a>
                      </div>
                      <div>
                        <span className={styles.muted}>Staging URL: </span>
                        <a href={modalItem.item.url} target="_blank" rel="noreferrer" className={styles.link}>
                          {modalItem.item.url}
                        </a>{' '}
                        <span className={`${styles.bd} ${styles.g}`}>HTTP 200 OK</span>
                      </div>
                      <div>
                        <span className={styles.muted}>Verifier Score: </span>
                        <b>{modalItem.item.score}/100</b> ({modalItem.item.note})
                      </div>
                      <div>
                        <span className={styles.muted}>Milestone: </span>
                        {modalItem.item.m}
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                      <div>
                        <span className={styles.muted}>Diagnosis: </span>
                        <code className={styles.mono}>{modalItem.item.diag}</code>
                      </div>
                      <div>
                        <span className={styles.muted}>Contact ladder: </span>
                        {modalItem.item.hist}
                      </div>
                      <div>
                        <span className={styles.muted}>Reconciliation: </span>
                        3-way check: no bank or ERP match found
                      </div>
                    </div>
                  )}
                </div>

                {/* Decision Form */}
                <form onSubmit={handleDecisionSubmit} style={{ marginTop: 16 }}>
                  <div className={styles.muted} style={{ fontWeight: 600, marginBottom: 6 }}>Decision</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <label className={`${styles.opt} ${decision === 'APPROVE' ? styles.optApproved : ''}`}>
                      <input
                        type="radio"
                        name="dec"
                        value="APPROVE"
                        checked={decision === 'APPROVE'}
                        onChange={() => setDecision('APPROVE')}
                      />
                      {modalItem.kind === 'p' ? 'Approve Payout' : 'Approve Action'}
                    </label>
                    <label className={`${styles.opt} ${decision === 'DENY' ? styles.optDenied : ''}`}>
                      <input
                        type="radio"
                        name="dec"
                        value="DENY"
                        checked={decision === 'DENY'}
                        onChange={() => setDecision('DENY')}
                      />
                      {modalItem.kind === 'p' ? 'Deny / Request Revisions' : 'Deny Action'}
                    </label>
                  </div>

                  <label className={styles.label} style={{ marginTop: 12 }}>
                    Reviewer Notes (required)
                    <textarea
                      className={styles.textarea}
                      value={notes}
                      onChange={e => setNotes(e.target.value)}
                    />
                  </label>
                  {notesError && <div className={styles.errorText}>{notesError}</div>}

                  <div className={styles.muted} style={{ marginTop: 8 }}>API call</div>
                  <code className={styles.mono} style={{ display: 'block', padding: '8px 12px', background: '#F0F3F8', borderRadius: 8, wordBreak: 'break-all' }}>
                    POST /submission-approvals/{modalItem.item.id}/decide {JSON.stringify({ decision, notes })}
                  </code>

                  <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
                    <button type="button" className={styles.btn} onClick={closeModal}>
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className={`${styles.btn} ${decision === 'APPROVE' ? styles.btnP : styles.btnDanger}`}
                      disabled={submitting}
                    >
                      {submitting
                        ? 'Executing…'
                        : decision === 'APPROVE'
                        ? 'Confirm Decision & Execute PayPal Payout'
                        : 'Confirm Decision & Request Revisions'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      )}

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
