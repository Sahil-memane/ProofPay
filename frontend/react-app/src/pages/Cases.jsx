import { useState, useEffect } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './Cases.module.css';

const BASE_COUNTS = { all: 150, ACTIVE: 38, PAID: 101, HALTED: 8, UNRECOVERED: 3 };

const INITIAL_CASES = [
  { id: 'REC-2026-0042', n: 'Sarah Johnson', e: 'sarah@example.com', inv: 'INV-2026-1024', a: 350, dx: 'EXPIRED_CARD', st: 1, q: false, rc: 'MATCHED', s: 'ACTIVE', m: 1110, ev: [], pend: null },
  { id: 'REC-2026-0041', n: 'Michael Anderson', e: 'michael@example.com', inv: 'INV-2026-1019', a: 450, dx: 'INSUFFICIENT_FUNDS', st: 0, q: false, rc: 'PAID_ELSEWHERE', s: 'HALTED', m: null, ev: [], pend: null },
  { id: 'REC-2026-0040', n: 'Priya Nair', e: 'priya@example.com', inv: 'SUB-8841', a: 129, dx: 'BANK_AUTH_FAILED', st: 1, q: true, rc: 'MATCHED', s: 'ACTIVE', m: null, ev: [], pend: null },
  { id: 'REC-2026-0039', n: 'Tom Becker', e: 'tom@example.com', inv: 'INV-2026-1011', a: 890, dx: 'GATEWAY_ERROR', st: 0, q: false, rc: 'MATCHED', s: 'PAID', m: null, ev: [], pend: null },
  { id: 'REC-2026-0038', n: 'Lena Ortiz', e: 'lena@example.com', inv: 'INV-2026-1008', a: 275, dx: 'EXPIRED_CARD', st: 2, q: false, rc: 'MATCHED', s: 'ACTIVE', m: 390, ev: [], pend: null },
  { id: 'REC-2026-0037', n: 'David Kim', e: 'david@example.com', inv: 'SUB-7730', a: 1200, dx: 'INSUFFICIENT_FUNDS', st: 3, q: true, rc: 'UNMATCHED', s: 'ACTIVE', m: null, ev: [], pend: null },
  { id: 'REC-2026-0036', n: 'Aisha Khan', e: 'aisha@example.com', inv: 'INV-2026-0997', a: 64, dx: 'EXPIRED_CARD', st: 0, q: false, rc: 'MATCHED', s: 'PAID', m: null, ev: [], pend: null },
  { id: 'REC-2026-0035', n: 'Omar Haddad', e: 'omar@example.com', inv: 'INV-2026-0990', a: 540, dx: 'BANK_AUTH_FAILED', st: 3, q: false, rc: 'MATCHED', s: 'UNRECOVERED', m: null, ev: [], pend: null },
  { id: 'REC-2026-0034', n: 'Grace Liu', e: 'grace@example.com', inv: 'SUB-7702', a: 220, dx: 'INSUFFICIENT_FUNDS', st: 2, q: false, rc: 'MATCHED', s: 'ACTIVE', m: 2640, ev: [], pend: null },
  { id: 'REC-2026-0033', n: 'Carlos Mendes', e: 'carlos@example.com', inv: 'INV-2026-0981', a: 99, dx: 'EXPIRED_CARD', st: 0, q: false, rc: 'MATCHED', s: 'PAID', m: null, ev: [], pend: null },
  { id: 'REC-2026-0032', n: 'Nina Petrova', e: 'nina@example.com', inv: 'INV-2026-0975', a: 760, dx: 'GATEWAY_ERROR', st: 1, q: false, rc: 'MATCHED', s: 'HALTED', m: null, ev: [], pend: null },
  { id: 'REC-2026-0031', n: "James O'Neil", e: 'james@example.com', inv: 'INV-2026-0968', a: 310, dx: 'EXPIRED_CARD', st: 1, q: true, rc: 'UNMATCHED', s: 'ACTIVE', m: null, ev: [], pend: null }
];

