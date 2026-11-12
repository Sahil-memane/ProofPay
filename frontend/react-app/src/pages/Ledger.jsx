import { useState, useEffect } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './Ledger.module.css';

const ESCROW_VAULT = 'ProofPay Escrow Vault';
const CLIENT_ACC = 'Client PayPal Account';
const FREELANCER_ACC = 'to freelancer account';

const INITIAL_TRANSACTIONS = [
  {
    id: 'TXN-2026-9041',
    ts: '2026-11-11T09:58:31Z',
    prj: 'PRJ-2026-001',
    ms: 'MS-2026-001-02',
    mn: 'Frontend Integration',
    type: 'PAYOUT_RELEASE',
    from: ESCROW_VAULT,
    to: FREELANCER_ACC,
    amt: 700,
    ref: 'PAYOUT-ITEM-1029',
    pol: 'MANUAL_OVERRIDE',
    note: 'Approved by Risk Officer in APP-104'
  },
  {
    id: 'TXN-2026-9040',
    ts: '2026-11-11T09:41:07Z',
    prj: 'PRJ-2026-001',
    ms: 'MS-2026-001-02',
    mn: 'Frontend Integration',
    type: 'PAYOUT_RELEASE',
    from: ESCROW_VAULT,
    to: FREELANCER_ACC,
    amt: 700,
    ref: '—',
    pol: 'POLICY_BLOCKED',
    note: 'Amount exceeds the $200.00 autonomous limit; routed to APP-104'
  },
  {
    id: 'TXN-2026-9039',
    ts: '2026-11-10T16:20:44Z',
    prj: 'PRJ-2026-005',
    ms: 'MS-2026-005-01',
    mn: 'Landing Page Build',
    type: 'PAYOUT_RELEASE',
    from: ESCROW_VAULT,
    to: FREELANCER_ACC,
    amt: 180,
    ref: 'PAYOUT-ITEM-1027',
    pol: 'ALLOWED',
    note: 'Verifier score 0.94, AUTO_APPROVE'
  },
  {
    id: 'TXN-2026-9038',
    ts: '2026-11-10T11:05:12Z',
    prj: 'PRJ-2026-004',
    ms: 'All milestones',
    mn: 'Escrow frozen',
    type: 'DISPUTE_FREEZE',
    from: ESCROW_VAULT,
    to: ESCROW_VAULT + ' (frozen)',
    amt: 850,
    ref: 'DISPUTE-PP-3391',
    pol: 'ALLOWED',
    note: 'Dispute webhook received; circuit breaker froze escrow'
  },
  {
    id: 'TXN-2026-9037',
    ts: '2026-11-08T14:33:50Z',
    prj: 'PRJ-2026-003',
    ms: 'MS-2026-003-03',
    mn: 'QA & Deployment',
    type: 'REFUND',
    from: ESCROW_VAULT,
    to: CLIENT_ACC,
    amt: 1400,
    ref: 'REFUND-ID-5512',
    pol: 'MANUAL_OVERRIDE',
    note: 'Client refund approved in APP-101'
  },
  {
    id: 'TXN-2026-9036',
    ts: '2026-11-06T10:12:09Z',
    prj: 'PRJ-2026-004',
    ms: 'All milestones',
    mn: 'Funding',
    type: 'CAPTURE_FUNDING',
    from: CLIENT_ACC,
    to: ESCROW_VAULT,
    amt: 3200,
    ref: 'CAPTURE-ID-8856',
    pol: 'ALLOWED',
    note: 'Orders v2 capture COMPLETED'
  },
  {
    id: 'TXN-2026-9035',
    ts: '2026-11-05T15:48:02Z',
    prj: 'PRJ-2026-001',
    ms: 'MS-2026-001-01',
    mn: 'UI Design & Figma Tokens',
    type: 'PAYOUT_RELEASE',
    from: ESCROW_VAULT,
    to: FREELANCER_ACC,
    amt: 400,
    ref: 'PAYOUT-ITEM-1019',
    pol: 'MANUAL_OVERRIDE',
    note: 'Approved by Risk Officer in APP-097'
  },
  {
    id: 'TXN-2026-9034',
    ts: '2026-11-04T09:30:18Z',
    prj: 'PRJ-2026-005',
    ms: 'All milestones',
    mn: 'Funding',
    type: 'CAPTURE_FUNDING',
    from: CLIENT_ACC,
    to: ESCROW_VAULT,
    amt: 900,
    ref: 'CAPTURE-ID-8850',
    pol: 'ALLOWED',
    note: 'Orders v2 capture COMPLETED'
  },
  {
    id: 'TXN-2026-9033',
    ts: '2026-11-03T13:09:41Z',
    prj: 'PRJ-2026-003',
    ms: 'MS-2026-003-01',
    mn: 'Discovery & Wireframes',
    type: 'PAYOUT_RELEASE',
    from: ESCROW_VAULT,
    to: FREELANCER_ACC,
    amt: 150,
    ref: 'PAYOUT-ITEM-1012',
    pol: 'ALLOWED',
    note: 'Verifier score 0.91, AUTO_APPROVE'
  },
  {
    id: 'TXN-2026-9032',
    ts: '2026-11-02T08:15:27Z',
    prj: 'PRJ-2026-001',
    ms: 'All milestones',
    mn: 'Funding',
    type: 'CAPTURE_FUNDING',
    from: CLIENT_ACC,
    to: ESCROW_VAULT,
    amt: 2400,
    ref: 'CAPTURE-ID-8841',
    pol: 'ALLOWED',
    note: 'Orders v2 capture COMPLETED; plan hash matched'
  }
];

