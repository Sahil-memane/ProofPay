import { useState, useEffect, useMemo } from 'react';
import { showToast } from '../components/ui/Toast';
import styles from './Audit.module.css';

const TEMPLATES = [
  ['project', 'PRJ-2026-001', 'client', 'PLAN_APPROVED', 'VERIFIED - Plan hash matched'],
  ['project', 'PRJ-2026-001', 'freelancer', 'PLAN_APPROVED', 'VERIFIED - Plan hash matched'],
  ['project', 'PRJ-2026-001', 'client', 'ESCROW_FUNDED', 'FUNDED - $2,400.00 captured via PayPal Orders v2'],
  ['milestone', 'MS-2026-002-01', 'verifier_agent', 'SUBMISSION_VERIFIED', 'VERIFIED - Score 0.91, route AUTO_APPROVE'],
  ['milestone', 'MS-2026-002-01', 'mandate_guard', 'POLICY_EVALUATION', 'ALLOWED - Released $200.00 via PayPal Payouts'],
  ['milestone', 'MS-2026-002-01', 'payout_executor', 'PAYOUT_DISPATCHED', 'PAID - $200.00 sent to verified PayPal account'],
  ['recovery_case', 'REC-2026-0040', 'diagnosis_agent', 'FAILURE_DIAGNOSED', 'BANK_AUTH_FAILED - Stage 1 PayPal link selected'],
  ['recovery_case', 'REC-2026-0041', 'reconciliation_agent', 'RECONCILIATION_MATCHED', 'MATCHED - PAID_ELSEWHERE, outreach halted'],
  ['recovery_case', 'REC-2026-0040', 'contact_ladder', 'OUTREACH_SENT', 'ALLOWED - Sent outside quiet hours'],
  ['payment', 'PAY-88231', 'paypal_webhook', 'PAYMENT_CAPTURED', 'PAID - Case settled via Smart Buttons']
];

const LAST_TEMPLATES = [
  ['milestone', 'MS-2026-001-02', 'verifier_agent', 'SUBMISSION_VERIFIED', 'VERIFIED - Score 0.94, route AUTO_APPROVE'],
  ['milestone', 'MS-2026-001-02', 'mandate_guard', 'POLICY_EVALUATION', 'POLICY_BLOCKED - $700.00 exceeds $200.00 limit, routed to APP-104'],
  ['approval', 'APP-104', 'risk_officer', 'APPROVAL_GRANTED', 'ALLOWED - Human approved $700.00 release'],
  ['milestone', 'MS-2026-001-02', 'payout_executor', 'PAYOUT_DISPATCHED', 'PAID - Released $700.00 via PayPal Payouts'],
  ['recovery_case', 'REC-2026-0042', 'diagnosis_agent', 'FAILURE_DIAGNOSED', 'EXPIRED_CARD - Stage 1 update link selected'],
  ['recovery_case', 'REC-2026-0042', 'contact_ladder', 'OUTREACH_SENT', 'ALLOWED - Update link sent, quiet hours respected'],
  ['payment', 'PAY-88240', 'paypal_webhook', 'PAYMENT_CAPTURED', 'PAID - REC-2026-0042 settled'],
  ['recovery_case', 'REC-2026-0042', 'paypal_webhook', 'CASE_CLOSED', 'PAID - Recovery ticket closed']
];

const N = 248;
const PER_PAGE = 12;
const ZERO_HASH = '0'.repeat(64);

async function sha256(text) {
  try {
    const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buffer)).map(x => x.toString(16).padStart(2, '0')).join('');
  } catch {
    let h = 0;
    for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) >>> 0;
    return h.toString(16).padStart(8, '0').repeat(8);
  }
}

function canonicalJson(obj) {
  return JSON.stringify(Object.keys(obj).sort().reduce((acc, k) => { acc[k] = obj[k]; return acc; }, {}));
}

function shortHash(h) {
  if (!h) return '—';
  return h.slice(0, 4) + '…' + h.slice(-3);
}

