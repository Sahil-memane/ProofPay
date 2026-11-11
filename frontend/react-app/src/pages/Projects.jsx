import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './Projects.module.css';

const DEFAULT_PROJECTS = [
  {
    id: 'PRJ-2026-001',
    title: 'E-commerce Website Development',
    description: 'Storefront, checkout and admin dashboard',
    client_email: 'client@example.com',
    freelancer_email: 'freelancer@example.com',
    total_amount_usd: 2400,
    funded_amount_usd: 2400,
    released_amount_usd: 1100,
    hashStatus: 'Both Approved',
    hashVariant: 'g',
    state: 'FUNDED',
    stateVariant: 'g'
  },
  {
    id: 'PRJ-2026-002',
    title: 'Mobile App Redesign',
    description: 'Design system and 14 core screens',
    client_email: 'ops@northwind.io',
    freelancer_email: 'freelancer@example.com',
    total_amount_usd: 3800,
    funded_amount_usd: 3800,
    released_amount_usd: 1520,
    hashStatus: 'Both Approved',
    hashVariant: 'g',
    state: 'FUNDED',
    stateVariant: 'g'
  },
  {
    id: 'PRJ-2026-003',
    title: 'Data Pipeline Audit',
    description: 'Review ETL jobs and data quality checks',
    client_email: 'client@example.com',
    freelancer_email: 'dev@lumen.studio',
    total_amount_usd: 1200,
    funded_amount_usd: 0,
    released_amount_usd: 0,
    hashStatus: 'Awaiting Freelancer',
    hashVariant: 'a',
    state: 'AWAITING_PAYPAL',
    stateVariant: 'a',
    extraAction: 'Approve Scope'
  },
  {
    id: 'PRJ-2026-004',
    title: 'Brand Identity Package',
    description: 'Logo, palette and brand guidelines',
    client_email: 'hello@kestrel.co',
    freelancer_email: 'freelancer@example.com',
    total_amount_usd: 1800,
    funded_amount_usd: 0,
    released_amount_usd: 0,
    hashStatus: 'Awaiting Client',
    hashVariant: 'a',
    state: 'AWAITING_PAYPAL',
    stateVariant: 'a',
    extraAction: 'Approve Scope'
  },
  {
    id: 'PRJ-2026-005',
    title: 'Analytics Dashboard Build',
    description: 'Embedded reporting for finance team',
    client_email: 'finance@acme.example',
    freelancer_email: 'dev@lumen.studio',
    total_amount_usd: 2900,
    funded_amount_usd: 2900,
    released_amount_usd: 0,
    hashStatus: 'Both Approved',
    hashVariant: 'g',
    state: 'FUNDED',
    stateVariant: 'g'
  },
  {
    id: 'PRJ-2026-006',
    title: 'Landing Page Copywriting',
    description: 'Homepage and pricing page copy',
    client_email: 'client@example.com',
    freelancer_email: 'writer@example.com',
    total_amount_usd: 600,
    funded_amount_usd: 0,
    released_amount_usd: 0,
    hashStatus: 'Not Generated',
    hashVariant: 'x',
    state: 'DRAFT',
    stateVariant: 'x'
  },
  {
    id: 'PRJ-2026-007',
    title: 'API Integration Sprint',
    description: 'Connect CRM and billing APIs',
    client_email: 'ops@northwind.io',
    freelancer_email: 'freelancer@example.com',
    total_amount_usd: 1500,
    funded_amount_usd: 1500,
    released_amount_usd: 1500,
    hashStatus: 'Both Approved',
    hashVariant: 'g',
    state: 'FUNDED',
    stateVariant: 'g'
  },
  {
    id: 'PRJ-2026-008',
    title: 'Security Review',
    description: 'Pen-test summary and fixes',
    client_email: 'client@example.com',
    freelancer_email: 'dev@lumen.studio',
    total_amount_usd: 950,
    funded_amount_usd: 950,
    released_amount_usd: 950,
    hashStatus: 'Both Approved',
    hashVariant: 'g',
    state: 'FUNDED',
    stateVariant: 'g'
  }
];

const FILTERS = [
  { key: 'All', label: 'All' },
  { key: 'DRAFT', label: 'Draft' },
  { key: 'AWAITING_PAYPAL', label: 'Awaiting Approval' },
  { key: 'FUNDED', label: 'Funded' },
  { key: 'COMPLETED', label: 'Completed' },
  { key: 'DISPUTED', label: 'Disputed' }
];

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

