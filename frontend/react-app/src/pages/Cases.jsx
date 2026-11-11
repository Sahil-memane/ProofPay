import { useState } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Drawer } from '../components/ui/Drawer';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './Cases.module.css';

const FILTERS = ['ALL', 'ACTIVE', 'RECOVERED', 'HALTED', 'PAID_ELSEWHERE'];

const EVENT_ICONS = {
  CASE_OPENED: '📂',
  STAGE_ADVANCED: '⏩',
  RECOVERY_ATTEMPTED: '📧',
  PAYMENT_RECEIVED: '💰',
  CASE_HALTED: '🛑',
  CASE_REOPENED: '🔄',
  PAID_ELSEWHERE: '🏦',
  DEFAULT: '📋',
};

function getEventIcon(type) {
  if (!type) return EVENT_ICONS.DEFAULT;
  for (const [key, icon] of Object.entries(EVENT_ICONS)) {
    if (type.includes(key)) return icon;
  }
  return EVENT_ICONS.DEFAULT;
}

function CaseDrawer({ caseId, onClose, onReopen }) {
  const { data, loading } = useApi(() => endpoints.cases.get(caseId), [caseId]);

  return (
    <Drawer open title={`Case ${caseId}`} onClose={onClose} width={520}>
      {loading && <PageLoader />}
      {data && (
        <div className={styles.drawerContent}>
          <div className={styles.drawerMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>Customer</span>
              <span>{data.customer_email ?? data.customer_id ?? '—'}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>Amount</span>
              <span className={styles.amount}>${(data.amount ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>State</span>
              <Badge variant={stateBadge(data.state)}>{data.state}</Badge>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>Stage</span>
              <span>Stage {data.stage ?? '—'}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>Created</span>
              <span className={styles.muted}>{data.created_at ? new Date(data.created_at).toLocaleString() : '—'}</span>
            </div>
          </div>

          {data.state === 'HALTED' && (
            <div className={styles.drawerActions}>
              <Button variant="primary" onClick={() => onReopen(caseId)}>
                🔄 Reopen Case
              </Button>
            </div>
          )}

          <div className={styles.timelineSection}>
            <h3 className={styles.timelineTitle}>Audit Timeline</h3>
            {(data.audit_events ?? data.timeline ?? []).length === 0 ? (
              <p className={styles.empty}>No timeline events recorded.</p>
            ) : (
              <ol className={styles.timeline}>
                {(data.audit_events ?? data.timeline ?? []).map((ev, i) => (
                  <li key={i} className={styles.timelineItem}>
                    <span className={styles.timelineIcon}>{getEventIcon(ev.event_type)}</span>
                    <div className={styles.timelineBody}>
                      <div className={styles.timelineEvent}>{ev.event_type ?? ev.type ?? 'EVENT'}</div>
                      <div className={styles.timelineDesc}>{ev.description ?? ev.detail ?? ev.payload_summary ?? '—'}</div>
                      <div className={styles.timelineTs}>{ev.ts ? new Date(ev.ts).toLocaleString() : '—'}</div>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}

export default function Cases() {
  const [filter, setFilter] = useState('ALL');
  const [selectedId, setSelectedId] = useState(null);
  const { data, loading, error, refetch } = useApi(() => endpoints.cases.list());

  if (loading) return <PageLoader />;
  if (error) return <div className={styles.error}>Failed to load cases: {error}</div>;

  const cases = data ?? [];
  const filtered = filter === 'ALL' ? cases : cases.filter(c => c.state === filter);

  async function handleReopen(id) {
    try {
      await endpoints.cases.reopen(id);
      showToast(`Case ${id} reopened successfully`, 'success');
      setSelectedId(null);
      refetch();
    } catch (err) {
      showToast(`Failed to reopen case: ${err.message}`, 'error');
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.h1}>Recovery Cases</h1>
        <p className={styles.sub}>AI-driven payment recovery case management.</p>
      </div>

      <div className={styles.filters}>
        {FILTERS.map(f => (
          <button
            key={f}
            className={`${styles.chip} ${filter === f ? styles.chipActive : ''}`}
            onClick={() => setFilter(f)}
          >
            {f}
            <span className={styles.chipCount}>
              {f === 'ALL' ? cases.length : cases.filter(c => c.state === f).length}
            </span>
          </button>
        ))}
      </div>

      <Card noPadding>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>State</th>
                <th>Stage</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.case_id} className={styles.clickableRow} onClick={() => setSelectedId(c.case_id)}>
                  <td className={styles.mono}>{c.case_id}</td>
                  <td>{c.customer_email ?? c.customer_id ?? '—'}</td>
                  <td className={styles.amount}>${(c.amount ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                  <td><Badge variant={stateBadge(c.state)}>{c.state}</Badge></td>
                  <td>{c.stage != null ? `Stage ${c.stage}` : '—'}</td>
                  <td className={styles.muted}>{c.created_at ? new Date(c.created_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className={styles.emptyRow}>No cases match the current filter.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {selectedId && (
        <CaseDrawer
          caseId={selectedId}
          onClose={() => setSelectedId(null)}
          onReopen={handleReopen}
        />
      )}
    </div>
  );
}