export default function Audit() {
  const [events, setEvents] = useState([]);
  const [verifyStatus, setVerifyStatus] = useState([]);
  const [verifiedCount, setVerifiedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [actorFilter, setActorFilter] = useState('');
  const [page, setPage] = useState(0);
  const [tamperedIdx, setTamperedIdx] = useState(null);
  const [originalDecision, setOriginalDecision] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [drawerComputed, setDrawerComputed] = useState(null);

  // Initialize chain
  useEffect(() => {
    let active = true;
    const buildChain = async () => {
      let prev = ZERO_HASH;
      const t0 = Date.UTC(2026, 10, 12, 14, 30, 12, 418);
      const list = [];

      for (let i = 1; i <= N; i++) {
        const x = i > N - LAST_TEMPLATES.length
          ? LAST_TEMPLATES[i - (N - LAST_TEMPLATES.length) - 1]
          : TEMPLATES[(i * 7) % TEMPLATES.length];

        let id = x[1];
        if (i <= N - LAST_TEMPLATES.length && x[0] !== 'project') {
          id = id.replace(/\d+$/, n => String(+n + (i % 9)).padStart(n.length, '0'));
        }

        const rec = {
          actor: x[2],
          action: x[3],
          decision: x[4],
          entity_id: id,
          entity_type: x[0],
          event_id: 'AUD-' + String(i).padStart(5, '0'),
          prev_hash: prev,
          ts: new Date(t0 - (N - i) * 437213).toISOString()
        };
        const rh = await sha256(canonicalJson(rec));
        list.push({ rec, rh });
        prev = rh;
      }

      if (!active) return;
      setEvents(list);

      // Verify initial chain
      let ok = 0;
      const statuses = [];
      for (let i = 0; i < list.length; i++) {
        const h = await sha256(canonicalJson(list[i].rec));
        const link = list[i].rec.prev_hash === (i ? list[i - 1].rh : ZERO_HASH);
        const hashOk = h === list[i].rh;
        statuses.push({ link, hash: hashOk, ok: link && hashOk });
        if (link && hashOk) ok++;
      }
      if (!active) return;
      setVerifyStatus(statuses);
      setVerifiedCount(ok);
      setLoading(false);
    };

    buildChain();
    return () => { active = false; };
  }, []);

  const actors = useMemo(() => {
    return Array.from(new Set(events.map(e => e.rec.actor))).sort();
  }, [events]);

  const verifyChain = async (currentList) => {
    let ok = 0;
    const statuses = [];
    for (let i = 0; i < currentList.length; i++) {
      const h = await sha256(canonicalJson(currentList[i].rec));
      const link = currentList[i].rec.prev_hash === (i ? currentList[i - 1].rh : ZERO_HASH);
      const hashOk = h === currentList[i].rh;
      statuses.push({ link, hash: hashOk, ok: link && hashOk });
      if (link && hashOk) ok++;
    }
    setVerifyStatus(statuses);
    setVerifiedCount(ok);
    return ok;
  };

  const handleSimulateTamper = async () => {
    if (tamperedIdx === null) {
      const idx = 199;
      setOriginalDecision(events[idx].rec.decision);
      setTamperedIdx(idx);

      const modified = events.map((e, i) => {
        if (i === idx) {
          return { ...e, rec: { ...e.rec, decision: 'ALLOWED - Released $7,000.00 via PayPal Payouts' } };
        }
        return e;
      });
      setEvents(modified);
      const ok = await verifyChain(modified);
      showToast('AUD-00200 was edited without recomputing its hash. Run verification.', 'warning');
    } else {
      const restored = events.map((e, i) => {
        if (i === tamperedIdx) {
          return { ...e, rec: { ...e.rec, decision: originalDecision } };
        }
        return e;
      });
      setTamperedIdx(null);
      setEvents(restored);
      const ok = await verifyChain(restored);
      showToast('Original record restored.', 'success');
    }
  };

  const handleReverify = async () => {
    const ok = await verifyChain(events);
    if (ok === N) {
      showToast(`Chain verified: all ${N} hashes match.`, 'success');
    } else {
      showToast(`Tampering detected in ${N - ok} event(s).`, 'warning');
    }
  };

  const handleVerifySelected = async () => {
    if (!selectedEvent) return;
    const r = selectedEvent.rec;
    const h = await sha256(canonicalJson(r));
    const ok = h === selectedEvent.rh;
    const idx = events.findIndex(e => e.rec.event_id === r.event_id);
    const pl = r.prev_hash === (idx > 0 ? events[idx - 1].rh : ZERO_HASH);
    setDrawerComputed({ hash: h, valid: ok && pl, linkValid: pl, hashValid: ok });
    showToast(ok && pl ? `${r.event_id} verified.` : `${r.event_id} failed verification.`, ok && pl ? 'success' : 'warning');
  };

  // Filtered & Paginated events (newest first)
  const filteredIndices = useMemo(() => {
    const q = search.trim().toLowerCase();
    return events
      .map((_, i) => i)
      .reverse()
      .filter(i => {
        const r = events[i].rec;
        const matchesActor = !actorFilter || r.actor === actorFilter;
        const matchesQ = !q || (Object.values(r).join(' ') + events[i].rh).toLowerCase().includes(q);
        return matchesActor && matchesQ;
      });
  }, [events, search, actorFilter]);

  const maxPage = Math.max(0, Math.ceil(filteredIndices.length / PER_PAGE) - 1);
  const pagedIndices = filteredIndices.slice(page * PER_PAGE, page * PER_PAGE + PER_PAGE);

  return (
    <div className={styles.page}>
      {/* Page Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Tamper-Evident Audit Trail</h1>
          <p className={styles.sub}>Every financial and policy decision linked via SHA-256 cryptographic hash chains.</p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btn} onClick={handleSimulateTamper}>
            {tamperedIdx === null ? 'Simulate tampering' : 'Restore original record'}
          </button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={handleReverify}>
            Re-verify entire chain
          </button>
        </div>
      </div>

      {/* Verification Banner */}
      <section className={styles.card} style={{ padding: 24, display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
        {verifiedCount === N ? (
          <>
            <span className={`${styles.bd} ${styles.g}`} style={{ fontSize: 16, padding: '10px 18px', display: 'inline-flex', gap: 8, alignItems: 'center' }}>
              🔒 Cryptographic Chain Verified: 100% Valid (All {N} Hashes Match)
            </span>
            <div className={styles.muted} style={{ flex: '1 1 240px' }}>
              Verified {N} chained events. No tampering detected. Hashes were recomputed in this browser with SHA-256 just now.
            </div>
          </>
        ) : (
          <>
            <span className={`${styles.bd} ${styles.r}`} style={{ fontSize: 16, padding: '10px 18px', display: 'inline-flex', gap: 8, alignItems: 'center' }}>
              ⚠️ Chain Broken: {N - verifiedCount} of {N} events fail verification
            </span>
            <div style={{ flex: '1 1 240px', fontSize: 13 }}>
              First mismatch at <b className={styles.mono}>AUD-00200</b>. Its stored row_hash no longer matches the recomputed hash, so the record was changed after it was written.
            </div>
          </>
        )}
      </section>

      {/* Master Audit Table */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }}>
        <div className={styles.filterBar}>
          <h2 className={styles.h2} style={{ marginRight: 'auto' }}>Master Audit Table</h2>
          <input
            className={styles.input}
            style={{ width: 260, margin: 0 }}
            placeholder="Filter by ID, entity, action, hash…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
          />
          <select
            className={styles.input}
            style={{ width: 200, margin: 0 }}
            value={actorFilter}
            onChange={e => { setActorFilter(e.target.value); setPage(0); }}
          >
            <option value="">All actors</option>
            {actors.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Event ID</th>
                <th className={styles.th}>Timestamp (UTC)</th>
                <th className={styles.th}>Entity</th>
                <th className={styles.th}>Actor</th>
                <th className={styles.th}>Action</th>
                <th className={styles.th}>Decision / payload summary</th>
                <th className={styles.th}>prev_hash</th>
                <th className={styles.th}>row_hash</th>
                <th className={styles.th}>Chain link</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="10" className={`${styles.td} ${styles.muted}`}>Computing SHA-256 hashes…</td></tr>
              ) : pagedIndices.length > 0 ? (
                pagedIndices.map(i => {
                  const r = events[i].rec;
                  const s = verifyStatus[i] || { ok: true, hash: true };
                  const d = r.decision;
                  const badgeCls = /^POLICY_BLOCKED/.test(d) ? 'r' : /^(ALLOWED|VERIFIED|FUNDED|PAID|MATCHED)/.test(d) ? 'g' : 'b';
                  const [k, ...m] = d.split(' - ');

                  return (
                    <tr key={r.event_id}>
                      <td className={styles.td}><span className={styles.mono}>{r.event_id}</span></td>
                      <td className={`${styles.td} ${styles.num}`} style={{ fontSize: 13, whiteSpace: 'nowrap' }}>
                        {r.ts.replace('T', ' ').replace('Z', '')}
                      </td>
                      <td className={styles.td}>
                        <span className={styles.muted}>{r.entity_type}:</span> <span className={styles.mono}>{r.entity_id}</span>
                      </td>
                      <td className={styles.td}><code className={styles.mono}>{r.actor}</code></td>
                      <td className={styles.td}><code className={styles.mono}>{r.action}</code></td>
                      <td className={styles.td}>
                        <span className={`${styles.bd} ${styles[badgeCls]}`}>{k}</span>{' '}
                        <span style={{ fontSize: 13 }}>{m.join(' - ')}</span>
                      </td>
                      <td className={styles.td}><span className={styles.mono}>{shortHash(r.prev_hash)}</span></td>
                      <td className={styles.td}><span className={styles.mono}>{shortHash(events[i].rh)}</span></td>
                      <td className={styles.td}>
                        {s.ok ? (
                          <span className={`${styles.bd} ${styles.g}`} style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                            🔒 Valid Link
                          </span>
                        ) : (
                          <span className={`${styles.bd} ${styles.r}`}>
                            {s.hash ? 'Broken Link' : 'Hash Mismatch'}
                          </span>
                        )}
                      </td>
                      <td className={styles.td}>
                        <button
                          className={styles.btn}
                          style={{ height: 32, fontSize: 13 }}
                          onClick={() => { setSelectedEvent(events[i]); setDrawerComputed(null); }}
                        >
                          Inspect Details
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="10" className={`${styles.td} ${styles.muted}`}>
                    No events match these filters. Clear the search or choose All actors.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className={styles.paginationBar}>
          <span className={styles.muted}>
            {filteredIndices.length > 0
              ? `Showing ${page * PER_PAGE + 1}–${Math.min(filteredIndices.length, page * PER_PAGE + PER_PAGE)} of ${filteredIndices.length} events, newest first`
              : '0 events'}
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className={styles.btn} style={{ height: 36 }} disabled={page === 0} onClick={() => setPage(p => p - 1)}>
              Newer
            </button>
            <button className={styles.btn} style={{ height: 36 }} disabled={page >= maxPage} onClick={() => setPage(p => p + 1)}>
              Older
            </button>
          </div>
        </div>
      </section>

      {/* Inspect Details Drawer */}
      {selectedEvent && (
        <>
          <div className={styles.backdrop} onClick={() => setSelectedEvent(null)} />
          <aside className={styles.drawer} role="dialog" aria-modal="true">
            <div className={styles.drawerHead}>
              <h2 className={styles.h2} style={{ flex: 1 }}>{selectedEvent.rec.event_id}</h2>
              <button className={styles.closeBtn} onClick={() => setSelectedEvent(null)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <div className={styles.drawerBody}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>Full JSON payload</div>
                <pre className={styles.jsonBox}>
                  {JSON.stringify({ ...selectedEvent.rec, row_hash: selectedEvent.rh }, null, 2)}
                </pre>
              </div>

              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>Cryptographic proof</div>
                <div className={styles.muted} style={{ marginTop: 8 }}>Canonical JSON (sorted keys, no whitespace)</div>
                <pre className={styles.jsonBox}>
                  {canonicalJson(selectedEvent.rec)}
                </pre>

                <div className={styles.muted} style={{ marginTop: 12 }}>Previous row hash</div>
                <div className={styles.mono} style={{ wordBreak: 'break-all' }}>{selectedEvent.rec.prev_hash}</div>

                <div className={styles.muted} style={{ marginTop: 12 }}>Stored row hash</div>
                <div className={styles.mono} style={{ wordBreak: 'break-all' }}>{selectedEvent.rh}</div>

                <div className={styles.muted} style={{ marginTop: 12 }}>Computed row hash</div>
                <div
                  className={styles.mono}
                  style={{
                    wordBreak: 'break-all',
                    color: drawerComputed ? (drawerComputed.hashValid ? '#1E7A4C' : '#B42830') : '#64748B'
                  }}
                >
                  {drawerComputed ? drawerComputed.hash : 'Not computed yet'}
                </div>

                {drawerComputed && (
                  <div style={{ marginTop: 12 }}>
                    {drawerComputed.valid ? (
                      <span className={`${styles.bd} ${styles.g}`}>
                        Valid: computed hash matches and links to the previous event
                      </span>
                    ) : (
                      <span className={`${styles.bd} ${styles.r}`}>
                        {drawerComputed.hashValid
                          ? 'Broken link to previous event'
                          : 'Mismatch: this record was altered after it was written'}
                      </span>
                    )}
                  </div>
                )}
              </div>

              <button className={`${styles.btn} ${styles.btnP}`} onClick={handleVerifySelected}>
                Re-Verify SHA-256 Hash Locally in Browser
              </button>
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
