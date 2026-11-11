import { useState } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './Approvals.module.css';

function fmt(n) { return `$${Number(n || 0).toFixed(2)}`; }

export default function Approvals() {
  const [tab, setTab] = useState('submissions');
  const { data: subApprovals, loading: sLoad, refetch: sRefetch } = useApi(() => endpoints.approvals.submissions.list());
  const { data: caseApprovals, loading: cLoad, refetch: cRefetch } = useApi(() => endpoints.approvals.cases.list());
  const [acting, setActing] = useState('');

  async function decideSubmission(taskId, approved) {
    setActing(taskId);
    try {
      await endpoints.approvals.submissions.decide(taskId, { approved, comment: approved ? 'Approved by admin' : 'Denied by admin' });
      showToast(approved ? '✓ Submission approved, payout released' : '✗ Submission denied', approved ? 'success' : 'warning');
      sRefetch();
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setActing(''); }
  }

  async function decideCase(caseId, approved) {
    setActing(caseId);
    try {
      await endpoints.approvals.cases.decide(caseId, { approved });
      showToast(approved ? 'Case approved ✓' : 'Case denied', approved ? 'success' : 'warning');
      cRefetch();
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setActing(''); }
  }

  const subList  = subApprovals  ?? [];
  const caseList = caseApprovals ?? [];

  return (
    <div className={styles.page}>
      <div>
        <h1 className={styles.h1}>Approvals Queue (HITL)</h1>
        <p className={styles.sub}>Human-in-the-Loop review for oversized payouts and policy escalations.</p>
      </div>

      <div className={styles.tabs}>
        <button className={`${styles.tab} ${tab === 'submissions' ? styles.tabActive : ''}`} onClick={() => setTab('submissions')}>
          Submission Approvals {subList.length > 0 && <span className={styles.badge}>{subList.length}</span>}
        </button>
        <button className={`${styles.tab} ${tab === 'cases' ? styles.tabActive : ''}`} onClick={() => setTab('cases')}>
          Case Approvals {caseList.length > 0 && <span className={styles.badge}>{caseList.length}</span>}
        </button>
      </div>

      {tab === 'submissions' && (
        sLoad ? <PageLoader /> : (
          <Card noPadding>
            <div style={{ overflowX: 'auto' }}>
              <table className={styles.table}>
                <thead><tr><th>Task ID</th><th>Milestone</th><th>Score</th><th>Route</th><th>Created</th><th>Actions</th></tr></thead>
                <tbody>
                  {subList.map(t => (
                    <tr key={t.id ?? t.task_id}>
                      <td className="mono">{t.id ?? t.task_id}</td>
                      <td className="mono">{t.milestone_id ?? '—'}</td>
                      <td><span style={{ fontWeight: 600, color: 'var(--blue)' }}>{t.score ?? '—'}/100</span></td>
                      <td><Badge variant="warning">{t.route ?? 'HUMAN_REVIEW'}</Badge></td>
                      <td className="muted">{t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <Button size="sm" variant="primary" disabled={acting === (t.id ?? t.task_id)} onClick={() => decideSubmission(t.id ?? t.task_id, true)}>Approve</Button>
                          <Button size="sm" variant="danger" disabled={acting === (t.id ?? t.task_id)} onClick={() => decideSubmission(t.id ?? t.task_id, false)}>Deny</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {subList.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>No pending submission approvals.</td></tr>}
                </tbody>
              </table>
            </div>
          </Card>
        )
      )}

      {tab === 'cases' && (
        cLoad ? <PageLoader /> : (
          <Card noPadding>
            <div style={{ overflowX: 'auto' }}>
              <table className={styles.table}>
                <thead><tr><th>Case ID</th><th>Customer</th><th>Amount</th><th>State</th><th>Actions</th></tr></thead>
                <tbody>
                  {caseList.map(c => (
                    <tr key={c.id}>
                      <td className="mono">{c.id}</td>
                      <td>{c.customer_id ?? '—'}</td>
                      <td className="tabular">{fmt(c.amount_usd)}</td>
                      <td><Badge variant={stateBadge(c.state)}>{c.state}</Badge></td>
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <Button size="sm" variant="primary" disabled={acting === c.id} onClick={() => decideCase(c.id, true)}>Approve</Button>
                          <Button size="sm" variant="danger" disabled={acting === c.id} onClick={() => decideCase(c.id, false)}>Deny</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {caseList.length === 0 && <tr><td colSpan={5} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>No pending case approvals.</td></tr>}
                </tbody>
              </table>
            </div>
          </Card>
        )
      )}
    </div>
  );
}
