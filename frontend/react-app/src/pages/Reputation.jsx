import { useState } from 'react';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './Reputation.module.css';

function ScoreBar({ score }) {
  const pct = Math.max(0, Math.min(100, score ?? 0));
  const color = pct >= 70 ? 'var(--green)' : pct >= 40 ? 'var(--amber)' : 'var(--red)';
  return (
    <div className={styles.scoreWrap}>
      <div className={styles.scoreNum} style={{ color }}>{pct}</div>
      <div className={styles.scoreLabel}>/ 100</div>
      <div className={styles.scoreBar}><div className={styles.scoreFill} style={{ width: `${pct}%`, background: color }} /></div>
    </div>
  );
}

export default function Reputation() {
  const [subject, setSubject] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);

  async function search(e) {
    e.preventDefault();
    if (!subject.trim()) return;
    setLoading(true);
    setData(null);
    try {
      const r = await endpoints.reputation.get(subject.trim());
      setData(r);
    } catch (err) {
      showToast(err.message, 'danger');
    } finally { setLoading(false); }
  }

  return (
    <div className={styles.page}>
      <div>
        <h1 className={styles.h1}>Reputation Ledger</h1>
        <p className={styles.sub}>Look up trust scores, payment history and dispute records for any entity.</p>
      </div>

      <Card>
        <form onSubmit={search} className={styles.searchForm}>
          <label className={styles.label}>Email or Subject ID</label>
          <div className={styles.row}>
            <input
              className={styles.input}
              placeholder="freelancer@example.com or SUBJ-001"
              value={subject}
              onChange={e => setSubject(e.target.value)}
            />
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? 'Looking up…' : 'Look Up'}
            </Button>
          </div>
        </form>
      </Card>

      {loading && <PageLoader />}

      {data && (
        <div className={styles.results}>
          <Card className={styles.scoreCard}>
            <div className={styles.scoreTitle}>Trust Score</div>
            <ScoreBar score={data.trust_score} />
            <div className={styles.scoreSubject}>{data.subject ?? subject}</div>
          </Card>
          <Card>
            <div className={styles.statTitle}>Reputation Details</div>
            <div className={styles.statGrid}>
              {[
                ['On-Time Payments', data.on_time_payments ?? '—'],
                ['Late Payments', data.late_payments ?? '—'],
                ['Disputes Filed', data.disputes ?? '—'],
                ['Disputes Lost', data.disputes_lost ?? '—'],
                ['Projects Completed', data.projects_completed ?? '—'],
                ['Recovery Rate', data.recovery_rate != null ? `${(data.recovery_rate * 100).toFixed(1)}%` : '—'],
              ].map(([k, v]) => (
                <div key={k} className={styles.statItem}>
                  <div className={styles.statLabel}>{k}</div>
                  <div className={styles.statValue}>{v}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {!loading && !data && (
        <Card>
          <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
            Enter an email address or subject ID above to look up their reputation score and payment history.
          </p>
        </Card>
      )}
    </div>
  );
}
