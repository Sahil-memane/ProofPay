import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { toast } from '../components/ui/Toast';
import styles from './Integrations.module.css';

const APIS = [
  { name: 'PayPal Orders v2', use: 'Creates escrow capture orders, authorizes payments, and links webhook authorizations.', ep: 'POST /v2/checkout/orders', calls: '1,420', ok: '99.8%', p95: '210ms' },
  { name: 'PayPal Payouts', use: 'Dispatches automated and HITL-approved milestone releases to freelancer wallets.', ep: 'POST /v1/payments/payouts', calls: '380', ok: '100%', p95: '340ms' },
  { name: 'PayPal Invoicing', use: 'Generates single-use recovery invoices with embedded payment links.', ep: 'POST /v2/invoicing/invoices', calls: '512', ok: '99.2%', p95: '180ms' },
  { name: 'PayPal Webhooks', use: 'Ingests real-time dispute, charge-failed, and capture-completed events.', ep: 'POST /webhooks/paypal', calls: '3,890', ok: '99.9%', p95: '95ms' },
];

const INITIAL_EVENTS = [
  { id: 'WH-7A41', type: 'PAYMENT.CAPTURE.COMPLETED', cat: 'capture', res: 'Escrow funding · PRJ-2026-001 · $2,400.00 USD', st: 'PROCESSED', time: 'Nov 11, 09:12', hash: '9c1e4f…a47f', tone: 'g' },
  { id: 'WH-7A3E', type: 'PAYMENT.PAYOUTS-ITEM.SUCCEEDED', cat: 'payout', res: 'Milestone 1 payout · Rahul Sharma · $400.00 USD', st: 'PROCESSED', time: 'Nov 11, 08:47', hash: 'b27d10…3c9e', tone: 'g' },
  { id: 'WH-7A39', type: 'BILLING.SUBSCRIPTION.PAYMENT.FAILED', cat: 'recovery', res: 'REC-2026-0042 · Sarah Johnson · $350.00 USD · EXPIRED_CARD', st: 'PROCESSED', time: 'Nov 11, 07:55', hash: '41af88…d02b', tone: 'a' },
  { id: 'WH-7A33', type: 'CUSTOMER.DISPUTE.CREATED', cat: 'dispute', res: 'Dispute on subscription charge · circuit breaker armed, recovery halted', st: 'PROCESSED', time: 'Nov 10, 22:31', hash: 'e8c3a1…76b4', tone: 'r' },
  { id: 'WH-7A2B', type: 'PAYMENT.CAPTURE.DENIED', cat: 'recovery', res: 'REC-2026-0041 · Michael Anderson · $450.00 USD', st: 'PROCESSED', time: 'Nov 10, 19:14', hash: '3d90f2…11aa', tone: 'r' },
];

const REPOS = [
  { name: 'rsharma/acme-shop', note: 'PR #42 merged · CI passed', st: 'SYNCED', tone: 'g' },
  { name: 'proofpay-team/core-escrow', note: 'Main branch · staging reachable', st: 'SYNCED', tone: 'g' },
  { name: 'acme-org/billing-service', note: 'PR #18 open · 3 checks pending', st: 'PENDING', tone: 'a' },
];