const CODE_MAP = {
  EXPIRED_CARD: 'INSTRUMENT_DECLINED',
  INSUFFICIENT_FUNDS: 'INSUFFICIENT_FUNDS',
  BANK_AUTH_FAILED: 'AUTHORIZATION_FAILED',
  GATEWAY_ERROR: 'GATEWAY_TIMEOUT'
};

const EXP_MAP = {
  EXPIRED_CARD: 'Customer card expired on 10/26. Soft reminder dispatched with secure PayPal payment method update token.',
  INSUFFICIENT_FUNDS: 'Bank declined for insufficient funds. A smart retry is scheduled after the customer’s typical payroll date.',
  BANK_AUTH_FAILED: 'Bank requested strong customer authentication that was not completed. A 1-click PayPal biometric authorization link was sent.',
  GATEWAY_ERROR: 'Transient gateway timeout, not a customer fault. Immediate retry with exponential backoff.'
};

const STAGE_NAMES = ['', 'Stage 1: Soft Update Link', 'Stage 2: Firm Warning', 'Stage 3: Executive Pause'];
const STAGE_COLORS = ['', 'b', 'a', 'r'];
const STATUS_COLORS = { ACTIVE: 'g', PAID: 'g', HALTED: 'a', UNRECOVERED: 'r' };
const RECON_COLORS = { MATCHED: 'b', UNMATCHED: 'a', PAID_ELSEWHERE: 'r' };

const fmt = (n) => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

function generateHash() {
  return 'sha256:' + Array.from({ length: 4 }, () => Math.floor(Math.random() * 65536).toString(16).padStart(4, '0')).join('').slice(0, 6) + '…' + Math.floor(Math.random() * 65536).toString(16).padStart(4, '0');
}

