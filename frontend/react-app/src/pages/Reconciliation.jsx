import { useState } from 'react';
import { showToast } from '../components/ui/Toast';
import styles from './Reconciliation.module.css';

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const INITIAL_SOURCES = [
  { k: 'pp', t: 'PayPal Gateway Report (.CSV)', f: 'paypal_nov_2026.csv', n: 184, u: 'txns' },
  { k: 'erp', t: 'Merchant ERP Invoices (.CSV)', f: 'erp_billing_nov.csv', n: 200, u: 'records' },
  { k: 'bk', t: 'Bank Offline Statement (.CSV)', f: 'bank_statement_nov.csv', n: 22, u: 'wires' }
];

const FN = ['Hannah Weiss', 'Carlos Ruiz', 'Aiko Tanaka', 'Daniel Okafor', 'Grace Liu', 'Samuel Reyes', 'Nora Ibrahim', 'Jonas Berg'];
const FA = [1200, 275, 640, 129, 890, 350, 520, 310];
const FS = [99, 97, 96, 94, 98, 93, 91, 95];

const INITIAL_PE = [
  { c: 'REC-2026-0051', n: 'Michael Anderson', a: 450, pp: 'FAILED (Card Declined)', w: 'WIRE-8891', d: 'Nov 10', s: 99, ok: true, inv: 'INV-2026-1019' },
  ...FN.slice(0, 7).map((n, i) => ({
    c: 'REC-2026-00' + (52 + i),
    n,
    a: FA[i],
    pp: ['FAILED (Card Declined)', 'FAILED (Insufficient Funds)'][i % 2],
    w: 'WIRE-88' + (85 - i),
    d: 'Nov ' + (10 - (i >> 1)),
    s: FS[i],
    ok: FS[i] >= 93,
    inv: 'INV-2026-10' + (40 + i)
  }))
];

const INITIAL_UN = [
  'Elena Petrov', 'Mark Davis', 'Yuki Sato', 'Fatima Noor', 'Liam Walsh', 'Ana Costa', 'Ben Carter',
  'Chloe Dubois', 'Ivan Novak', 'Maya Rao', 'Noah Fischer', 'Olivia Grant', 'Pablo Reyes', 'Quinn Adams',
  'Rosa Lindqvist', 'Sven Holm', 'Tara Bhatt', 'Umar Sheikh', 'Vera Kovacs', 'Will Tran', 'Xena Moore',
  'Yusuf Ali', 'Zoe Clark', 'Adam Brooks'
].map((n, i) => ({
  c: 'REC-2026-0' + (60 + i).toString().padStart(3, '0'),
  n,
  a: [89, 240, 415, 129, 760, 98, 310, 185][i % 8],
  pp: i % 5 === 0 ? 'NO TRANSACTION' : 'FAILED (Card Declined)',
  w: '',
  d: '',
  s: [38, 52, 44, 61, 29][i % 5],
  ok: false,
  inv: 'INV-2026-11' + (10 + i)
}));

async function sha256(obj) {
  try {
    const text = JSON.stringify(obj);
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(b)).map(x => x.toString(16).padStart(2, '0')).join('');
  } catch {
    return 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
  }
}