export default function Integrations() {
  const { role } = useAuth();
  const [isTesting, setIsTesting] = useState(false);
  const [hooksOpen, setHooksOpen] = useState(false);
  const [sigVerifyOn, setSigVerifyOn] = useState(true);
  const [rotateOpen, setRotateOpen] = useState(false);
  const [keyId, setKeyId] = useState('K-2026-0917-f3a9');
  const [filterCat, setFilterCat] = useState('all');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [csvWhen] = useState('Nov 10, 18:40');
  const [csvRows] = useState(214);
  const [csvMatched] = useState(14);

  const canManage = role === 'admin' || role === 'risk_officer';

  const handleTestConnection = () => {
    setIsTesting(true);
    setTimeout(() => {
      setIsTesting(false);
      toast.success('PayPal sandbox connection verified: HTTP 200 OK, latency 182ms.');
    }, 800);
  };

  const handleRotateKeys = () => {
    const nextKey = `K-2026-1111-${Math.random().toString(36).slice(2, 6)}`;
    setKeyId(nextKey);
    setRotateOpen(false);
    toast.success(`PayPal API keys rotated. New active key: ${nextKey}`);
  };

  const handleReplayEvent = (e, ev) => {
    e.stopPropagation();
    toast.success(`Webhook ${ev.id} (${ev.type}) replayed successfully.`);
  };

  const filteredEvents = events.filter(e => filterCat === 'all' || e.cat === filterCat);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>Integrations &amp; PayPal Connect</h1>
          <p>Connection health, API scopes, evidence connectors and the live webhook feed that drives escrow, payouts and recovery.</p>
        </div>
        <div className={styles.actionsGroup}>
          <button
            className={styles.btn}
            onClick={handleTestConnection}
            disabled={!canManage || isTesting}
          >
            {isTesting ? 'Testing…' : 'Test Connection'}
          </button>
          <button
            className={styles.btn}
            onClick={() => setHooksOpen(!hooksOpen)}
            disabled={!canManage}
          >
            {hooksOpen ? 'Close Webhooks' : 'Manage Webhooks'}
          </button>
          <button
            className={`${styles.btn} ${styles.btnDanger}`}
            onClick={() => setRotateOpen(true)}
            disabled={!canManage}
          >
            Rotate API Keys
          </button>
        </div>
      </div>

      {!canManage && (
        <div className={styles.roleNotice}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l10 18H2zM12 10v5M12 18h.01" />
          </svg>
          <span>Read-only for the current role. Switch to <b>Risk Officer / Admin</b> to test the connection, rotate keys or replay webhooks.</span>
        </div>
      )}

      {/* Master PayPal Card */}
      <section className={styles.masterCard} aria-label="PayPal integration">
        <div className={styles.masterLeft}>
          <div className={styles.ppLogo}>PP</div>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className={styles.masterTitle}>PayPal Business</span>
              <span className={`${styles.badge} ${styles.badgeGreen}`}>CONNECTED</span>
            </div>
            <div className={styles.masterSub}>Sandbox environment · REST API · last health check 4 min ago</div>
          </div>
        </div>
        <div className={styles.masterMetrics}>
          <div>
            <div className={styles.metricLabel}>Merchant ID</div>
            <div className={styles.metricVal} style={{ fontFamily: 'JetBrains Mono', fontSize: 14 }}>M-•••••1094</div>
          </div>
          <div>
            <div className={styles.metricLabel}>Median latency</div>
            <div className={styles.metricVal}>182 ms</div>
          </div>
          <div>
            <div className={styles.metricLabel}>API success · 24h</div>
            <div className={styles.metricVal} style={{ color: '#4CC38A' }}>99.6%</div>
          </div>
        </div>
      </section>

      {/* Client Credentials & Key Info */}
      <div className={styles.card} style={{ display: 'flex', flexWrap: 'wrap', gap: 24 }}>
        <div style={{ flex: '1 1 240px' }}>
          <div className={styles.metricLabel} style={{ color: 'var(--muted)' }}>Client ID</div>
          <div className={styles.mono} style={{ marginTop: 4 }}>AaB4••••••••••••••••Xk9Q</div>
        </div>
        <div style={{ flex: '1 1 280px' }}>
          <div className={styles.metricLabel} style={{ color: 'var(--muted)' }}>Client secret</div>
          <div className={styles.mono} style={{ marginTop: 4 }}>
            •••••••••••••••• <span style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--muted)' }}>stored server-side only</span>
          </div>
        </div>
        <div style={{ flex: '1 1 200px' }}>
          <div className={styles.metricLabel} style={{ color: 'var(--muted)' }}>Active key ID</div>
          <div className={styles.mono} style={{ marginTop: 4 }}>{keyId}</div>
        </div>
      </div>

      {/* Active APIs Grid */}
      <div className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>Active APIs</h2>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>4 of 4 enabled</span>
        </div>
        <div className={styles.gridCards}>
          {APIS.map(a => (
            <div key={a.name} className={styles.itemCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{a.name}</span>
                <span className={`${styles.badge} ${styles.badgeGreen}`}>ENABLED</span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted)', minHeight: 36 }}>{a.use}</div>
              <span className={styles.mono} style={{ background: '#F0F3F8', padding: '4px 8px', borderRadius: 6, alignSelf: 'flex-start' }}>
                {a.ep}
              </span>
              <div style={{ display: 'flex', gap: 16, borderTop: '1px solid var(--border)', paddingTop: 10, marginTop: 'auto' }}>
                <div><div style={{ fontSize: 11, color: 'var(--muted)' }}>Calls 24h</div><b>{a.calls}</b></div>
                <div><div style={{ fontSize: 11, color: 'var(--muted)' }}>Success</div><b>{a.ok}</b></div>
                <div><div style={{ fontSize: 11, color: 'var(--muted)' }}>p95</div><b>{a.p95}</b></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Webhook Endpoint Config (Toggled) */}
      {hooksOpen && (
        <section className={styles.card} aria-label="Webhook endpoint">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>Webhook Endpoint</h2>
            <button className={`${styles.btn} ${styles.btnSm}`} onClick={() => setHooksOpen(false)}>Close</button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, marginTop: 16 }}>
            <div style={{ flex: '1 1 360px' }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Listener URL</div>
              <div className={styles.mono} style={{ marginTop: 4, padding: '10px 12px', background: '#F0F3F8', borderRadius: 8 }}>
                https://api.proofpay.example/webhooks/paypal
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                <input
                  type="checkbox"
                  checked={sigVerifyOn}
                  onChange={(e) => setSigVerifyOn(e.target.checked)}
                  style={{ width: 18, height: 18 }}
                />
                <div>
                  <div style={{ fontWeight: 500, fontSize: 14 }}>Verify webhook signature</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>Events failing verification are rejected and logged, never processed.</div>
                </div>
              </div>
            </div>
            <div style={{ flex: '1 1 360px' }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Subscribed events</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                {['PAYMENT.CAPTURE.COMPLETED', 'PAYMENT.PAYOUTS-ITEM.SUCCEEDED', 'BILLING.SUBSCRIPTION.PAYMENT.FAILED', 'CUSTOMER.DISPUTE.CREATED'].map(s => (
                  <span key={s} className={styles.mono} style={{ background: '#F0F3F8', padding: '3px 8px', borderRadius: 6 }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Additional Integrations: GitHub & Bank Feed */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 24 }}>
        <div className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: '#E6F0FC', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 5L3 12l5 7M16 5l5 7-5 7M14 4l-4 16" />
                </svg>
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>GitHub Evidence Connector</div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>OAuth · read-only PR and CI access</div>
              </div>
            </div>
            <span className={`${styles.badge} ${styles.badgeGreen}`}>CONNECTED</span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 13, margin: '8px 0 16px' }}>
            The AI Verification Agent reads linked pull requests, diffs and CI results to score each milestone submission.
          </p>
          <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
            {REPOS.map((r, i) => (
              <div key={r.name} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '10px 12px', borderTop: i > 0 ? '1px solid var(--border)' : 0 }}>
                <span className={styles.mono} style={{ flex: 1 }}>{r.name}</span>
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>{r.note}</span>
                <span className={`${styles.badge} ${r.tone === 'g' ? styles.badgeGreen : styles.badgeAmber}`}>{r.st}</span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button className={`${styles.btn} ${styles.btnSm}`} onClick={() => toast.info('GitHub app permissions verified.')}>
              Link repository
            </button>
            <button className={`${styles.btn} ${styles.btnSm}`} onClick={() => toast.success('GitHub evidence synced.')}>
              Sync now
            </button>
          </div>
        </div>

        <div className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: '#E6F0FC', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 10l9-6 9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18" />
                </svg>
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>Bank Statement CSV Parser</div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>Feeds 3-way reconciliation</div>
              </div>
            </div>
            <span className={`${styles.badge} ${styles.badgeGreen}`}>READY</span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 13, margin: '8px 0 16px' }}>
            Offline wires and ACH credits are matched against failed gateway charges so customers who already paid are never chased.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <div style={{ background: '#F0F3F8', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Last import</div>
              <b>{csvWhen}</b>
            </div>
            <div style={{ background: '#F0F3F8', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Rows parsed</div>
              <b>{csvRows}</b>
            </div>
            <div style={{ background: '#F0F3F8', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Matched</div>
              <b>{csvMatched}</b>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <Link to="/reconciliation" className={`${styles.btn} ${styles.btnSm} ${styles.btnPrimary}`} style={{ textDecoration: 'none' }}>
              Open Reconciliation
            </Link>
          </div>
        </div>
      </section>

      {/* Webhook Event Log */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>Webhook Event Log</h2>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
              Select an event to inspect its payload. Replays are idempotent.
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['all', 'capture', 'payout', 'recovery', 'dispute'].map(cat => (
              <button
                key={cat}
                className={`${styles.tab} ${filterCat === cat ? styles.tabActive : ''}`}
                style={{ height: 32, padding: '0 10px', fontSize: 12 }}
                onClick={() => setFilterCat(cat)}
              >
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Event</th>
                <th className={styles.th}>Resource</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>Received</th>
                <th className={styles.th}>Audit hash</th>
                <th className={styles.th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map(e => (
                <tr
                  key={e.id}
                  className={styles.tr}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedEvent(e)}
                >
                  <td className={styles.td}>
                    <div className={styles.mono} style={{ color: '#172B4D', fontWeight: 600 }}>{e.type}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{e.id}</div>
                  </td>
                  <td className={styles.td} style={{ maxWidth: 320 }}>{e.res}</td>
                  <td className={styles.td}>
                    <span className={`${styles.badge} ${e.tone === 'g' ? styles.badgeGreen : e.tone === 'a' ? styles.badgeAmber : styles.badgeRed}`}>
                      {e.st}
                    </span>
                  </td>
                  <td className={styles.td} style={{ fontSize: 13, color: 'var(--muted)' }}>{e.time}</td>
                  <td className={styles.td} onClick={(ev) => ev.stopPropagation()}>
                    <Link to="/audit" className={styles.mono}>{e.hash}</Link>
                  </td>
                  <td className={styles.td} onClick={(ev) => ev.stopPropagation()}>
                    <button
                      className={`${styles.btn} ${styles.btnSm}`}
                      onClick={(ev) => handleReplayEvent(ev, e)}
                      disabled={!canManage}
                    >
                      Replay
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Selected Event Drawer / Modal */}
      {selectedEvent && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalCard} style={{ maxWidth: 560 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>{selectedEvent.id}</div>
                <h2 style={{ fontSize: 18, margin: '2px 0 0', fontWeight: 600, wordBreak: 'break-all' }}>
                  {selectedEvent.type}
                </h2>
              </div>
              <button
                className={styles.btn}
                style={{ width: 36, height: 36, padding: 0, fontSize: 20 }}
                onClick={() => setSelectedEvent(null)}
              >
                ×
              </button>
            </div>

            <div style={{ background: '#F0F3F8', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Resource</div>
              <div style={{ marginTop: 2, fontSize: 13 }}>{selectedEvent.res}</div>
            </div>

            <div style={{ background: '#F0F3F8', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>SHA-256 audit link</div>
              <Link to="/audit" className={styles.mono}>{selectedEvent.hash}</Link>
            </div>

            <div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>Payload</div>
              <pre className={styles.mono} style={{ margin: 0, background: '#001C64', color: '#D6E2F5', borderRadius: 8, padding: 12, overflow: 'auto', fontSize: 12, lineHeight: 1.5 }}>
                {JSON.stringify(
                  {
                    id: selectedEvent.id,
                    event_type: selectedEvent.type,
                    create_time: selectedEvent.time,
                    resource: selectedEvent.res,
                    status: selectedEvent.st,
                  },
                  null,
                  2
                )}
              </pre>
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button className={styles.btn} onClick={() => setSelectedEvent(null)}>Close</button>
              <button
                className={`${styles.btn} ${styles.btnPrimary}`}
                onClick={(e) => {
                  handleReplayEvent(e, selectedEvent);
                  setSelectedEvent(null);
                }}
                disabled={!canManage}
              >
                Replay event
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rotate Keys Modal */}
      {rotateOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalCard}>
            <h2 style={{ fontSize: 18, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
              Rotate PayPal API keys?
            </h2>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 14, lineHeight: 1.5 }}>
              A new client secret is generated server-side. The current key stays valid for 15 minutes so in-flight captures and payouts finish. This action is written to the audit trail.
            </p>
            <div style={{ background: '#FEF1D9', color: '#5C3B00', borderRadius: 8, padding: 12, fontSize: 13 }}>
              Secrets never appear in the browser. Only the new key ID is shown here.
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button className={styles.btn} onClick={() => setRotateOpen(false)}>Cancel</button>
              <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={handleRotateKeys}>
                Rotate keys
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

