import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './ProjectDetails.module.css';

function fmt(n) {
  return `$${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD`;
}

export default function ProjectDetails() {
  const [params] = useSearchParams();
  const id = params.get('id') ?? '';
  const { data: project, loading, refetch } = useApi(() => id ? endpoints.projects.get(id) : Promise.resolve(null), [id]);
  const [acting, setActing] = useState('');

  async function approve(role) {
    setActing('approve');
    try {
      await endpoints.projects.approve(id, { role });
      showToast(`${role} approval recorded ✓`, 'success');
      refetch();
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setActing(''); }
  }

  async function fund() {
    setActing('fund');
    try {
      const r = await endpoints.projects.fund(id);
      if (r.approval_url) {
        showToast('Redirecting to PayPal…', 'info');
        window.open(r.approval_url, '_blank');
      } else {
        showToast('Fund initiated ✓', 'success');
      }
      refetch();
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setActing(''); }
  }

  async function capture() {
    const token = window.prompt('Paste PayPal order token:');
    if (!token) return;
    setActing('capture');
    try {
      await endpoints.projects.capture(id, { token });
      showToast('Payment captured ✓', 'success');
      refetch();
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setActing(''); }
  }

  if (!id) return <div style={{ padding: 40, color: 'var(--muted)' }}>No project selected. Go to <a href="/projects">Projects →</a></div>;
  if (loading) return <PageLoader />;
  if (!project) return <div style={{ padding: 40, color: 'var(--muted)' }}>Project not found.</div>;

  const p = project;
  const milestones = p.milestones ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <div className={styles.breadcrumb}><a href="/projects">Projects</a> / {p.id}</div>
          <h1 className={styles.h1}>{p.title}</h1>
          <p className={styles.sub}>{p.description}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {!p.client_approved && <Button variant="secondary" onClick={() => approve('client')} disabled={acting==='approve'}>✓ Approve as Client</Button>}
          {!p.freelancer_approved && <Button variant="secondary" onClick={() => approve('freelancer')} disabled={acting==='approve'}>✓ Approve as Freelancer</Button>}
          {p.client_approved && p.freelancer_approved && p.state !== 'FUNDED' && p.state !== 'COMPLETED' && (
            <Button variant="primary" onClick={fund} disabled={acting==='fund'}>💳 Fund via PayPal</Button>
          )}
          {p.state === 'AWAITING_PAYPAL' && (
            <Button variant="secondary" onClick={capture} disabled={acting==='capture'}>📥 Capture Payment</Button>
          )}
        </div>
      </div>

      {/* Meta cards */}
      <div className={styles.metaGrid}>
        <Card>
          <div className={styles.metaLabel}>Status</div>
          <div style={{ marginTop: 6 }}><Badge variant={stateBadge(p.state)}>{p.state}</Badge></div>
        </Card>
        <Card>
          <div className={styles.metaLabel}>Total Amount</div>
          <div className={styles.metaValue}>{fmt(p.total_amount_usd)}</div>
        </Card>
        <Card>
          <div className={styles.metaLabel}>Funded</div>
          <div className={styles.metaValue}>{fmt(p.funded_amount_usd)}</div>
        </Card>
        <Card>
          <div className={styles.metaLabel}>Released</div>
          <div className={styles.metaValue}>{fmt(p.released_amount_usd)}</div>
        </Card>
      </div>

      {/* Plan hash */}
      <Card>
        <div className={styles.sectionTitle}>Dual Cryptographic Approval</div>
        <div className={styles.hashRow}>
          <div>
            <div className={styles.metaLabel}>Plan Hash (SHA-256)</div>
            <div className="mono" style={{ marginTop: 4, wordBreak: 'break-all' }}>{p.plan_hash ?? '(not generated yet)'}</div>
          </div>
          <div className={styles.approvalBadges}>
            <span className={styles.approvalItem}>
              {p.client_approved ? '✅' : '⬜'} Client: {p.client_email}
            </span>
            <span className={styles.approvalItem}>
              {p.freelancer_approved ? '✅' : '⬜'} Freelancer: {p.freelancer_email}
            </span>
          </div>
        </div>
      </Card>

      {/* Milestones */}
      <Card noPadding>
        <div className={styles.tableHeader}>
          <span className={styles.sectionTitle} style={{ padding: 0 }}>Milestones</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className={styles.table}>
            <thead>
              <tr><th>#</th><th>Title</th><th>Amount</th><th>State</th><th>Due Date</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {milestones.map((m, i) => (
                <tr key={m.id ?? i}>
                  <td className="mono">{i + 1}</td>
                  <td><div style={{ fontWeight: 500 }}>{m.title}</div><div className="muted" style={{ fontSize: 12 }}>{m.description}</div></td>
                  <td className="tabular">{fmt(m.amount_usd)}</td>
                  <td><Badge variant={stateBadge(m.state)}>{m.state}</Badge></td>
                  <td className="muted">{m.due_date ?? '—'}</td>
                  <td>
                    <a href={`/submissions?milestone_id=${m.id}&project_id=${p.id}`} className={styles.link}>
                      Submit Work
                    </a>
                  </td>
                </tr>
              ))}
              {milestones.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 24, color: 'var(--muted)' }}>No milestones defined yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

