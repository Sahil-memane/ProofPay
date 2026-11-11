import { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { toast } from '../components/ui/Toast';
import styles from './PaymentAttempts.module.css';

const INITIAL_ATTEMPTS = [
  { id: 'ATT-2026-5516', ts: '2026-11-11 09:14', k: 'REC-2026-0042', e: 'sarah@example.com', n: 1, err: 'INSTRUMENT_DECLINED', rt: '+48 hours · Fri 09:14 UTC', r: 'FAILED' },
  { id: 'ATT-2026-5515', ts: '2026-11-11 02:40', k: 'REC-2026-0038', e: 'lena@example.com', n: 2, err: 'INSTRUMENT_DECLINED', rt: 'Held until 08:00 local (quiet hours)', r: 'SKIPPED_QUIET_HOURS' },
  { id: 'ATT-2026-5514', ts: '2026-11-10 18:30', k: 'REC-2026-0043', e: 'dev@example.com', n: 1, err: 'INSUFFICIENT_FUNDS', rt: '+48 hours · Thu 18:30 UTC', r: 'FAILED' },
  { id: 'ATT-2026-5513', ts: '2026-11-10 13:05', k: 'REC-2026-0040', e: 'priya@example.com', n: 2, err: '', rt: 'Not needed', r: 'SUCCEEDED' },
  { id: 'ATT-2026-5512', ts: '2026-11-09 21:42', k: 'REC-2026-0039', e: 'tom@example.com', n: 2, err: '', rt: 'Not needed', r: 'SUCCEEDED' },
  { id: 'ATT-2026-5511', ts: '2026-11-09 11:05', k: 'REC-2026-0041', e: 'michael@example.com', n: 1, err: 'INSUFFICIENT_FUNDS', rt: 'Cancelled: paid elsewhere (wire match)', r: 'FAILED' },
  { id: 'ATT-2026-5510', ts: '2026-11-07 08:10', k: 'REC-2026-0042', e: 'sarah@example.com', n: 0, err: 'INSTRUMENT_DECLINED', rt: 'Original charge, case opened', r: 'FAILED' },
  { id: 'ATT-2026-5509', ts: '2026-11-06 16:22', k: 'REC-2026-0040', e: 'priya@example.com', n: 1, err: 'PAYER_ACTION_REQUIRED', rt: 'Update link sent, retried +24 hours', r: 'FAILED' },
  { id: 'ATT-2026-5508', ts: '2026-11-05 10:48', k: 'REC-2026-0039', e: 'tom@example.com', n: 1, err: 'TRANSACTION_REFUSED', rt: 'Retried +48 hours', r: 'FAILED' },
];

const INITIAL_WEBHOOKS = [
  { id: 'WHK-88213', ts: '2026-11-11 09:14', t: 'PAYMENT.CAPTURE.DENIED', k: 'REC-2026-0042', h: 200, d: 1, s: 'DELIVERED' },
  { id: 'WHK-88209', ts: '2026-11-10 13:05', t: 'PAYMENT.CAPTURE.COMPLETED', k: 'REC-2026-0040', h: 200, d: 1, s: 'DELIVERED' },
  { id: 'WHK-88204', ts: '2026-11-10 08:31', t: 'BILLING.SUBSCRIPTION.PAYMENT.FAILED', k: 'REC-2026-0043', h: 503, d: 3, s: 'RETRYING' },
  { id: 'WHK-88197', ts: '2026-11-09 21:42', t: 'PAYMENT.CAPTURE.COMPLETED', k: 'REC-2026-0039', h: 200, d: 1, s: 'DELIVERED' },
  { id: 'WHK-88190', ts: '2026-11-09 11:05', t: 'PAYMENT.CAPTURE.DENIED', k: 'REC-2026-0041', h: 500, d: 5, s: 'FAILED' },
];

const ERROR_MESSAGES = {
  INSTRUMENT_DECLINED: "The cardholder's bank rejected the transaction.",
  INSUFFICIENT_FUNDS: 'The payer account has insufficient funds for this amount.',
  PAYER_ACTION_REQUIRED: 'The payer must authorize this payment before it can be captured.',
  TRANSACTION_REFUSED: 'PayPal refused the transaction. Try another payment method.',
};

export default function PaymentAttempts() {
  const navigate = useNavigate();
  const { data: apiAttempts } = useApi(() => endpoints.paymentAttempts.list());
  const [activeTab, setActiveTab] = useState('gw');
  const [attempts, setAttempts] = useState(INITIAL_ATTEMPTS);
  const [webhooks, setWebhooks] = useState(INITIAL_WEBHOOKS);

  useEffect(() => {
    if (apiAttempts && Array.isArray(apiAttempts) && apiAttempts.length > 0) {
      setAttempts(apiAttempts.map((sub, i) => ({
        id: `ATT-2026-${sub.sub_id.slice(0, 4)}`,
        ts: sub.failed_at ? sub.failed_at.replace('T', ' ').slice(0, 16) : '2026-11-11 09:14',
        k: `REC-${sub.customer_id}`,
        e: `${sub.customer_id.toLowerCase()}@client.example`,
        n: sub.retry_count || 1,
        err: (sub.failure_code || 'INSTRUMENT_DECLINED').toUpperCase().replace(/ /g, '_'),
        rt: sub.retry_count > 2 ? 'Executive escalation' : '+48 hours · Scheduled',
        r: i % 4 === 3 ? 'SUCCEEDED' : 'FAILED',
      })));
    }
  }, [apiAttempts]);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [resultFilter, setResultFilter] = useState('');
  const [errorCodeFilter, setErrorCodeFilter] = useState('');

  // Drawer
  const [activeDrawer, setActiveDrawer] = useState(null);
  const [drawerHash, setDrawerHash] = useState('');
  const [replayingWebhookId, setReplayingWebhookId] = useState(null);

  // KPIs
  const retries = attempts.filter(a => a.n > 0);
  const succeededCount = attempts.filter(a => a.r === 'SUCCEEDED').length;
  const retrySuccessRate = retries.length ? Math.round((succeededCount / retries.length) * 100) : 0;
  const quietHoursHeld = attempts.filter(a => a.r === 'SKIPPED_QUIET_HOURS').length;
  const webhooksNeedingAttention = webhooks.filter(w => w.s !== 'DELIVERED').length;

  const filteredAttempts = useMemo(() => {
    return attempts.filter(a => {
      const matchResult = !resultFilter || a.r === resultFilter;
      const matchError = !errorCodeFilter || a.err === errorCodeFilter;
      const q = searchQuery.toLowerCase();
      const matchQuery = !q || (a.id + a.k + a.e).toLowerCase().includes(q);
      return matchResult && matchError && matchQuery;
    });
  }, [attempts, resultFilter, errorCodeFilter, searchQuery]);

  const handleOpenDrawer = async (attempt) => {
    setActiveDrawer(attempt);
    const rawData = {
      attempt_id: attempt.id,
      case_id: attempt.k,
      payer_email: attempt.e,
      status: attempt.r,
      error: attempt.err || null,
      message: attempt.err ? ERROR_MESSAGES[attempt.err] : 'Payment captured.',
      created: attempt.ts.replace(' ', 'T') + ':00Z',
    };
    try {
      const hashBuffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(rawData)));
      const hashHex = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
      setDrawerHash(hashHex);
    } catch {
      setDrawerHash('Hash unavailable in this browser context');
    }
  };

  const handleSimulateFailure = () => {
    const errorCodes = ['INSUFFICIENT_FUNDS', 'INSTRUMENT_DECLINED', 'TRANSACTION_REFUSED', 'PAYER_ACTION_REQUIRED'];
    const chosen = errorCodes[Math.floor(Math.random() * errorCodes.length)];
    const nextNum = 17 + attempts.length - 9;
    const nowStr = new Date().toISOString().slice(0, 16).replace('T', ' ');
    const newAttempt = {
      id: `ATT-2026-55${nextNum}`,
      ts: nowStr,
      k: 'REC-2026-0044',
      e: 'ravi@example.com',
      n: 1,
      err: chosen,
      rt: '+48 hours · weekends skipped',
      r: 'FAILED',
    };
    setAttempts([newAttempt, ...attempts]);
    toast.warning(`Gateway failure logged: ${chosen}. Smart retry scheduled.`);
  };

  const handleExportCSV = () => {
    const rows = [
      ['attempt_id', 'timestamp_utc', 'case', 'email', 'attempt', 'error_code', 'result'],
      ...attempts.map(a => [a.id, a.ts, a.k, a.e, a.n ? `Attempt ${a.n} of 3` : 'Original charge', a.err, a.r]),
    ];
    const csvContent = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'gateway-logs.csv';
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Gateway logs exported to gateway-logs.csv.');
  };

  const handleReplayWebhook = (idx) => {
    const target = webhooks[idx];
    setReplayingWebhookId(target.id);
    setTimeout(() => {
      setWebhooks(prev => prev.map((w, i) => i === idx ? { ...w, s: 'DELIVERED', h: 200, d: w.d + 1 } : w));
      setReplayingWebhookId(null);
      toast.success(`Webhook ${target.id} replayed and delivered.`);
    }, 900);
  };

  const getResultBadge = (r) => {
    switch (r) {
      case 'SUCCEEDED':
      case 'DELIVERED':
        return styles.badgeGreen;
      case 'SKIPPED_QUIET_HOURS':
      case 'RETRYING':
        return styles.badgeAmber;
      case 'FAILED':
        return styles.badgeRed;
      default:
        return styles.badgeGray;
    }
  };

  return (
    <div className={styles.container}>
      {/* Top Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>Payment Attempts &amp; Gateway Logs</h1>
          <p>Every charge attempt and webhook delivery, matched to its recovery case, with the next smart retry.</p>
        </div>
        <div className={styles.actionsGroup}>
          <button className={styles.btn} onClick={handleExportCSV}>Export CSV</button>
          <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={handleSimulateFailure}>
            Simulate gateway failure
          </button>
        </div>
      </div>

      {/* 4 KPIs */}
      <section className={styles.kpiCard} aria-label="Attempt summary">
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Attempts logged</span>
          <div className={styles.kpiValue}>{attempts.length}</div>
          <span className={styles.kpiLabel}>Last 7 days</span>
        </div>
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Retry success rate</span>
          <div className={styles.kpiValue}>{retrySuccessRate}%</div>
          <span className={styles.kpiLabel}>{succeededCount} of {retries.length} retries recovered</span>
        </div>
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Held for quiet hours</span>
          <div className={styles.kpiValue}>{quietHoursHeld}</div>
          <span className={styles.kpiLabel}>Resume at 08:00 local</span>
        </div>
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Webhooks needing attention</span>
          <div className={styles.kpiValue}>{webhooksNeedingAttention}</div>
          <span className={styles.kpiLabel}>Retrying or failed</span>
        </div>
      </section>

      {/* Smart Retry Rules Callout */}
      <div className={styles.bannerCard}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--blue)', marginTop: 2, flexShrink: 0 }}>
          <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 8h.01M11 12h1v5h1" />
        </svg>
        <div>
          <b>Smart retry rules.</b> Retries wait 48 hours, skip weekends, and never run between 21:00 and 08:00 in the customer&apos;s local time. A case paid elsewhere cancels every pending retry.
        </div>
      </div>

      {/* Log Tabs */}
      <section className={styles.card}>
        <div className={styles.tabList} role="tablist">
          <button
            className={`${styles.tab} ${activeTab === 'gw' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('gw')}
          >
            Gateway Logs <span className={styles.tabCounter}>{attempts.length}</span>
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'wh' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('wh')}
          >
            Webhook Outbox <span className={styles.tabCounter}>{webhooks.length}</span>
          </button>
        </div>

        {/* Gateway Logs Tab */}
        {activeTab === 'gw' && (
          <div className={styles.tabPanel}>
            <div className={styles.filterBar}>
              <input
                className={styles.input}
                style={{ flex: '1 1 240px', maxWidth: 340 }}
                placeholder="Filter by attempt, case, or email"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <select
                className={styles.input}
                style={{ minWidth: 190 }}
                value={resultFilter}
                onChange={(e) => setResultFilter(e.target.value)}
              >
                <option value="">All results</option>
                <option value="FAILED">FAILED</option>
                <option value="SUCCEEDED">SUCCEEDED</option>
                <option value="SKIPPED_QUIET_HOURS">SKIPPED_QUIET_HOURS</option>
              </select>
              <select
                className={styles.input}
                style={{ minWidth: 210 }}
                value={errorCodeFilter}
                onChange={(e) => setErrorCodeFilter(e.target.value)}
              >
                <option value="">All error codes</option>
                <option value="INSTRUMENT_DECLINED">INSTRUMENT_DECLINED</option>
                <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS</option>
                <option value="PAYER_ACTION_REQUIRED">PAYER_ACTION_REQUIRED</option>
                <option value="TRANSACTION_REFUSED">TRANSACTION_REFUSED</option>
              </select>
            </div>

            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Attempt ID</th>
                    <th className={styles.th}>Timestamp (UTC)</th>
                    <th className={styles.th}>Case</th>
                    <th className={styles.th}>Customer email</th>
                    <th className={styles.th}>Attempt</th>
                    <th className={styles.th}>Error code</th>
                    <th className={styles.th}>Gateway message</th>
                    <th className={styles.th}>Smart retry</th>
                    <th className={styles.th}>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAttempts.map(a => (
                    <tr
                      key={a.id}
                      className={styles.tr}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleOpenDrawer(a)}
                    >
                      <td className={styles.td}><code className={styles.mono}>{a.id}</code></td>
                      <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}>{a.ts}</td>
                      <td className={styles.td} onClick={(e) => e.stopPropagation()}>
                        <Link to="/cases" style={{ color: 'var(--blue)' }}>{a.k}</Link>
                      </td>
                      <td className={styles.td}>{a.e}</td>
                      <td className={styles.td}>{a.n ? `Attempt ${a.n} of 3` : 'Original charge'}</td>
                      <td className={styles.td}>
                        {a.err ? <code className={styles.mono}>{a.err}</code> : <span className={styles.kpiLabel}>None</span>}
                      </td>
                      <td className={styles.td} style={{ maxWidth: 260 }}>
                        {a.err ? ERROR_MESSAGES[a.err] : 'Payment captured.'}
                      </td>
                      <td className={styles.td}>{a.rt}</td>
                      <td className={styles.td}>
                        <span className={`${styles.badge} ${getResultBadge(a.r)}`}>{a.r}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Webhook Outbox Tab */}
        {activeTab === 'wh' && (
          <div className={styles.tabPanel}>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Event ID</th>
                    <th className={styles.th}>Timestamp (UTC)</th>
                    <th className={styles.th}>Event type</th>
                    <th className={styles.th}>Case</th>
                    <th className={styles.th}>HTTP</th>
                    <th className={styles.th}>Deliveries</th>
                    <th className={styles.th}>Status</th>
                    <th className={styles.th} />
                  </tr>
                </thead>
                <tbody>
                  {webhooks.map((w, idx) => (
                    <tr key={w.id} className={styles.tr}>
                      <td className={styles.td}><code className={styles.mono}>{w.id}</code></td>
                      <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}>{w.ts}</td>
                      <td className={styles.td}><code className={styles.mono}>{w.t}</code></td>
                      <td className={styles.td}>
                        <Link to="/cases" style={{ color: 'var(--blue)' }}>{w.k}</Link>
                      </td>
                      <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}>{w.h}</td>
                      <td className={styles.td} style={{ fontVariantNumeric: 'tabular-nums' }}>{w.d}</td>
                      <td className={styles.td}>
                        <span className={`${styles.badge} ${getResultBadge(w.s)}`}>{w.s}</span>
                      </td>
                      <td className={styles.td} style={{ textAlign: 'right' }}>
                        {w.s !== 'DELIVERED' && (
                          <button
                            className={`${styles.btn} ${styles.btnSm}`}
                            onClick={() => handleReplayWebhook(idx)}
                            disabled={replayingWebhookId === w.id}
                          >
                            {replayingWebhookId === w.id ? 'Replaying…' : 'Replay'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* Attempt Detail Drawer */}
      {activeDrawer && (
        <>
          <div className={styles.drawerOverlay} onClick={() => setActiveDrawer(null)} />
          <aside className={styles.drawer} role="dialog" aria-modal="true">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: 20, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
                {activeDrawer.id}
              </h2>
              <button
                className={styles.btn}
                style={{ width: 36, height: 36, padding: 0, fontSize: 20 }}
                onClick={() => setActiveDrawer(null)}
              >
                ×
              </button>
            </div>
            <div style={{ margin: '8px 0 4px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`${styles.badge} ${getResultBadge(activeDrawer.r)}`}>{activeDrawer.r}</span>
              <span className={styles.kpiLabel}>
                {activeDrawer.n ? `Attempt ${activeDrawer.n} of 3` : 'Original charge'} · <Link to="/cases" style={{ color: 'var(--blue)' }}>{activeDrawer.k}</Link>
              </span>
            </div>

            <div className={styles.kpiLabel} style={{ marginTop: 20 }}>Attempt history for this case</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
              {attempts.filter(x => x.k === activeDrawer.k).map(hist => (
                <div
                  key={hist.id}
                  className={styles.drawerRow}
                  style={{
                    background: hist.id === activeDrawer.id ? '#E6F0FC' : 'transparent',
                    borderRadius: 8,
                  }}
                >
                  <span className={styles.kpiLabel} style={{ width: 120 }}>{hist.ts}</span>
                  <div style={{ flex: 1 }}>
                    <code className={styles.mono}>{hist.id}</code>
                    <div className={styles.kpiLabel}>{hist.err || 'Succeeded'}</div>
                  </div>
                  <span className={`${styles.badge} ${getResultBadge(hist.r)}`}>{hist.r}</span>
                </div>
              ))}
            </div>

            <div className={styles.kpiLabel} style={{ marginTop: 20 }}>Next step</div>
            <div style={{ padding: '12px 16px', borderRadius: 8, background: '#F0F3F8', marginTop: 4, fontSize: 13 }}>
              {activeDrawer.rt}
            </div>

            <div className={styles.kpiLabel} style={{ marginTop: 20 }}>Gateway response</div>
            <pre
              className={styles.mono}
              style={{
                margin: '4px 0 0',
                padding: 12,
                background: '#F0F3F8',
                borderRadius: 8,
                overflowX: 'auto',
                whiteSpace: 'pre-wrap',
                fontSize: 12,
                lineHeight: 1.4,
              }}
            >
              {JSON.stringify(
                {
                  attempt_id: activeDrawer.id,
                  case_id: activeDrawer.k,
                  payer_email: activeDrawer.e,
                  status: activeDrawer.r,
                  error: activeDrawer.err || null,
                  message: activeDrawer.err ? ERROR_MESSAGES[activeDrawer.err] : 'Payment captured.',
                  created: activeDrawer.ts.replace(' ', 'T') + ':00Z',
                },
                null,
                2
              )}
            </pre>

            <div className={styles.kpiLabel} style={{ marginTop: 20 }}>
              Audit proof (SHA-256 of this response)
            </div>
            <code
              className={styles.mono}
              style={{
                display: 'block',
                wordBreak: 'break-all',
                padding: 12,
                background: '#F0F3F8',
                borderRadius: 8,
                marginTop: 4,
                lineHeight: 1.4,
              }}
            >
              {drawerHash}
            </code>

            <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
              <button className={styles.btn} onClick={() => navigate('/audit')}>
                Open in audit trail
              </button>
            </div>
          </aside>
        </>
      )}

      <footer className={styles.footerTagline}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </footer>
    </div>
  );
}

