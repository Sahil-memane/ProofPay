import { useState } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { PageLoader } from '../components/ui/Spinner';
import styles from './Audit.module.css';

function short(hash) {
  if (!hash) return '—';
  return hash.slice(0, 12) + '…';
}

export default function Audit() {
  const { data: events, loading } = useApi(() => endpoints.audit.list({ limit: 100 }));
  const [typeFilter, setTypeFilter] = useState('All');

  const list = events ?? [];
  const types = ['All', ...new Set(list.map(e => e.event_type).filter(Boolean))];
  const filtered = typeFilter === 'All' ? list : list.filter(e => e.event_type === typeFilter);

  // Validate hash chain
  let chainBroken = false;
  for (let i = 1; i < filtered.length; i++) {
    if (filtered[i].prev_hash && filtered[i - 1].hash && filtered[i].prev_hash !== filtered[i - 1].hash) {
      chainBroken = true;
      break;
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Audit Trail (SHA-256)</h1>
          <p className={styles.sub}>Tamper-evident chain of all financial state changes.</p>
        </div>
        <Badge variant={chainBroken ? 'danger' : 'success'}>
          {chainBroken ? '✗ Chain Broken' : '✓ Chain Valid'}
        </Badge>
      </div>

      <div className={styles.filters}>
        <label className={styles.filterLabel}>Event Type:</label>
        <select className={styles.select} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          {types.map(t => <option key={t}>{t}</option>)}
        </select>
        <span className={styles.count}>{filtered.length} events</span>
      </div>

      {loading ? <PageLoader /> : (
        <Card noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table className={styles.table}>
              <thead>
                <tr><th>#</th><th>Event Type</th><th>Subject</th><th>Hash</th><th>Prev Hash</th><th>Timestamp</th></tr>
              </thead>
              <tbody>
                {filtered.map((ev, i) => {
                  const broken = i > 0 && ev.prev_hash && filtered[i - 1].hash && ev.prev_hash !== filtered[i - 1].hash;
                  return (
                    <tr key={i} className={broken ? styles.broken : ''}>
                      <td className="muted">{i + 1}</td>
                      <td><Badge variant="info">{ev.event_type ?? '—'}</Badge></td>
                      <td className="mono">{ev.case_id ?? ev.project_id ?? ev.subject ?? '—'}</td>
                      <td className="mono" title={ev.hash}>{short(ev.hash)}</td>
                      <td className="mono" title={ev.prev_hash}>{short(ev.prev_hash)}</td>
                      <td className="muted">{ev.ts ? new Date(ev.ts).toLocaleString() : '—'}</td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                    No audit events yet. Inject a failure via the Demo Bar.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