export default function Cases() {
  const [cases, setCases] = useState(INITIAL_CASES);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedCase, setSelectedCase] = useState(null);

  const { data: apiData } = useApi(() => endpoints.cases.list());

  // Merge API data when available
  useEffect(() => {
    if (apiData && Array.isArray(apiData) && apiData.length > 0) {
      setCases(prev => {
        const merged = [...prev];
        apiData.forEach(ac => {
          const idx = merged.findIndex(c => c.id === ac.case_id || c.id === ac.id);
          const mapped = {
            id: ac.case_id || ac.id,
            n: ac.customer_name || ac.customer_email || 'Customer',
            e: ac.customer_email || 'customer@example.com',
            inv: ac.invoice_id || 'INV-2026',
            a: ac.amount || 250,
            dx: ac.diagnosis || 'EXPIRED_CARD',
            st: ac.stage || 1,
            q: ac.quiet_hours ?? false,
            rc: ac.reconciliation_status || 'MATCHED',
            s: ac.state || ac.status || 'ACTIVE',
            m: ac.next_action_minutes || 600,
            ev: ac.audit_events || [],
            pend: null
          };
          if (idx >= 0) {
            merged[idx] = { ...merged[idx], ...mapped };
          } else {
            merged.unshift(mapped);
          }
        });
        return merged;
      });
    }
  }, [apiData]);

  // Compute live counts
  const counts = {
    all: BASE_COUNTS.all + (cases.length - INITIAL_CASES.length),
    ACTIVE: BASE_COUNTS.ACTIVE + (cases.filter(c => c.s === 'ACTIVE').length - INITIAL_CASES.filter(c => c.s === 'ACTIVE').length),
    PAID: BASE_COUNTS.PAID + (cases.filter(c => c.s === 'PAID').length - INITIAL_CASES.filter(c => c.s === 'PAID').length),
    HALTED: BASE_COUNTS.HALTED + (cases.filter(c => c.s === 'HALTED').length - INITIAL_CASES.filter(c => c.s === 'HALTED').length),
    UNRECOVERED: BASE_COUNTS.UNRECOVERED + (cases.filter(c => c.s === 'UNRECOVERED').length - INITIAL_CASES.filter(c => c.s === 'UNRECOVERED').length)
  };

  const filteredCases = cases.filter(c => {
    const matchesFilter = filter === 'all' || c.s === filter;
    const q = search.trim().toLowerCase();
    const matchesSearch = !q || [c.n, c.e, c.inv, c.dx, c.id].some(f => (f || '').toLowerCase().includes(q));
    return matchesFilter && matchesSearch;
  });

  const getTimeline = (c) => {
    const events = [
      ['Day 0 08:30 UTC', `Payment failure received (${CODE_MAP[c.dx] || c.dx}).`, true],
      ['Day 0 08:31 UTC', c.rc === 'PAID_ELSEWHERE' ? 'Reconciliation matched an offline wire. Case halted; outreach permanently blocked.' : 'Case created; reconciliation passed.', true]
    ];
    if (c.rc !== 'PAID_ELSEWHERE') {
      events.push(['Day 0 09:00 UTC', 'Stage 1 PayPal payment link generated and sent.', true]);
      if (c.s === 'PAID') {
        events.push(['Day 1 10:12 UTC', 'PayPal webhook captured payment. Case marked PAID.', true]);
      } else if (c.s === 'ACTIVE' || c.s === 'UNRECOVERED') {
        if (c.st >= 2) events.push(['Day 2 09:00 UTC', 'Stage 2 firm warning sent.', true]);
        if (c.st >= 3) events.push(['Day 4 09:00 UTC', 'Stage 3 executive pause: account review flagged.', true]);
        if (c.s === 'UNRECOVERED') {
          events.push(['Day 7 09:00 UTC', 'Ladder exhausted without payment. Case marked UNRECOVERED.', true]);
        } else if (c.st < 3) {
          events.push(['Day 2 09:00 UTC', `(+48h ladder gap) Stage ${c.st + 1} reminder scheduled.`, false]);
          events.push(['Day 2 21:00 UTC', 'Quiet hours active; outreach paused until 08:00 UTC next morning.', false]);
        }
      } else {
        events.push(['Day 3 10:00 UTC', 'Recovery halted by operator.', true]);
      }
    }
    return events.concat((c.ev || []).map(e => [e.ts || 'Just now', e.desc || e.detail || e.payload_summary || e.event_type, true, e.hash]));
  };

  const handleHalt = (caseObj) => {
    const updated = {
      ...caseObj,
      s: 'HALTED',
      ev: [...(caseObj.ev || []), { ts: 'Day 2 14:30 UTC (simulated)', desc: 'Recovery halted by operator.', hash: generateHash() }]
    };
    setCases(prev => prev.map(c => c.id === caseObj.id ? updated : c));
    if (selectedCase?.id === caseObj.id) setSelectedCase(updated);
    showToast(`Recovery halted for ${caseObj.id}. Outreach stopped.`, 'warning');
  };

  const handleReopen = async (caseObj) => {
    try {
      await endpoints.cases.reopen(caseObj.id);
    } catch {
      // offline/demo fallback
    }
    const updated = {
      ...caseObj,
      s: 'ACTIVE',
      st: 1,
      m: 1440,
      ev: [...(caseObj.ev || []), { ts: 'Day 2 14:30 UTC (simulated)', desc: 'Case reopened. Restarting at Stage 1.', hash: generateHash() }]
    };
    setCases(prev => prev.map(c => c.id === caseObj.id ? updated : c));
    if (selectedCase?.id === caseObj.id) setSelectedCase(updated);
    showToast(`POST /cases/${caseObj.id}/reopen — case is active again.`, 'success');
  };

  const handlePaidElsewhere = (caseObj) => {
    const updated = {
      ...caseObj,
      rc: 'PAID_ELSEWHERE',
      s: 'HALTED',
      ev: [...(caseObj.ev || []), { ts: 'Day 2 14:30 UTC (simulated)', desc: 'Marked Paid Elsewhere. Outreach permanently halted.', hash: generateHash() }]
    };
    setCases(prev => prev.map(c => c.id === caseObj.id ? updated : c));
    if (selectedCase?.id === caseObj.id) setSelectedCase(updated);
    showToast('Marked Paid Elsewhere. Reminders permanently blocked.', 'warning');
  };

  const handleEscalate = (caseObj) => {
    const pendId = 'APP-' + (106 + cases.filter(x => x.pend).length);
    const updated = {
      ...caseObj,
      pend: pendId,
      ev: [...(caseObj.ev || []), { ts: 'Day 2 14:30 UTC (simulated)', desc: `Human escalation requested (${pendId}).`, hash: generateHash() }]
    };
    setCases(prev => prev.map(c => c.id === caseObj.id ? updated : c));
    if (selectedCase?.id === caseObj.id) setSelectedCase(updated);
    showToast(`Policy Alert: Escalation routed to Human Approvals Queue (${pendId}).`, 'warning');
  };

  const handleDecide = (caseObj, decision) => {
    const pend = caseObj.pend;
    const updated = {
      ...caseObj,
      pend: null,
      s: decision === 'DENY' ? 'HALTED' : caseObj.s,
      ev: [...(caseObj.ev || []), { ts: 'Day 2 14:30 UTC (simulated)', desc: `${pend} decided: ${decision}.`, hash: generateHash() }]
    };
    setCases(prev => prev.map(c => c.id === caseObj.id ? updated : c));
    if (selectedCase?.id === caseObj.id) setSelectedCase(updated);
    showToast(`POST /approvals/${caseObj.id}/decide — ${decision}. Recorded in audit trail.`, decision === 'DENY' ? 'warning' : 'success');
  };

  return (
    <div className={styles.page}>
      {/* Page Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Recovery Cases</h1>
          <p className={styles.sub}>Every failed payment, its diagnosis, contact ladder stage, and next scheduled action.</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <a href="/recovery-overview" className={styles.btn}>Recovery Overview</a>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <section className={styles.card}>
        <div className={styles.bar}>
          <div className={styles.pills} role="group" aria-label="Filter by status">
            {[
              ['all', `All Cases (${counts.all})`],
              ['ACTIVE', `Active (${counts.ACTIVE})`],
              ['PAID', `Recovered (${counts.PAID})`],
              ['HALTED', `Halted (${counts.HALTED})`],
              ['UNRECOVERED', `Unrecovered (${counts.UNRECOVERED})`]
            ].map(([k, t]) => (
              <button
                key={k}
                className={`${styles.tab} ${filter === k ? styles.tabOn : ''}`}
                onClick={() => setFilter(k)}
              >
                {t}
              </button>
            ))}
          </div>

          <div className={styles.searchWrap}>
            <svg className={styles.searchIco} viewBox="0 0 24 24" aria-hidden="true">
              <path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5" />
            </svg>
            <input
              className={styles.searchInput}
              placeholder="Name, email, invoice ID or diagnosis"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Table */}
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Case ID</th>
                <th className={styles.th}>Customer</th>
                <th className={styles.th}>Invoice / Subscription</th>
                <th className={styles.th}>Amount at risk</th>
                <th className={styles.th}>Diagnosis</th>
                <th className={styles.th}>Current stage</th>
                <th className={styles.th}>Quiet hours</th>
                <th className={styles.th}>Reconciliation</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>Next action</th>
                <th className={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.length > 0 ? (
                filteredCases.map(c => (
                  <tr key={c.id}>
                    <td className={styles.td}>
                      <a href="#" className={styles.monoLink} onClick={(e) => { e.preventDefault(); setSelectedCase(c); }}>
                        {c.id}
                      </a>
                    </td>
                    <td className={styles.td}>
                      <b>{c.n}</b>
                      <div className={styles.muted}>{c.e}</div>
                    </td>
                    <td className={styles.td}>
                      <code className={styles.mono}>{c.inv}</code>
                    </td>
                    <td className={`${styles.td} ${styles.num}`}>
                      {fmt(c.a)}
                    </td>
                    <td className={styles.td}>
                      <code className={styles.mono}>{c.dx}</code>
                    </td>
                    <td className={styles.td}>
                      {c.st && c.s === 'ACTIVE' ? (
                        <span className={`${styles.bd} ${styles[STAGE_COLORS[c.st]]}`}>
                          {STAGE_NAMES[c.st]}
                        </span>
                      ) : (
                        <span className={styles.muted}>—</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      {c.s === 'ACTIVE' ? (
                        c.q ? (
                          <span className={`${styles.bd} ${styles.a}`}>Quiet Hours (9pm-8am) - Paused</span>
                        ) : (
                          <span className={`${styles.bd} ${styles.g}`}>Active Hours - OK</span>
                        )
                      ) : (
                        <span className={styles.muted}>—</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      <span className={`${styles.bd} ${styles[RECON_COLORS[c.rc]] || styles.b}`}>
                        {c.rc}
                      </span>
                    </td>
                    <td className={styles.td}>
                      <span className={`${styles.bd} ${styles[STATUS_COLORS[c.s]] || styles.g}`}>
                        {c.s}
                      </span>
                    </td>
                    <td className={styles.td}>
                      {c.s !== 'ACTIVE' ? (
                        <span className={styles.muted}>—</span>
                      ) : c.q ? (
                        <span className={styles.muted}>Paused during quiet hours</span>
                      ) : c.m ? (
                        <span className={`${styles.num} ${styles.muted}`}>
                          In {Math.floor(c.m / 60)}h {c.m % 60}m
                        </span>
                      ) : (
                        <span className={styles.muted}>—</span>
                      )}
                    </td>
                    <td className={styles.td} style={{ whiteSpace: 'nowrap' }}>
                      <button
                        className={styles.rowBtn}
                        onClick={() => setSelectedCase(c)}
                      >
                        View Timeline
                      </button>{' '}
                      <a
                        className={styles.rowBtn}
                        href={`/pay?case_id=${c.id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Portal
                      </a>{' '}
                      {c.s === 'ACTIVE' && (
                        <button
                          className={`${styles.rowBtn} ${styles.haltBtn}`}
                          onClick={() => handleHalt(c)}
                        >
                          Halt
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="11" style={{ textAlign: 'center', padding: 40, color: '#64748B' }}>
                    No cases match your filters.{' '}
                    <a href="#" onClick={(e) => { e.preventDefault(); setFilter('all'); setSearch(''); }}>
                      Clear filters
                    </a>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className={styles.tableFoot}>
          Showing {filteredCases.length} of {BASE_COUNTS.all} cases (sample page)
        </div>
      </section>

      {/* Case Details Drawer */}
      {selectedCase && (
        <>
          <div className={styles.backdrop} onClick={() => setSelectedCase(null)} />
          <aside className={styles.drawer} role="dialog" aria-modal="true">
            <div className={styles.drawerHead}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className={styles.muted}><code className={styles.mono}>{selectedCase.id}</code></div>
                <h2 className={styles.drawerTitle}>{selectedCase.n}</h2>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 4, flexWrap: 'wrap' }}>
                  <span className={`${styles.num}`} style={{ fontSize: 20, fontWeight: 600 }}>{fmt(selectedCase.a)}</span>
                  <span className={styles.muted}>outstanding</span>
                  <span className={`${styles.bd} ${styles[STATUS_COLORS[selectedCase.s]] || styles.g}`}>{selectedCase.s}</span>
                </div>
              </div>
              <button className={styles.closeBtn} onClick={() => setSelectedCase(null)} aria-label="Close case details">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <div className={styles.drawerBody}>
              {selectedCase.pend && (
                <div className={styles.escalationCard}>
                  <div style={{ fontWeight: 600 }}>Pending human approval · {selectedCase.pend}</div>
                  <div style={{ margin: '4px 0 12px', fontSize: 13, color: '#64748B' }}>
                    Escalation is waiting for a decision. <a href="/approvals" className={styles.link}>Approvals Queue →</a>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className={`${styles.btn} ${styles.btnP}`} style={{ height: 40 }} onClick={() => handleDecide(selectedCase, 'APPROVE')}>Approve</button>
                    <button className={styles.btn} style={{ height: 40, color: '#B42830' }} onClick={() => handleDecide(selectedCase, 'DENY')}>Deny</button>
                  </div>
                </div>
              )}

              {/* Diagnosis */}
              <div className={styles.subCard}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>Diagnosis</div>
                <div style={{ margin: '2px 0 6px' }}>
                  <code className={styles.mono}>{selectedCase.dx}</code>
                </div>
                <div style={{ fontSize: 13, color: '#172B4D' }}>{EXP_MAP[selectedCase.dx] || 'Automated diagnosis in progress.'}</div>
              </div>

              {/* Reconciliation check */}
              <div className={styles.subCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>Reconciliation check</div>
                  <span className={`${styles.bd} ${styles[RECON_COLORS[selectedCase.rc]] || styles.b}`}>{selectedCase.rc}</span>
                </div>
                <div style={{ marginTop: 6, fontSize: 13, color: '#64748B' }}>
                  {selectedCase.rc === 'PAID_ELSEWHERE'
                    ? `Verified against Bank CSV: offline payment of ${fmt(selectedCase.a)} found. Outreach permanently halted.`
                    : selectedCase.rc === 'UNMATCHED'
                    ? 'No gateway or ERP match yet. Held for manual review before further contact.'
                    : 'Verified against Bank CSV: No offline match found. Safe to contact.'}
                </div>
              </div>

              {/* Timeline */}
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px' }}>Audit Timeline</h3>
                <ol className={styles.timeline}>
                  {getTimeline(selectedCase).map((ev, i, arr) => (
                    <li key={i} className={styles.timelineItem}>
                      <span className={ev[2] ? styles.dotDone : styles.dotPending} />
                      {i < arr.length - 1 && <span className={styles.timelineLine} />}
                      <div style={{ flex: 1 }}>
                        <div className={`${styles.muted} ${styles.num}`} style={{ fontSize: 12 }}>
                          {ev[0]}{ev[2] ? '' : ' · scheduled'}
                        </div>
                        <div style={{ fontSize: 13, marginTop: 2 }}>{ev[1]}</div>
                        {ev[3] && (
                          <div style={{ marginTop: 4 }}>
                            <code className={styles.mono} style={{ fontSize: 11 }}>{ev[3]}</code>{' '}
                            <a href="/audit" className={styles.link} style={{ fontSize: 11 }}>Audit</a>
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>

            {/* Actions footer */}
            <div className={styles.drawerActions}>
              {selectedCase.s === 'ACTIVE' ? (
                <>
                  <a
                    className={`${styles.btn} ${styles.btnP}`}
                    href={`/pay?case_id=${selectedCase.id}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ textDecoration: 'none' }}
                  >
                    Open Customer Pay Portal
                  </a>
                  <button
                    className={styles.btn}
                    onClick={() => handleEscalate(selectedCase)}
                    disabled={!!selectedCase.pend}
                  >
                    Request Human Escalation
                  </button>
                  <button
                    className={styles.btn}
                    onClick={() => handlePaidElsewhere(selectedCase)}
                  >
                    Mark Paid Elsewhere
                  </button>
                  <button
                    className={styles.btn}
                    style={{ color: '#B42830' }}
                    onClick={() => handleHalt(selectedCase)}
                  >
                    Halt Recovery
                  </button>
                </>
              ) : selectedCase.s === 'PAID' ? (
                <span className={styles.muted}>Case closed. No further actions.</span>
              ) : (
                <button
                  className={`${styles.btn} ${styles.btnP}`}
                  onClick={() => handleReopen(selectedCase)}
                >
                  Reopen Case
                </button>
              )}
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
