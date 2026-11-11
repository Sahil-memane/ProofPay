import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { PageLoader } from '../components/ui/Spinner';
import styles from './Dashboard.module.css';

function KpiCard({ label, value, unit, sub, color }) {
  return (
    <Card className={styles.kpi}>
      <div className={styles.kpiLabel}>{label}</div>
      <div className={styles.kpiValue} style={{ color }}>
        {unit}{typeof value === 'number' ? value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}
      </div>
      {sub && <div className={styles.kpiSub}>{sub}</div>}
    </Card>
  );
}

export default function Dashboard() {
  const { data: headline, loading: hlLoad } = useApi(() => endpoints.dashboard.headline());
  const { data: audit, loading: auditLoad }  = useApi(() => endpoints.audit.list({ limit: 8 }));
  const { data: recon }                      = useApi(() => endpoints.reconciliation.summary());
  const { data: approvals }                  = useApi(() => endpoints.approvals.submissions.list());

  if (hlLoad) return <PageLoader />;

  const hl = headline ?? {};
  const recoveryRate = hl.case_count
    ? ((hl.recovered_count / hl.case_count) * 100).toFixed(1)
    : '0.0';

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.h1}>Operations Overview</h1>
        <p className={styles.sub}>AI-powered escrow and revenue recovery — real-time metrics.</p>
      </div>

      {/* Attention banner */}
      {approvals && approvals.length > 0 && (
        <div className={styles.banner}>
          ⚠️ <strong>{approvals.length} pending human approvals</strong> in the HITL queue —{' '}
          <a href="/approvals">Review now →</a>
        </div>
      )}

      {/* Reconciliation banner */}
      {recon && recon.paid_elsewhere_count > 0 && (
        <div className={styles.bannerInfo}>
          🔄 <strong>{recon.paid_elsewhere_count} paid-elsewhere cases</strong> blocked from re-contact —{' '}
          <a href="/reconciliation">View reconciliation →</a>
        </div>
      )}

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <KpiCard label="Total Recovered" value={hl.recovered_amount ?? 0} unit="$" color="var(--green)" sub={`${hl.recovered_count ?? 0} cases recovered`} />
        <KpiCard label="At-Risk Amount" value={hl.at_risk_amount ?? 0} unit="$" color="var(--amber)" sub={`${hl.case_count ?? 0} total cases`} />
        <KpiCard label="Recovery Rate" value={`${recoveryRate}%`} color="var(--blue)" sub="Agent vs 8% baseline" />
        <KpiCard label="Total Cases" value={hl.case_count ?? 0} unit="" color="var(--text)" sub={`${hl.recovered_count ?? 0} resolved`} />
      </div>

      {/* Audit stream */}
      <Card noPadding>
        <div className={styles.tableHeader}>
          <span className={styles.tableTitle}>Recent Audit Events</span>
          <a href="/audit" className={styles.tableLink}>View full trail →</a>
        </div>
        {auditLoad ? <PageLoader /> : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Subject</th>
                  <th>SHA-256 Hash</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {(audit ?? []).map((ev, i) => (
                  <tr key={i}>
                    <td><Badge variant={stateBadge(ev.event_type)}>{ev.event_type}</Badge></td>
                    <td className="mono">{ev.case_id ?? ev.project_id ?? '—'}</td>
                    <td className="mono" style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {ev.hash ?? '—'}
                    </td>
                    <td className="muted">{ev.ts ? new Date(ev.ts).toLocaleString() : '—'}</td>
                  </tr>
                ))}
                {(!audit || audit.length === 0) && (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--muted)', padding: 24 }}>No audit events yet. Inject a failure to begin.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className={styles.footer}>AI recommends. Policy decides. PayPal executes. Every action is auditable.</div>
    </div>
  );
}

