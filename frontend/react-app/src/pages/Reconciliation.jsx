import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { PageLoader } from '../components/ui/Spinner';
import styles from './Reconciliation.module.css';

function fmt(n) { return `$${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`; }

export default function Reconciliation() {
  const { data: summary, loading } = useApi(() => endpoints.reconciliation.summary());

  if (loading) return <PageLoader />;
  const s = summary ?? {};

  return (
    <div className={styles.page}>
      <div>
        <h1 className={styles.h1}>Reconciliation (3-Way)</h1>
        <p className={styles.sub}>ProofPay Ledger ↔ PayPal Transactions ↔ Bank Statement cross-matching.</p>
      </div>

      {/* How it works */}
      <Card className={styles.howTo}>
        <div className={styles.flowRow}>
          {['ProofPay Ledger', '↔', 'PayPal Transactions', '↔', 'Bank Statement'].map((step, i) => (
            <div key={i} className={i % 2 === 0 ? styles.flowBox : styles.flowArrow}>{step}</div>
          ))}
        </div>
        <p className={styles.howDesc}>
          When a customer pays via bank transfer or other method, ProofPay detects the settlement
          and blocks all further recovery outreach — preventing wrongful contacts and protecting merchant reputation.
        </p>
      </Card>

      {/* KPI cards */}
      <div className={styles.kpiGrid}>
        {[
          { label: 'Total Invoiced', value: fmt(s.total_invoiced ?? s.at_risk_amount), color: 'var(--navy)' },
          { label: 'Amount Recovered', value: fmt(s.recovered_amount), color: 'var(--green)' },
          { label: 'Paid Elsewhere (Blocked)', value: s.paid_elsewhere_count ?? 0, color: 'var(--blue)', unit: ' cases' },
          { label: 'Outbox Size', value: s.outbox_size ?? 0, color: 'var(--muted)', unit: ' pending' },
        ].map(k => (
          <Card key={k.label} className={styles.kpi}>
            <div className={styles.kpiLabel}>{k.label}</div>
            <div className={styles.kpiValue} style={{ color: k.color }}>{k.value}{k.unit}</div>
          </Card>
        ))}
      </div>

      {/* Paid elsewhere table */}
      {Array.isArray(s.paid_elsewhere) && s.paid_elsewhere.length > 0 && (
        <Card noPadding>
          <div className={styles.tableHeader}>Paid-Elsewhere Cases (Outreach Blocked)</div>
          <div style={{ overflowX: 'auto' }}>
            <table className={styles.table}>
              <thead><tr><th>Case ID</th><th>Customer</th><th>Amount</th><th>Detected At</th><th>Status</th></tr></thead>
              <tbody>
                {s.paid_elsewhere.map((c, i) => (
                  <tr key={i}>
                    <td className="mono">{c.case_id ?? c.id}</td>
                    <td>{c.customer_id ?? '—'}</td>
                    <td className="tabular">{fmt(c.amount_usd)}</td>
                    <td className="muted">{c.detected_at ? new Date(c.detected_at).toLocaleString() : '—'}</td>
                    <td><Badge variant="info">BLOCKED</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {(!s.paid_elsewhere || s.paid_elsewhere.length === 0) && (
        <Card>
          <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
            No paid-elsewhere cases detected yet. When a customer pays via another channel, it appears here and outreach is automatically stopped.
          </p>
        </Card>
      )}
    </div>
  );
}
