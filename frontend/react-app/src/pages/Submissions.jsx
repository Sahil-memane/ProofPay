import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge, stateBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './Submissions.module.css';

function ScoreGauge({ score }) {
  const pct = Math.max(0, Math.min(100, score ?? 0));
  const color = pct >= 80 ? 'var(--green)' : pct >= 50 ? 'var(--amber)' : 'var(--red)';
  return (
    <div className={styles.gauge}>
      <div className={styles.gaugeTrack}>
        <div className={styles.gaugeFill} style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className={styles.gaugeScore} style={{ color }}>{pct}/100</span>
    </div>
  );
}

export default function Submissions() {
  const [params] = useSearchParams();
  const milestoneId = params.get('milestone_id') ?? '';
  const projectId   = params.get('project_id') ?? '';

  const { data: submission, loading, refetch } = useApi(
    () => milestoneId ? endpoints.submissions.get(milestoneId) : Promise.resolve(null),
    [milestoneId]
  );

  const [submitting, setSubmitting] = useState(false);
  const [evidence, setEvidence] = useState('');
  const [notes, setNotes] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    if (!milestoneId) return showToast('No milestone selected', 'danger');
    setSubmitting(true);
    try {
      await endpoints.submissions.submit(milestoneId, { evidence_url: evidence, notes });
      showToast('Work submitted for AI verification ✓', 'success');
      setEvidence(''); setNotes('');
      refetch();
    } catch (err) { showToast(err.message, 'danger'); }
    finally { setSubmitting(false); }
  }

  async function injectVerification(scenario) {
    try {
      await endpoints.submissions.inject(milestoneId, { scenario });
      showToast(`Injected: ${scenario}`, 'info');
      refetch();
    } catch (e) { showToast(e.message, 'danger'); }
  }

  async function reviewSubmission(approved) {
    if (!submission?.id) return;
    try {
      await endpoints.submissions.review(milestoneId, { approved, comment: approved ? 'Approved by admin' : 'Rejected by admin' });
      showToast(approved ? 'Submission approved ✓' : 'Submission rejected', approved ? 'success' : 'warning');
      refetch();
    } catch (e) { showToast(e.message, 'danger'); }
  }

  const sub = submission;

  const routeVariant = {
    AUTO_APPROVE: 'success',
    HUMAN_REVIEW: 'warning',
    AUTO_REJECT:  'danger',
  };

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Submissions & AI Verification</h1>
          <p className={styles.sub}>Submit work, receive AI-graded scores, and trigger milestone payouts via PayPal.</p>
        </div>
        {projectId && <a href={`/project-details?id=${projectId}`} className={styles.backLink}>← Back to Project</a>}
      </div>

      {/* Submit form */}
      <Card>
        <div className={styles.sectionTitle}>Submit Work Evidence</div>
        {!milestoneId && (
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>
            Navigate here from a milestone in <a href="/project-details">Project Details</a> to submit work.
          </div>
        )}
        {milestoneId && (
          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.field}>
              <label>Milestone ID</label>
              <input readOnly value={milestoneId} className={styles.input} />
            </div>
            <div className={styles.field}>
              <label>Evidence URL / GitHub Link *</label>
              <input required value={evidence} onChange={e => setEvidence(e.target.value)} placeholder="https://github.com/..." className={styles.input} />
            </div>
            <div className={styles.field}>
              <label>Notes for Verifier</label>
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} placeholder="Describe what was completed…" className={styles.textarea} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button type="submit" variant="primary" disabled={submitting}>{submitting ? 'Submitting…' : 'Submit for AI Verification'}</Button>
            </div>
          </form>
        )}
      </Card>

      {/* Verification result */}
      {loading && <PageLoader />}
      {sub && (
        <Card>
          <div className={styles.sectionTitle}>AI Verification Result</div>
          <div className={styles.resultGrid}>
            <div>
              <div className={styles.metaLabel}>AI Score</div>
              <ScoreGauge score={sub.score} />
            </div>
            <div>
              <div className={styles.metaLabel}>Route Decision</div>
              <div style={{ marginTop: 8 }}>
                <Badge variant={routeVariant[sub.route] ?? 'neutral'}>{sub.route ?? '—'}</Badge>
              </div>
            </div>
            <div>
              <div className={styles.metaLabel}>Mandate Guard</div>
              <div style={{ marginTop: 8 }}>
                <Badge variant={sub.mandate_guard_passed ? 'success' : 'danger'}>
                  {sub.mandate_guard_passed ? '✓ ALLOWED' : '✗ BLOCKED'}
                </Badge>
              </div>
            </div>
            <div>
              <div className={styles.metaLabel}>Status</div>
              <div style={{ marginTop: 8 }}><Badge variant={stateBadge(sub.state)}>{sub.state}</Badge></div>
            </div>
          </div>

          {/* Criteria checklist */}
          {sub.criteria && (
            <div className={styles.criteria}>
              <div className={styles.metaLabel}>Verification Criteria</div>
              {sub.criteria.map((c, i) => (
                <div key={i} className={styles.criterionRow}>
                  <span className={c.passed ? styles.checkGreen : styles.checkRed}>{c.passed ? '✓' : '✗'}</span>
                  <span>{c.label}</span>
                  {c.score != null && <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>{c.score}/100</span>}
                </div>
              ))}
            </div>
          )}

          {/* Admin actions */}
          {sub.route === 'HUMAN_REVIEW' && (
            <div className={styles.reviewActions}>
              <div className={styles.metaLabel}>Manual Review Required</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <Button variant="primary" onClick={() => reviewSubmission(true)}>✓ Approve Payout</Button>
                <Button variant="danger" onClick={() => reviewSubmission(false)}>✗ Reject</Button>
              </div>
            </div>
          )}

          {/* Demo injectors */}
          {milestoneId && (
            <div className={styles.injectSection}>
              <div className={styles.metaLabel}>Demo: Inject Verification Scenario</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                {['AUTO_APPROVE', 'HUMAN_REVIEW', 'AUTO_REJECT', 'MANDATE_BLOCKED'].map(s => (
                  <Button key={s} variant="secondary" size="sm" onClick={() => injectVerification(s)}>{s}</Button>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

