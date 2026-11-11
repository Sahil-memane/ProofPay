import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { PageLoader } from '../components/ui/Spinner';
import styles from './Ledger.module.css';

function fmt(n) { return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function Ledger() {
  const { data: projects, loading: pLoad } = useApi(() => endpoints.projects.list());
  const { data: audit,    loading: aLoad } = useApi(() => endpoints.audit.list({ limit: 100 }));

  if (pLoad || aLoad) return <PageLoader />;

  // Build ledger entries from projects
  const entries = [];

  (projects ?? []).forEach(p => {
    if (p.funded_amount_usd > 0) {
      entries.push({ date: p.created_at, type: 'ESCROW_FUNDED', desc: `${p.title}`, ref: p.id, cr: p.funded_amount_usd, dr: 0 });
    }
    (p.milestones ?? []).forEach(m => {
      if (m.state === 'RELEASED') {
        entries.push({ date: m.updated_at ?? p.created_at, type: 'MILESTONE_RELEASED', desc: `${m.title} (${p.id})`, ref: m.id, cr: 0, dr: m.amount_usd });
      }
    });
  });

  // Also pull RELEASED events from audit trail
  (audit ?? []).filter(e => e.event_type === 'PAYMENT.PAYOUTS-ITEM.SUCCEEDED').forEach(ev => {
    entries.push({ date: ev.ts, type: 'PAYOUT', desc: ev.case_id ?? ev.project_id ?? 'Payout', ref: ev.case_id, cr: 0, dr: ev.amount ?? 0 });
  });

  entries.sort((a, b) => (a.date ?? '') > (b.date ?? '') ? 1 : -1);

  const totalEscrowed  = entries.filter(e => e.cr > 0).reduce((s, e) => s + e.cr, 0);
  const totalReleased  = entries.filter(e => e.dr > 0).reduce((s, e) => s + e.dr, 0);
  const netBalance     = totalEscrowed - totalReleased;

  return (
    <div className={styles.page}>
      <div>
        <h1 className={styles.h1}>Escrow Ledger</h1>
        <p className={styles.sub}>Complete transaction history of escrow funds, releases, and payouts.</p>
      </div>

      <div className={styles.summaryGrid}>
        {[
          { label: 'Total Escrowed', value: `$${fmt(totalEscrowed)}`, color: 'var(--blue)' },
          { label: 'Total Released', value: `$${fmt(totalReleased)}`, color: 'var(--red)' },
          { label: 'Net Balance (Held)', value: `$${fmt(netBalance)}`, color: 'var(--green)' },
        ].map(s => (
          <Card key={s.label} className={styles.summaryCard}>
            <div className={styles.summaryLabel}>{s.label}</div>
            <div className={styles.summaryValue} style={{ color: s.color }}>{s.value}</div>
          </Card>
        ))}
      </div>

      <Card noPadding>
        <div style={{ overflowX: 'auto' }}>
          <table className={styles.table}>
            <thead>
              <tr><th>Date</th><th>Type</th><th>Description</th><th>Ref</th><th>Credit (IN)</th><th>Debit (OUT)</th></tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{e.date ? new Date(e.date).toLocaleDateString() : '—'}</td>
                  <td><span className={`${styles.typeBadge} ${e.cr > 0 ? styles.credit : styles.debit}`}>{e.type}</span></td>
                  <td>{e.desc}</td>
                  <td className="mono">{e.ref ?? '—'}</td>
                  <td className={e.cr > 0 ? styles.crAmt : styles.zero}>{e.cr > 0 ? `+$${fmt(e.cr)}` : '—'}</td>
                  <td className={e.dr > 0 ? styles.drAmt : styles.zero}>{e.dr > 0 ? `-$${fmt(e.dr)}` : '—'}</td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                  No ledger entries yet. Fund a project to begin.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