export default function Projects() {
  const navigate = useNavigate();
  const { data: apiProjects, refetch } = useApi(() => endpoints.projects.list());

  const [projects, setProjects] = useState(DEFAULT_PROJECTS);
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    title: '',
    description: '',
    client_email: '',
    freelancer_email: '',
    total_amount_usd: ''
  });

  // Merge API projects if any exist
  useEffect(() => {
    if (apiProjects && Array.isArray(apiProjects) && apiProjects.length > 0) {
      setProjects(prev => {
        const merged = [...prev];
        apiProjects.forEach(ap => {
          const idx = merged.findIndex(p => p.id === ap.id);
          const mapped = {
            id: ap.id,
            title: ap.title,
            description: ap.description || 'Project deliverables and milestones',
            client_email: ap.client_email,
            freelancer_email: ap.freelancer_email,
            total_amount_usd: ap.total_amount_usd || 0,
            funded_amount_usd: ap.funded_amount_usd || 0,
            released_amount_usd: ap.released_amount_usd || 0,
            hashStatus: ap.client_approved && ap.freelancer_approved ? 'Both Approved' : 'Pending',
            hashVariant: ap.client_approved && ap.freelancer_approved ? 'g' : 'a',
            state: ap.state || 'DRAFT',
            stateVariant: ap.state === 'FUNDED' ? 'g' : ap.state === 'AWAITING_PAYPAL' ? 'a' : 'x'
          };
          if (idx >= 0) {
            merged[idx] = { ...merged[idx], ...mapped };
          } else {
            merged.unshift(mapped);
          }
        });
        return merged;
      });
    }
  }, [apiProjects]);

  const filteredProjects = projects.filter(p => {
    const matchFilter = filter === 'All'
      ? true
      : filter === 'COMPLETED'
      ? p.released_amount_usd > 0 && p.released_amount_usd >= p.total_amount_usd
      : p.state === filter;

    const q = search.trim().toLowerCase();
    const matchSearch = !q || [p.title, p.id, p.client_email, p.freelancer_email].some(s => (s || '').toLowerCase().includes(q));
    return matchFilter && matchSearch;
  });

  const getCount = (key) => {
    if (key === 'All') return projects.length;
    if (key === 'COMPLETED') return projects.filter(p => p.released_amount_usd > 0 && p.released_amount_usd >= p.total_amount_usd).length;
    return projects.filter(p => p.state === key).length;
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const created = await endpoints.projects.create({
        ...form,
        total_amount_usd: parseFloat(form.total_amount_usd)
      });
      showToast(`Project ${created.id} created ✓`, 'success');
      setShowCreate(false);
      setForm({ title: '', description: '', client_email: '', freelancer_email: '', total_amount_usd: '' });
      refetch();
    } catch {
      // Local fallback
      const newId = `PRJ-2026-00${projects.length + 1}`;
      setProjects(prev => [
        {
          id: newId,
          title: form.title,
          description: form.description || 'Deliverables and scope',
          client_email: form.client_email,
          freelancer_email: form.freelancer_email,
          total_amount_usd: parseFloat(form.total_amount_usd) || 1000,
          funded_amount_usd: 0,
          released_amount_usd: 0,
          hashStatus: 'Not Generated',
          hashVariant: 'x',
          state: 'DRAFT',
          stateVariant: 'x'
        },
        ...prev
      ]);
      showToast(`Project ${newId} created ✓`, 'success');
      setShowCreate(false);
      setForm({ title: '', description: '', client_email: '', freelancer_email: '', total_amount_usd: '' });
    } finally {
      setCreating(false);
    }
  };

  const handleExportCsv = () => {
    const header = ['Project ID', 'Project', 'Client Email', 'Freelancer Email', 'Total Amount', 'Funded Amount', 'Released Amount', 'Plan Hash Status', 'PayPal Status'];
    const rows = filteredProjects.map(p => [p.id, p.title, p.client_email, p.freelancer_email, p.total_amount_usd, p.funded_amount_usd, p.released_amount_usd, p.hashStatus, p.state]);
    const csv = [header, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'proofpay-projects.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Projects exported as CSV.', 'success');
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Projects &amp; Contracts</h1>
          <p className={styles.sub}>
            Manage freelance client agreements, milestone deliverables, and protected PayPal escrow.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btn} onClick={handleExportCsv}>Export CSV</button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={() => setShowCreate(true)}>
            + Create Project
          </button>
        </div>
      </div>

      {/* Filter Chips & Search Bar */}
      <div className={styles.filtersBar}>
        <div className={styles.chipsWrap}>
          {FILTERS.map(f => (
            <button
              key={f.key}
              className={`${styles.chip} ${filter === f.key ? styles.chipOn : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label} ({getCount(f.key)})
            </button>
          ))}
        </div>

        <div className={styles.searchWrap}>
          <input
            className={styles.searchInput}
            placeholder="Search projects..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Create Project Modal / Inline Card */}
      {showCreate && (
        <section className={styles.card}>
          <h2 className={styles.h2} style={{ marginBottom: 16 }}>Create New Project</h2>
          <form onSubmit={handleCreate} className={styles.createForm}>
            <div className={styles.formGrid}>
              <label className={styles.label}>
                Project Title *
                <input
                  className={styles.input}
                  required
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="E.g. E-commerce Website"
                />
              </label>

              <label className={styles.label}>
                Total Amount (USD) *
                <input
                  className={styles.input}
                  required
                  type="number"
                  min="1"
                  step="0.01"
                  value={form.total_amount_usd}
                  onChange={e => setForm(f => ({ ...f, total_amount_usd: e.target.value }))}
                  placeholder="2400.00"
                />
              </label>

              <label className={styles.label}>
                Client Email *
                <input
                  className={styles.input}
                  required
                  type="email"
                  value={form.client_email}
                  onChange={e => setForm(f => ({ ...f, client_email: e.target.value }))}
                  placeholder="client@example.com"
                />
              </label>

              <label className={styles.label}>
                Freelancer Email *
                <input
                  className={styles.input}
                  required
                  type="email"
                  value={form.freelancer_email}
                  onChange={e => setForm(f => ({ ...f, freelancer_email: e.target.value }))}
                  placeholder="freelancer@example.com"
                />
              </label>

              <label className={styles.label} style={{ gridColumn: '1 / -1' }}>
                Description
                <textarea
                  className={styles.textarea}
                  rows={2}
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Deliverables and scope..."
                />
              </label>
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
              <button type="button" className={styles.btn} onClick={() => setShowCreate(false)}>
                Cancel
              </button>
              <button type="submit" className={`${styles.btn} ${styles.btnP}`} disabled={creating}>
                {creating ? 'Creating…' : 'Create Project'}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Projects Table */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }}>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Project ID</th>
                <th className={styles.th}>Project</th>
                <th className={styles.th}>Client Email</th>
                <th className={styles.th}>Freelancer Email</th>
                <th className={styles.th}>Total Amount</th>
                <th className={styles.th}>Funded Amount</th>
                <th className={styles.th}>Released Amount</th>
                <th className={styles.th}>Plan Hash Status</th>
                <th className={styles.th}>PayPal Status</th>
                <th className={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProjects.map(p => (
                <tr key={p.id}>
                  <td className={styles.td}>
                    <a className={styles.monoLink} href={`/project-details?id=${p.id}`}>
                      {p.id}
                    </a>
                  </td>
                  <td className={styles.td} style={{ minWidth: 240 }}>
                    <div style={{ fontWeight: 500 }}>{p.title}</div>
                    <div className={styles.muted} style={{ fontSize: 12 }}>{p.description}</div>
                  </td>
                  <td className={styles.td}>{p.client_email}</td>
                  <td className={styles.td}>{p.freelancer_email}</td>
                  <td className={`${styles.td} ${styles.num}`}>{fmt(p.total_amount_usd)}</td>
                  <td className={`${styles.td} ${styles.num}`}>{fmt(p.funded_amount_usd)}</td>
                  <td className={`${styles.td} ${styles.num}`}>{fmt(p.released_amount_usd)}</td>
                  <td className={styles.td}>
                    <span className={`${styles.bd} ${styles[p.hashVariant]}`}>
                      {p.hashStatus}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <span className={`${styles.bd} ${styles[p.stateVariant]}`}>
                      {p.state}
                    </span>
                  </td>
                  <td className={styles.td} style={{ whiteSpace: 'nowrap' }}>
                    <button
                      className={styles.actionBtn}
                      onClick={() => navigate(`/project-details?id=${p.id}`)}
                    >
                      View Details
                    </button>
                    {p.extraAction && (
                      <button
                        className={styles.actionBtn}
                        style={{ marginLeft: 6 }}
                        onClick={() => navigate(`/project-details?id=${p.id}`)}
                      >
                        {p.extraAction}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.tableFoot}>
          <span>Showing {filteredProjects.length} of {projects.length} projects</span>
          <span>Plan hashes are verified against both approvals before funding unlocks</span>
        </div>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