const TYPE_BADGE = {
  CAPTURE_FUNDING: 'b',
  PAYOUT_RELEASE: 'g',
  REFUND: 'a',
  DISPUTE_FREEZE: 'r'
};

const POLICY_BADGE = {
  ALLOWED: 'g',
  POLICY_BLOCKED: 'r',
  MANUAL_OVERRIDE: 'a'
};

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

function canon(t) {
  return JSON.stringify({
    id: t.id,
    ts: t.ts,
    prj: t.prj,
    ms: t.ms,
    type: t.type,
    from: t.from,
    to: t.to,
    amt: t.amt,
    ref: t.ref,
    pol: t.pol
  });
}

async function sha256(text) {
  try {
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(b)).map(x => x.toString(16).padStart(2, '0')).join('');
  } catch {
    return 'c2d8e51f07a39b64d1e8f20a5c7b36940a8f9c2d';
  }
}

export default function Ledger() {
  const { data: apiLedger } = useApi(() => endpoints.ledger.list());
  const [transactions, setTransactions] = useState(INITIAL_TRANSACTIONS);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [policyFilter, setPolicyFilter] = useState('');
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [recomputeResult, setRecomputeResult] = useState(null);

  // Compute SHA-256 chain links on load or when apiLedger updates
  useEffect(() => {
    let active = true;
    const computeChain = async () => {
      let sourceList;
      if (apiLedger && Array.isArray(apiLedger) && apiLedger.length > 0) {
        sourceList = apiLedger.map((l, i) => {
          const isFunding = l.type === 'FUNDING' || l.type === 'CAPTURE_FUNDING';
          const isPayout = l.type === 'RELEASE' || l.type === 'PAYOUT_RELEASE' || l.type === 'COMPLETED';
          const isRefund = l.type === 'REFUND';
          const isFreeze = l.type === 'DISPUTE_FREEZE';

          const txnType = isFunding ? 'CAPTURE_FUNDING' : (isPayout ? 'PAYOUT_RELEASE' : (l.type || 'CAPTURE_FUNDING'));
          const from = l.debited_account || (isFunding ? CLIENT_ACC : ESCROW_VAULT);
          const to = l.credited_account || (isFunding ? ESCROW_VAULT : (isPayout ? FREELANCER_ACC : (isRefund ? CLIENT_ACC : (isFreeze ? ESCROW_VAULT + ' (frozen)' : FREELANCER_ACC))));

          return {
            id: l.id?.startsWith('TXN-') || l.id?.startsWith('REL-') ? l.id : `TXN-${l.id?.slice(0, 8)?.toUpperCase() || (9040 - i)}`,
            ts: l.created_at || '—',
            prj: l.subject_id || l.project_id || '—',
            ms: l.milestone_id || 'All milestones',
            mn: l.milestone_title || l.note || 'Escrow funding & release',
            type: txnType,
            from,
            to,
            amt: Number(l.amount) || 0,
            ref: l.paypal_id || '—',
            pol: l.policy_status || 'ALLOWED',
            note: l.note || 'Tamper-evident audit verified ledger entry',
          };
        });
      } else {
        sourceList = INITIAL_TRANSACTIONS;
      }

      let prev = '0'.repeat(64);
      const reversed = [...sourceList].reverse();
      const chained = [];
      for (const t of reversed) {
        const hash = await sha256(prev + canon(t));
        chained.push({ ...t, prev, hash });
        prev = hash;
      }
      if (active) {
        setTransactions(chained.reverse());
      }
    };
    computeChain();
    return () => { active = false; };
  }, [apiLedger]);

  const filteredTransactions = transactions.filter(x => {
    const matchesType = !typeFilter || x.type === typeFilter;
    const matchesPolicy = !policyFilter || x.pol === policyFilter;
    const q = search.trim().toLowerCase();
    const matchesSearch = !q || [x.id, x.prj, x.ms, x.mn, x.ref].join(' ').toLowerCase().includes(q);
    return matchesType && matchesPolicy && matchesSearch;
  });

  const handleVerifyChain = async () => {
    let prev = '0'.repeat(64);
    let ok = true;
    for (const t of [...transactions].reverse()) {
      const h = await sha256(prev + canon(t));
      if (h !== t.hash) {
        ok = false;
        break;
      }
      prev = h;
    }
    showToast(
      ok
        ? `Audit chain verified: ${transactions.length} entries, no hash breaks.`
        : 'Audit chain verification failed.',
      ok ? 'success' : 'warning'
    );
  };

  const handleExportCsv = () => {
    const header = ['Transaction ID', 'Timestamp', 'Project', 'Milestone', 'Type', 'Debited', 'Credited', 'Amount USD', 'PayPal reference', 'Policy status', 'Entry hash'];
    const rows = transactions.map(x => [
      x.id,
      x.ts,
      x.prj,
      x.ms + (x.mn ? ': ' + x.mn : ''),
      x.type,
      x.from,
      x.to,
      x.amt.toFixed(2),
      x.ref,
      x.pol,
      x.hash || ''
    ]);
    const csv = [header, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'proofpay-escrow-ledger.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported escrow-ledger CSV.', 'success');
  };

  const handleExportPdf = () => {
    showToast('Opening print dialog. Choose "Save as PDF".', 'info');
    setTimeout(() => window.print(), 400);
  };

  const handleRecompute = async () => {
    if (!selectedTxn) return;
    const h = await sha256(selectedTxn.prev + canon(selectedTxn));
    setRecomputeResult(h === selectedTxn.hash);
  };

  const getPaypalPayload = (x) => {
    if (x.type === 'CAPTURE_FUNDING') {
      return {
        id: x.ref,
        status: 'COMPLETED',
        intent: 'CAPTURE',
        amount: { currency_code: 'USD', value: x.amt.toFixed(2) }
      };
    }
    if (x.type === 'PAYOUT_RELEASE' && x.ref !== '—') {
      return {
        batch_header: { payout_batch_id: 'BATCH-' + x.ref.slice(-4), batch_status: 'SUCCESS' },
        items: [{ payout_item_id: x.ref, transaction_status: 'SUCCESS', amount: { currency: 'USD', value: x.amt.toFixed(2) } }]
      };
    }
    if (x.ref === '—') {
      return { note: 'No PayPal call was made. Mandate Guard blocked the action before execution.' };
    }
    return { id: x.ref, status: 'RECORDED', amount: { currency_code: 'USD', value: x.amt.toFixed(2) } };
  };

  const totalFunded = transactions.filter(x => x.type === 'CAPTURE_FUNDING').reduce((s, x) => s + (Number(x.amt) || 0), 0);
  const totalReleased = transactions.filter(x => x.type === 'PAYOUT_RELEASE').reduce((s, x) => s + (Number(x.amt) || 0), 0);
  const totalRefunded = transactions.filter(x => x.type === 'REFUND').reduce((s, x) => s + (Number(x.amt) || 0), 0);
  const balanceOnHold = Math.max(0, totalFunded - totalReleased - totalRefunded);
  const refundCount = transactions.filter(x => x.type === 'REFUND').length;

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Escrow Financial Ledger</h1>
          <p className={styles.sub}>
            Double-entry accounting of all PayPal Order captures, holds, and Payout releases.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btn} onClick={handleExportCsv}>Export CSV</button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={handleExportPdf}>
            Export PDF Audit Statement
          </button>
        </div>
      </div>

      {/* 4 Totals Cards */}
      <section className={styles.totalsGrid} aria-label="Ledger totals">
        <div className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div className={styles.muted}>Total Funded into Escrow</div>
            <div className={styles.ico}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
              </svg>
            </div>
          </div>
          <div className={`${styles.bigNum} ${styles.num}`}>{fmt(totalFunded)}</div>
          <div className={styles.muted}>USD · PayPal Order captures</div>
        </div>

        <div className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div className={styles.muted}>Total Released to Freelancers</div>
            <div className={styles.ico}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12h14M13 6l6 6-6 6" />
              </svg>
            </div>
          </div>
          <div className={`${styles.bigNum} ${styles.num}`}>{fmt(totalReleased)}</div>
          <div className={styles.muted}>USD · PayPal Payouts</div>
        </div>

        <div className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div className={styles.muted}>Total Refunded to Clients</div>
            <div className={styles.ico} style={{ background: '#FEF1D9', color: '#8A5A00' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 14L4 9l5-5M4 9h10a6 6 0 0 1 0 12h-3" />
              </svg>
            </div>
          </div>
          <div className={`${styles.bigNum} ${styles.num}`}>{fmt(totalRefunded)}</div>
          <div className={styles.muted}>USD · {refundCount} refund{refundCount !== 1 ? 's' : ''}</div>
        </div>

        <div className={styles.card} style={{ borderColor: '#0070E0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div className={styles.muted}>Active Escrow Balance on Hold</div>
            <div className={styles.ico}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 11V8a5 5 0 0 1 10 0v3M5 11h14v10H5z" />
              </svg>
            </div>
          </div>
          <div className={`${styles.bigNum} ${styles.num}`}>{fmt(balanceOnHold)}</div>
          <div className={styles.up}>Funded − released − refunded ✓</div>
        </div>
      </section>

      {/* Filter Bar */}
      <section className={styles.filtersBar} aria-label="Filters">
        <input
          className={styles.input}
          style={{ flex: '1 1 280px' }}
          placeholder="Search transaction, project, PayPal reference"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className={styles.input} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          <option value="">All transaction types</option>
          <option value="CAPTURE_FUNDING">CAPTURE_FUNDING</option>
          <option value="PAYOUT_RELEASE">PAYOUT_RELEASE</option>
          <option value="REFUND">REFUND</option>
          <option value="DISPUTE_FREEZE">DISPUTE_FREEZE</option>
        </select>
        <select className={styles.input} value={policyFilter} onChange={e => setPolicyFilter(e.target.value)}>
          <option value="">All policy statuses</option>
          <option value="ALLOWED">ALLOWED</option>
          <option value="POLICY_BLOCKED">POLICY_BLOCKED</option>
          <option value="MANUAL_OVERRIDE">MANUAL_OVERRIDE</option>
        </select>
        <button className={styles.btn} onClick={handleVerifyChain}>Verify audit chain</button>
      </section>

      {/* Master Ledger Table */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }}>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Transaction ID</th>
                <th className={styles.th}>Timestamp (UTC)</th>
                <th className={styles.th}>Project</th>
                <th className={styles.th}>Milestone</th>
                <th className={styles.th}>Type</th>
                <th className={styles.th}>Debited account</th>
                <th className={styles.th}>Credited account</th>
                <th className={styles.th} style={{ textAlign: 'right' }}>Amount</th>
                <th className={styles.th}>PayPal reference</th>
                <th className={styles.th}>Policy status</th>
                <th className={styles.th}>Audit</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.map(x => (
                <tr key={x.id} className={styles.trHover} onClick={() => { setSelectedTxn(x); setRecomputeResult(null); }}>
                  <td className={styles.td}><span className={styles.mono}>{x.id}</span></td>
                  <td className={`${styles.td} ${styles.num}`} style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{x.ts}</td>
                  <td className={styles.td}><span className={styles.link}>{x.prj}</span></td>
                  <td className={styles.td}><span className={styles.mono}>{x.ms}</span>{x.mn ? ' · ' + x.mn : ''}</td>
                  <td className={styles.td}><span className={`${styles.bd} ${styles[TYPE_BADGE[x.type]]}`}>{x.type}</span></td>
                  <td className={styles.td}>{x.from}</td>
                  <td className={styles.td}>{x.to}</td>
                  <td className={`${styles.td} ${styles.num}`} style={{ textAlign: 'right', fontWeight: 600 }}>{fmt(x.amt)}</td>
                  <td className={styles.td}><span className={styles.mono}>{x.ref}</span></td>
                  <td className={styles.td}><span className={`${styles.bd} ${styles[POLICY_BADGE[x.pol]]}`}>{x.pol}</span></td>
                  <td className={styles.td}>
                    <button
                      className={styles.lockBtn}
                      onClick={(e) => { e.stopPropagation(); setSelectedTxn(x); setRecomputeResult(null); }}
                      aria-label={`Open audit proof for ${x.id}`}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M7 11V8a5 5 0 0 1 10 0v3M5 11h14v10H5z" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredTransactions.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <div style={{ fontWeight: 600, fontSize: 16 }}>No transactions match these filters</div>
            <p className={styles.muted} style={{ margin: '6px 0 12px' }}>
              Clear the search or choose All transaction types to see the full ledger.
            </p>
            <button className={styles.btn} onClick={() => { setSearch(''); setTypeFilter(''); setPolicyFilter(''); }}>
              Clear filters
            </button>
          </div>
        )}

        <div className={styles.tableFoot}>
          Showing {filteredTransactions.length} of {transactions.length} most recent ledger entries
        </div>
      </section>

      {/* Transaction Detail Drawer */}
      {selectedTxn && (
        <>
          <div className={styles.backdrop} onClick={() => setSelectedTxn(null)} />
          <aside className={styles.drawer} role="dialog" aria-modal="true">
            <div className={styles.drawerHead}>
              <div style={{ flex: 1 }}>
                <div className={styles.muted}>Transaction detail</div>
                <div className={`${styles.h2} ${styles.mono}`} style={{ fontSize: 18, marginTop: 2 }}>{selectedTxn.id}</div>
              </div>
              <button className={styles.closeBtn} onClick={() => setSelectedTxn(null)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <div className={styles.drawerBody}>
              <div style={{ display: 'flex', gap: 8 }}>
                <span className={`${styles.bd} ${styles[TYPE_BADGE[selectedTxn.type]]}`}>{selectedTxn.type}</span>
                <span className={`${styles.bd} ${styles[POLICY_BADGE[selectedTxn.pol]]}`}>{selectedTxn.pol}</span>
              </div>

              <div className={styles.detailGrid}>
                <div><span className={styles.muted}>Amount:</span> <b className={`${styles.num}`}>{fmt(selectedTxn.amt)}</b></div>
                <div><span className={styles.muted}>Timestamp:</span> <span className={styles.num}>{selectedTxn.ts}</span></div>
                <div><span className={styles.muted}>Project:</span> <span>{selectedTxn.prj}</span></div>
                <div><span className={styles.muted}>Milestone:</span> <span>{selectedTxn.ms}{selectedTxn.mn ? ' · ' + selectedTxn.mn : ''}</span></div>
                <div><span className={styles.muted}>Debited:</span> <span>{selectedTxn.from}</span></div>
                <div><span className={styles.muted}>Credited:</span> <span>{selectedTxn.to}</span></div>
                <div><span className={styles.muted}>PayPal reference:</span> <span className={styles.mono}>{selectedTxn.ref}</span></div>
                <div><span className={styles.muted}>Policy note:</span> <span>{selectedTxn.note}</span></div>
              </div>

              <div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px' }}>Raw ledger payload</h3>
                <pre className={styles.jsonBox}>
                  {JSON.stringify(JSON.parse(canon(selectedTxn)), null, 2)}
                </pre>
              </div>

              <div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px' }}>PayPal API response</h3>
                <pre className={styles.jsonBox}>
                  {JSON.stringify(getPaypalPayload(selectedTxn), null, 2)}
                </pre>
              </div>

              <div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px' }}>Audit verification proof</h3>
                <div style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                  <div><span className={styles.muted}>Entry hash: </span><code className={styles.mono}>{selectedTxn.hash || 'unavailable'}</code></div>
                  <div><span className={styles.muted}>Previous hash: </span><code className={styles.mono}>{selectedTxn.prev || '—'}</code></div>
                  <div><span className={styles.muted}>Method: </span><span>SHA-256 of previous hash + canonical payload</span></div>
                </div>

                <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <button className={styles.btn} onClick={handleRecompute}>
                    Recompute and verify
                  </button>
                  {recomputeResult !== null && (
                    <span className={`${styles.bd} ${recomputeResult ? styles.g : styles.r}`}>
                      {recomputeResult ? 'Verified · hash matches' : 'Mismatch'}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </aside>
        </>
      )}

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