export default function Reconciliation() {
  const [sources, setSources] = useState(INITIAL_SOURCES);
  const [tabKey, setTabKey] = useState('pe');
  const [search, setSearch] = useState('');
  const [shownCount, setShownCount] = useState(10);
  const [paidElsewhere, setPaidElsewhere] = useState(INITIAL_PE);
  const [unmatched, setUnmatched] = useState(INITIAL_UN);
  const [selectedCase, setSelectedCase] = useState(null);
  const [drawerHash, setDrawerHash] = useState('');
  const [runningEngine, setRunningEngine] = useState(false);
  const [progressText, setProgressText] = useState('Starting…');
  const [progressWidth, setProgressWidth] = useState(0);
  const [lastRunTime, setLastRunTime] = useState('Nov 11, 07:55 UTC');

  const currentList = tabKey === 'pe' ? paidElsewhere : unmatched;
  const filteredList = currentList.filter(r => {
    const q = search.trim().toLowerCase();
    return !q || (r.c + r.n).toLowerCase().includes(q);
  });
  const visibleRows = tabKey === 'pe' ? filteredList : filteredList.slice(0, shownCount);

  const safeTotalAmount = paidElsewhere.reduce((s, r) => s + r.a, 0);

  const handleRunEngine = () => {
    if (runningEngine) return;
    setRunningEngine(true);
    const steps = [
      'Matching PayPal against ERP invoices…',
      'Matching bank wires against failed charges…',
      'Scoring fuzzy matches…',
      'Halting outreach on paid-elsewhere cases…'
    ];
    let i = 0;
    const interval = setInterval(() => {
      setProgressText(steps[i]);
      setProgressWidth(((i + 1) / steps.length) * 100);
      i++;
      if (i > steps.length) {
        clearInterval(interval);
        setRunningEngine(false);
        setProgressWidth(0);
        setLastRunTime(new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC');
        showToast('Reconciliation: 3-way matching completed: 8 cases marked Paid Elsewhere.', 'success');
      }
    }, 600);
  };

  const handleExportCsv = () => {
    const rows = [
      ['case', 'customer', 'amount', 'paypal_status', 'bank_ref', 'score', 'action'],
      ...paidElsewhere.concat(unmatched).map(x => [x.c, x.n, x.a, x.pp, x.w, x.s, x.w ? 'HALTED' : 'ACTIVE'])
    ];
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'reconciliation.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Reconciliation report exported.', 'success');
  };

  const openDrawer = async (row) => {
    setSelectedCase(row);
    const h = await sha256({ case: row.c, amount: row.a, bank_ref: row.w || null, score: row.s });
    setDrawerHash(h);
  };

  const handleConfirmMatch = (caseId) => {
    setPaidElsewhere(prev => prev.map(x => x.c === caseId ? { ...x, ok: true } : x));
    if (selectedCase?.c === caseId) {
      setSelectedCase(prev => ({ ...prev, ok: true }));
    }
    showToast(`${caseId} confirmed as paid elsewhere. Outreach stays permanently halted.`, 'success');
  };

  const handleFileUpload = (idx, file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showToast('That file is not a .csv. Export it as CSV and try again.', 'warning');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const rows = reader.result.split(/\r?\n/).filter(x => x.trim()).length - 1;
      if (rows < 1) {
        showToast(`${file.name} has no data rows. Check the export and upload again.`, 'warning');
        return;
      }
      setSources(prev => prev.map((s, i) => i === idx ? { ...s, f: file.name, n: rows } : s));
      showToast(`${file.name} uploaded: ${rows} ${sources[idx].u}.`, 'success');
    };
    reader.readAsText(file);
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Payment Reconciliation &amp; 3-Way Matching</h1>
          <p className={styles.sub}>
            Automatically match bank statements and merchant ledgers against PayPal transactions to prevent wrongful dunning.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btn} onClick={handleExportCsv}>Export report</button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={handleRunEngine} disabled={runningEngine}>
            {runningEngine ? 'Running Engine…' : 'Run 3-Way Reconciliation Engine'}
          </button>
        </div>
      </div>

      {/* KPI summary */}
      <section className={styles.kpiGrid} aria-label="Reconciliation summary">
        <div className={styles.kpiCard}>
          <span className={styles.muted}>Total ledger records</span>
          <div className={`${styles.bigNum} ${styles.num}`}>200</div>
          <span className={styles.muted} style={{ fontSize: 12 }}>Last run {lastRunTime}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.muted}>Perfect 3-way matches</span>
          <div className={`${styles.bigNum} ${styles.num}`}>
            168 <span className={styles.muted} style={{ fontSize: 14 }}>84%</span>
          </div>
          <span className={`${styles.bd} ${styles.g}`}>MATCHED</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.muted}>Unmatched invoices</span>
          <div className={`${styles.bigNum} ${styles.num}`}>
            24 <span className={styles.muted} style={{ fontSize: 14 }}>12%</span>
          </div>
          <span className={`${styles.bd} ${styles.a}`}>NEEDS REVIEW</span>
        </div>
        <div className={styles.kpiCard} style={{ borderColor: '#0070E0', background: '#F4F9FF' }}>
          <span className={styles.muted}>Paid elsewhere (offline / wire)</span>
          <div className={`${styles.bigNum} ${styles.num}`} style={{ color: '#003087' }}>
            8 <span className={styles.muted} style={{ fontSize: 14 }}>4%</span>
          </div>
          <span className={`${styles.bd} ${styles.b}`}>Halted from dunning</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.muted}>Matching confidence</span>
          <div className={`${styles.bigNum} ${styles.num}`}>98.5%</div>
          <span className={styles.muted}>Average fuzzy score</span>
        </div>
      </section>

      {/* Reconciliation sources */}
      <section className={styles.card} aria-label="Upload sources">
        <div className={styles.sourcesHead}>
          <h2 className={styles.h2}>Reconciliation sources</h2>
          <span className={styles.muted}>Drop a CSV on a source, or select it to browse</span>
        </div>

        <div className={styles.sourcesGrid}>
          {sources.map((z, i) => (
            <label
              key={z.k}
              className={styles.uploadZone}
              style={{
                borderColor: z.f ? '#2E9D65' : '#C5CEDB',
                background: z.f ? '#F7FCF9' : '#F8FAFC'
              }}
            >
              <input
                type="file"
                accept=".csv,text/csv"
                style={{ display: 'none' }}
                onChange={e => handleFileUpload(i, e.target.files[0])}
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className={styles.ico}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 16V4M7 9l5-5 5 5M4 20h16" />
                  </svg>
                </span>
                <b>{z.t}</b>
              </div>
              {z.f ? (
                <>
                  <div style={{ marginTop: 12 }}>
                    <span className={`${styles.bd} ${styles.g}`}>UPLOADED</span>
                  </div>
                  <div className={styles.mono} style={{ marginTop: 8 }}>{z.f}</div>
                  <div className={styles.muted} style={{ marginTop: 2 }}>{z.n} {z.u} · select to replace</div>
                </>
              ) : (
                <div className={styles.muted} style={{ marginTop: 12 }}>No file yet. Drop a .csv here.</div>
              )}
            </label>
          ))}
        </div>

        {runningEngine && (
          <div style={{ marginTop: 16 }}>
            <div className={styles.muted}>{progressText}</div>
            <div className={styles.progressBar}>
              <div className={styles.progressFill} style={{ width: `${progressWidth}%` }} />
            </div>
          </div>
        )}
      </section>

      {/* Discrepancies Table */}
      <section className={styles.card} aria-label="Discrepancies">
        <div className={styles.safeBanner}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4" />
          </svg>
          <div>
            <b>Safe!</b> Customer was NOT sent an embarrassing overdue notice.{' '}
            <span>{paidElsewhere.length} customers ({fmt(safeTotalAmount)}) protected from wrongful dunning.</span>
          </div>
        </div>

        <div className={styles.tableControls}>
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              className={`${styles.tab} ${tabKey === 'pe' ? styles.tabOn : ''}`}
              onClick={() => { setTabKey('pe'); setShownCount(10); }}
            >
              Paid elsewhere <span className={styles.badgeNum}>{paidElsewhere.length}</span>
            </button>
            <button
              className={`${styles.tab} ${tabKey === 'un' ? styles.tabOn : ''}`}
              onClick={() => { setTabKey('un'); setShownCount(10); }}
            >
              Unmatched <span className={styles.badgeNum}>{unmatched.length}</span>
            </button>
          </div>

          <input
            className={styles.input}
            placeholder="Filter by case or customer"
            style={{ width: 240 }}
            value={search}
            onChange={e => { setSearch(e.target.value); setShownCount(10); }}
          />
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Case</th>
                <th className={styles.th}>Customer</th>
                <th className={styles.th} style={{ textAlign: 'right' }}>Amount</th>
                <th className={styles.th}>PayPal status</th>
                <th className={styles.th}>Bank match</th>
                <th className={styles.th}>Score</th>
                <th className={styles.th}>System action</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.length > 0 ? (
                visibleRows.map(r => (
                  <tr key={r.c} className={styles.trHover} onClick={() => openDrawer(r)}>
                    <td className={styles.td}><code className={styles.mono}>{r.c}</code></td>
                    <td className={styles.td}><b>{r.n}</b></td>
                    <td className={`${styles.td} ${styles.num}`} style={{ textAlign: 'right' }}>{fmt(r.a)}</td>
                    <td className={styles.td}><span className={`${styles.bd} ${styles.r}`}>{r.pp}</span></td>
                    <td className={styles.td}>
                      {r.w ? (
                        <>
                          <span className={`${styles.bd} ${styles.b}`}>MATCH FOUND</span>
                          <div className={styles.muted}>{r.w} · {fmt(r.a)} received {r.d === 'Nov 10' ? 'yesterday' : r.d}</div>
                        </>
                      ) : (
                        <span className={styles.muted}>No bank match found</span>
                      )}
                    </td>
                    <td className={`${styles.td} ${styles.num}`}>{r.s}%</td>
                    <td className={styles.td}>
                      {r.w ? (
                        <>
                          <span className={`${styles.bd} ${styles.mutedBadge}`}>RECOVERY HALTED</span>
                          <div className={styles.muted}>{r.ok ? 'Match confirmed' : 'Awaiting manual confirm'}</div>
                        </>
                      ) : (
                        <>
                          <span className={`${styles.bd} ${styles.a}`}>RECOVERY ACTIVE</span>
                          <div className={styles.muted}>Flagged for review</div>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: 32 }}>
                    <b>No cases match.</b>
                    <div className={styles.muted}>Clear the filter to see all {tabKey === 'pe' ? 'paid-elsewhere' : 'unmatched'} cases.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {tabKey === 'un' && filteredList.length > shownCount && (
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <button className={styles.btn} style={{ height: 36 }} onClick={() => setShownCount(c => c + 10)}>
              Show 10 more
            </button>
          </div>
        )}
      </section>

      {/* Match Detail Drawer */}
      {selectedCase && (
        <>
          <div className={styles.backdrop} onClick={() => setSelectedCase(null)} />
          <aside className={styles.drawer} role="dialog" aria-modal="true">
            <div className={styles.drawerHead}>
              <div>
                <h2 className={styles.h2}>{selectedCase.c}</h2>
                <div className={styles.muted} style={{ marginTop: 2 }}>{selectedCase.n} · {selectedCase.inv}</div>
              </div>
              <button className={styles.closeBtn} onClick={() => setSelectedCase(null)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <div className={styles.drawerBody}>
              {/* 3-way match cards */}
              <div className={styles.threeWayGrid}>
                <div className={styles.miniCard}>
                  <div className={styles.miniCardTitle}>PayPal gateway</div>
                  <div className={styles.miniCardRow}><span className={styles.muted}>Amount:</span> <b>{fmt(selectedCase.a)}</b></div>
                  <div className={styles.miniCardRow}><span className={styles.muted}>Status:</span> <span>{selectedCase.pp}</span></div>
                  <div className={styles.miniCardRow}><span className={styles.muted}>Payer:</span> <span>{selectedCase.n}</span></div>
                </div>

                <div className={styles.miniCard}>
                  <div className={styles.miniCardTitle}>Merchant ERP</div>
                  <div className={styles.miniCardRow}><span className={styles.muted}>Amount:</span> <b>{fmt(selectedCase.a)}</b></div>
                  <div className={styles.miniCardRow}><span className={styles.muted}>Invoice:</span> <span>{selectedCase.inv}</span></div>
                  <div className={styles.miniCardRow}><span className={styles.muted}>Customer:</span> <span>{selectedCase.n}</span></div>
                </div>

                <div className={styles.miniCard}>
                  <div className={styles.miniCardTitle}>Bank statement</div>
                  {selectedCase.w ? (
                    <>
                      <div className={styles.miniCardRow}><span className={styles.muted}>Amount:</span> <b>{fmt(selectedCase.a)}</b></div>
                      <div className={styles.miniCardRow}><span className={styles.muted}>Reference:</span> <span>{selectedCase.w} · {selectedCase.d}</span></div>
                      <div className={styles.miniCardRow}><span className={styles.muted}>Sender:</span> <span>{selectedCase.n.split(' ').reverse().join(', ')}</span></div>
                    </>
                  ) : (
                    <div className={styles.muted}>No matching transaction found</div>
                  )}
                </div>
              </div>

              {/* Fuzzy score gauge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className={styles.muted}>Fuzzy match score</span>
                <span className={`${styles.num}`} style={{ fontSize: 28, fontWeight: 600 }}>{selectedCase.s}%</span>
                <span className={`${styles.bd} ${selectedCase.s >= 93 ? styles.g : selectedCase.s >= 60 ? styles.a : styles.r}`}>
                  {selectedCase.s >= 93 ? 'HIGH CONFIDENCE' : selectedCase.s >= 60 ? 'MEDIUM' : 'NO MATCH'}
                </span>
              </div>

              {/* Fuzzy score breakdowns */}
              {selectedCase.w && (
                <div style={{ display: 'grid', gap: 8, fontSize: 13 }}>
                  {[
                    ['Amount match', 100],
                    ['Payer name similarity', Math.min(99, selectedCase.s + 2)],
                    ['Date window', 96],
                    ['Reference pattern', Math.max(60, selectedCase.s - 6)]
                  ].map(p => (
                    <div key={p[0]} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ width: 180 }}>{p[0]}</span>
                      <span className={styles.track}>
                        <span className={styles.trackFill} style={{ width: `${p[1]}%` }} />
                      </span>
                      <b className={styles.num}>{p[1]}%</b>
                    </div>
                  ))}
                </div>
              )}

              {/* Status explanation */}
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: 8,
                  background: selectedCase.w ? '#E3F4EB' : '#FEF1D9',
                  fontSize: 13
                }}
              >
                {selectedCase.w ? (
                  <b>Recovery halted. No reminders will be sent to this customer.</b>
                ) : (
                  <b>Recovery still active. No bank payment found, so the contact ladder continues.</b>
                )}
              </div>

              {/* Audit proof */}
              <div>
                <div className={styles.muted}>Audit proof (SHA-256 of this match record)</div>
                <code className={styles.mono} style={{ display: 'block', wordBreak: 'break-all', padding: 12, background: '#F0F3F8', borderRadius: 8, marginTop: 4 }}>
                  {drawerHash}
                </code>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {selectedCase.w && !selectedCase.ok && (
                  <button className={`${styles.btn} ${styles.btnP}`} onClick={() => handleConfirmMatch(selectedCase.c)}>
                    Confirm match
                  </button>
                )}
                {selectedCase.w && selectedCase.ok && (
                  <span className={`${styles.bd} ${styles.g}`} style={{ alignSelf: 'center', padding: '6px 14px' }}>
                    MATCH CONFIRMED
                  </span>
                )}
                <a className={styles.btn} href="/audit">Open in audit trail</a>
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
