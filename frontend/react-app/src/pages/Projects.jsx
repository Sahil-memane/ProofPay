import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './Projects.module.css';

const FILTERS = ['All', 'DRAFT', 'AWAITING_PAYPAL', 'FUNDED', 'COMPLETED', 'DISPUTED'];

function fmt(n) {
  return `$${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
}

function hashStatus(p) {
  if (p.client_approved && p.freelancer_approved) return { label: 'Both Approved', v: 'success' };
  if (p.client_approved) return { label: 'Awaiting Freelancer', v: 'warning' };
  if (p.freelancer_approved) return { label: 'Awaiting Client', v: 'warning' };
  if (!p.plan_hash) return { label: 'Not Generated', v: 'neutral' };
  return { label: 'Pending Signatures', v: 'warning' };
}

export default function Projects() {
  const navigate = useNavigate();
  const { data: projects, loading, refetch } = useApi(() => endpoints.projects.list());
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', client_email: '', freelancer_email: '', total_amount_usd: '' });

  const list = (projects ?? []).filter(p => {
    const matchFilter = filter === 'All' || p.state === filter;
    const matchSearch = !search || p.title?.toLowerCase().includes(search.toLowerCase()) || p.id?.includes(search);
    return matchFilter && matchSearch;
  });

  const counts = {};
  FILTERS.forEach(f => {
    counts[f] = f === 'All' ? (projects ?? []).length : (projects ?? []).filter(p => p.state === f).length;
  });

  async function createProject(e) {
    e.preventDefault();
    setCreating(true);
    try {
      const proj = await endpoints.projects.create({
        ...form,
        total_amount_usd: parseFloat(form.total_amount_usd),
      });
      showToast(`Project ${proj.id} created ✓`, 'success');
      setShowCreate(false);
      setForm({ title: '', description: '', client_email: '', freelancer_email: '', total_amount_usd: '' });
      refetch();
    } catch (err) {
      showToast(err.message, 'danger');
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Projects & Contracts</h1>
          <p className={styles.sub}>Manage freelance agreements, milestones, and PayPal escrow.</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="secondary">Export CSV</Button>
          <Button variant="primary" onClick={() => setShowCreate(true)}>+ Create Project</Button>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        {FILTERS.map(f => (
          <button key={f} className={`${styles.chip} ${filter === f ? styles.chipActive : ''}`} onClick={() => setFilter(f)}>
            {f} ({counts[f] ?? 0})
          </button>
        ))}
        <input
          className={styles.searchBox}
          placeholder="Search projects..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Create form */}
      {showCreate && (
        <Card>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600 }}>Create New Project</h3>
          <form onSubmit={createProject} className={styles.form}>
            <div className={styles.formGrid}>
              <div className={styles.field}>
                <label>Project Title *</label>
                <input required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="E.g. E-commerce Website" />
              </div>
              <div className={styles.field}>
                <label>Total Amount (USD) *</label>
                <input required type="number" min="1" step="0.01" value={form.total_amount_usd} onChange={e => setForm(f => ({ ...f, total_amount_usd: e.target.value }))} placeholder="2400.00" />
              </div>
              <div className={styles.field}>
                <label>Client Email *</label>
                <input required type="email" value={form.client_email} onChange={e => setForm(f => ({ ...f, client_email: e.target.value }))} placeholder="client@example.com" />
              </div>
              <div className={styles.field}>
                <label>Freelancer Email *</label>
                <input required type="email" value={form.freelancer_email} onChange={e => setForm(f => ({ ...f, freelancer_email: e.target.value }))} placeholder="freelancer@example.com" />
              </div>
              <div className={styles.field} style={{ gridColumn: '1/-1' }}>
                <label>Description</label>
                <textarea rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Deliverables and scope..." />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
              <Button variant="secondary" onClick={() => setShowCreate(false)} type="button">Cancel</Button>
              <Button variant="primary" type="submit" disabled={creating}>{creating ? 'Creating…' : 'Create Project'}</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Table */}
      {loading ? <PageLoader /> : (
        <Card noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Project ID</th><th>Project</th><th>Client</th><th>Freelancer</th>
                  <th>Total</th><th>Funded</th><th>Released</th><th>Plan Hash</th><th>Status</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {list.map(p => {
                  const hs = hashStatus(p);
                  return (
                    <tr key={p.id}>
                      <td><span className="mono">{p.id}</span></td>
                      <td style={{ minWidth: 220 }}>
                        <div style={{ fontWeight: 500 }}>{p.title}</div>
                        <div className="muted" style={{ fontSize: 12 }}>{p.description}</div>
                      </td>
                      <td>{p.client_email}</td>
                      <td>{p.freelancer_email}</td>
                      <td className="tabular">{fmt(p.total_amount_usd)}</td>
                      <td className="tabular">{fmt(p.funded_amount_usd)}</td>
                      <td className="tabular">{fmt(p.released_amount_usd)}</td>
                      <td><Badge variant={hs.v}>{hs.label}</Badge></td>
                      <td><Badge variant={stateBadge(p.state)}>{p.state ?? '—'}</Badge></td>
                      <td>
                        <button className={styles.link} onClick={() => navigate(`/project-details?id=${p.id}`)}>
                          View Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {list.length === 0 && (
                  <tr><td colSpan={10} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                    {loading ? 'Loading…' : 'No projects. Create your first project above.'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className={styles.tableFooter}>
            <span>Showing {list.length} of {(projects ?? []).length} projects</span>
            <span>Plan hashes verified before funding unlocks</span>
          </div>
        </Card>
      )}
    </div>
  );
}

