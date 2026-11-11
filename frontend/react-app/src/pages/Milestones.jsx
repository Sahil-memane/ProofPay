import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { PageLoader } from '../components/ui/Spinner';
import styles from './Milestones.module.css';

function fmt(n) { return `$${Number(n || 0).toFixed(2)} USD`; }

export default function Milestones() {
  const { data: projects, loading } = useApi(() => endpoints.projects.list());
  const navigate = useNavigate();

  const milestones = (projects ?? []).flatMap(p =>
    (p.milestones ?? []).map(m => ({ ...m, project_id: p.id, project_title: p.title }))
  );

  return (
    <div className={styles.page}>
      <div>
        <h1 className={styles.h1}>Milestones</h1>
        <p className={styles.sub}>All project milestones across active escrow contracts.</p>
      </div>

      {loading ? <PageLoader /> : (
        <Card noPadding>
          <div style={{ overflowX: 'auto' }}>
            <table className={styles.table}>
              <thead>
                <tr><th>#</th><th>Milestone ID</th><th>Project</th><th>Title</th><th>Amount</th><th>State</th><th>Due Date</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {milestones.map((m, i) => (
                  <tr key={m.id ?? i}>
                    <td className="muted">{i + 1}</td>
                    <td className="mono">{m.id ?? '—'}</td>
                    <td>
                      <button className={styles.link} onClick={() => navigate(`/project-details?id=${m.project_id}`)}>
                        {m.project_id}
                      </button>
                      <div className="muted" style={{ fontSize: 11 }}>{m.project_title}</div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{m.title}</div>
                      <div className="muted" style={{ fontSize: 12 }}>{m.description}</div>
                    </td>
                    <td className="tabular">{fmt(m.amount_usd)}</td>
                    <td><Badge variant={stateBadge(m.state)}>{m.state ?? 'PENDING'}</Badge></td>
                    <td className="muted">{m.due_date ?? '—'}</td>
                    <td>
                      <button className={styles.link} onClick={() => navigate(`/submissions?milestone_id=${m.id}&project_id=${m.project_id}`)}>
                        Submit Work
                      </button>
                    </td>
                  </tr>
                ))}
                {milestones.length === 0 && (
                  <tr><td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                    No milestones yet. <button className={styles.link} onClick={() => navigate('/projects')}>Create a project →</button>
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className={styles.footer}>{milestones.length} milestones across {(projects ?? []).length} projects</div>
        </Card>
      )}
    </div>
  );
}

