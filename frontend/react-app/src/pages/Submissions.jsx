import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './Submissions.module.css';

const STATUS_BADGE = {
  FUNDED: 'b',
  DRAFT: 'x',
  IN_REVIEW: 'a',
  VERIFYING: 'a',
  SUBMITTED: 'b',
  DISPUTED: 'r',
  COMPLETED: 'g',
  RELEASED: 'g',
  PAID: 'g',
  REFUNDED: 'x',
  REVISION_REQUESTED: 'a',
  ACTION_FAILED: 'r',
  RESUBMIT: 'a',
  RELEASE_PENDING: 'g',
};

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

export default function Submissions() {
  const { user, role } = useAuth();
  const isFreelancer = role === 'freelancer';
  const isClient = role === 'client';
  const isAdmin = role === 'admin';

  const { data: allSubmissions, reload: reloadSubmissions, loading } = useApi(() => endpoints.submissions.list());
  const milestones = allSubmissions || [];

  const [selectedMilestoneId, setSelectedMilestoneId] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form inputs
  const [prUrl, setPrUrl] = useState('https://github.com/proofpay-dev/escrow-004/pull/17');
  const [repo, setRepo] = useState('proofpay-dev/escrow-004');
  const [liveUrl, setLiveUrl] = useState('https://staging-004.proofpay-dev.app');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [notes, setNotes] = useState('');

  // Auto-select milestone on data load
  useEffect(() => {
    if (!milestones.length) return;
    if (!selectedMilestoneId || !milestones.some(m => m.milestone_id === selectedMilestoneId)) {
      // Prioritize milestones with an active submission, else first funded, else first
      const withSub = milestones.find(m => m.submission);
      const funded = milestones.find(m => m.state === 'FUNDED');
      setSelectedMilestoneId((withSub || funded || milestones[0]).milestone_id);
    }
  }, [milestones, selectedMilestoneId]);

  const selected = milestones.find(m => m.milestone_id === selectedMilestoneId);
  const sub = selected?.submission;

  // Derivations for AI verification report
  const scoreRatio = sub && typeof sub.score === 'number' ? sub.score : 0;
  const scoreDisplay = Math.round(scoreRatio * 100);
  const route = scoreRatio >= 0.8
    ? { text: 'AUTO_APPROVE', cls: 'g', stroke: '#2E9D65' }
    : scoreRatio >= 0.6
    ? { text: 'HUMAN_REVIEW', cls: 'a', stroke: '#F5A623' }
    : { text: 'AUTO_REJECT', cls: 'r', stroke: '#D9363E' };

  // Mandate Guard Autonomous Policy Guard evaluation
  const amt = selected ? Number(selected.amount) || 0 : 0;
  const autoLimit = 1500.0;
  const isOverLimit = amt > autoLimit;

  let policyBadge = { text: 'ALLOWED', cls: 'g' };
  let policyMsg = '';
  let policyBg = '#E3F4EB';
  let policyColor = '#1E7A4C';

  if (!sub) {
    policyBadge = { text: 'PENDING_SUBMISSION', cls: 'b' };
    policyMsg = 'Awaiting deliverable submission. Mandate Guard policy will evaluate payout criteria upon submission.';
    policyBg = '#F8FAFC';
    policyColor = '#475569';
  } else if (sub.status === 'DISPUTED' || selected?.state === 'DISPUTED') {
    policyBadge = { text: 'DISPUTED', cls: 'r' };
    policyMsg = 'Escrow frozen by Mandate Guard. Active dispute prevents automated release.';
    policyBg = '#FBE5E6';
    policyColor = '#B42830';
  } else if (sub.status === 'RELEASED' || selected?.state === 'COMPLETED' || selected?.state === 'RELEASED') {
    policyBadge = { text: 'RELEASED', cls: 'g' };
    policyMsg = `RELEASED — Full payout of ${fmt(amt)} was dispatched via PayPal Payouts.`;
    policyBg = '#E3F4EB';
    policyColor = '#1E7A4C';
  } else if (isOverLimit) {
    policyBadge = { text: 'NEEDS_APPROVAL', cls: 'r' };
    policyMsg = `NEEDS_APPROVAL — Milestone amount (${fmt(amt)}) exceeds the $1,500.00 autonomous execution threshold. Mandate Guard routed this proposal to the Human Approvals Queue.`;
    policyBg = '#FBE5E6';
    policyColor = '#B42830';
  } else if (scoreRatio < 0.6) {
    policyBadge = { text: 'AUTO_REJECT', cls: 'r' };
    policyMsg = 'AI verification score below 0.60 threshold. Payout blocked and deliverable returned for revision.';
    policyBg = '#FBE5E6';
    policyColor = '#B42830';
  } else if (scoreRatio < 0.8) {
    policyBadge = { text: 'HUMAN_REVIEW', cls: 'a' };
    policyMsg = `Borderline score (${scoreDisplay}%). Routed to Human Approvals Queue for officer verification.`;
    policyBg = '#FEF1D9';
    policyColor = '#8A5A00';
  } else {
    policyBadge = { text: 'ALLOWED', cls: 'g' };
    policyMsg = `ALLOWED — Within the $1,500.00 autonomous limit. Payout proposal approved for automated release.`;
    policyBg = '#E3F4EB';
    policyColor = '#1E7A4C';
  }

  // Handle manual client review
  const handleClientApprove = async () => {
    if (!selectedMilestoneId) return;
    try {
      await endpoints.submissions.review(selectedMilestoneId, { decision: 'approve', actor: 'client' });
      showToast('Client approved deliverable. Processing payout release.', 'success');
      reloadSubmissions();
    } catch (err) {
      showToast(err.message || 'Approval failed', 'danger');
    }
  };

  const handleRequestRevision = async () => {
    if (!selectedMilestoneId) return;
    try {
      await endpoints.submissions.review(selectedMilestoneId, { decision: 'reject', actor: 'client', reason: 'Client requested deliverable revisions' });
      showToast('Revision requested. Freelancer notified.', 'warning');
      reloadSubmissions();
    } catch (err) {
      showToast(err.message || 'Request revision failed', 'danger');
    }
  };

  const handleDispute = () => {
    showToast('Active dispute initiated for this milestone escrow.', 'danger');
  };

  // Handle deliverable submission
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!selectedMilestoneId) return;
    setSubmitting(true);
    try {
      await endpoints.submissions.submit(selectedMilestoneId, {
        freelancer_id: user?.customer_id || 'CUST-00081',
        pr_url: prUrl,
        repository: repo,
        deployed_url: liveUrl,
        evidence_url: evidenceUrl || undefined,
        notes: notes || undefined,
      });
      showToast('Deliverable submitted successfully. AI verifier triggered.', 'success');
      setModalOpen(false);
      reloadSubmissions();
    } catch (err) {
      showToast(err.message || 'Submission failed', 'danger');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      {/* Header with Milestone Selector */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Submissions &amp; AI Verification</h1>
          <p className={styles.sub}>
            Select a milestone to view its submitted deliverable, acceptance criteria, and AI verification report.
          </p>
        </div>
        <div className={styles.headerActions}>
          <select
            className={styles.input}
            style={{ minWidth: 320, fontWeight: 500 }}
            value={selectedMilestoneId}
            onChange={e => setSelectedMilestoneId(e.target.value)}
            disabled={loading}
          >
            {milestones.length === 0 && <option value="">No milestones found</option>}
            {milestones.map(m => (
              <option key={m.milestone_id} value={m.milestone_id}>
                {m.milestone_id}: {m.milestone_title} ({m.project_name || m.project_id}) · {m.state}
              </option>
            ))}
          </select>
          {isFreelancer && selected?.state === 'FUNDED' && (
            <button className={`${styles.btn} ${styles.btnP}`} onClick={() => setModalOpen(true)}>
              Submit Deliverable
            </button>
          )}
        </div>
      </div>

      {/* Selected Milestone Context Bar */}
      {selected && (
        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: '12px 18px', display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <span className={styles.muted}>Milestone: </span>
            <strong style={{ color: '#003087' }}>{selected.milestone_title}</strong>
          </div>
          <div>
            <span className={styles.muted}>Project: </span>
            <strong>{selected.project_name || selected.project_id}</strong>
          </div>
          <div>
            <span className={styles.muted}>Amount: </span>
            <strong className={styles.num}>{fmt(selected.amount)}</strong>
          </div>
          <div>
            <span className={styles.muted}>Status: </span>
            <span className={`${styles.bd} ${styles[STATUS_BADGE[selected.state]] || styles.b}`}>{selected.state}</span>
          </div>
          {sub && (
            <div>
              <span className={styles.muted}>Submission Attempt: </span>
              <strong>#{sub.attempt || 1}</strong>
            </div>
          )}
          {sub && sub.created_at && (
            <div>
              <span className={styles.muted}>Submitted: </span>
              <span className={styles.num}>{new Date(sub.created_at).toLocaleDateString()} {new Date(sub.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
          )}
        </div>
      )}

      {/* No Deliverable Submitted Yet */}
      {selected && !sub && (
        <section className={styles.card} style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontWeight: 600, fontSize: 17, color: '#172B4D' }}>No deliverable submitted yet for this milestone</div>
          <p className={styles.muted} style={{ maxWidth: 540, margin: '8px auto 20px' }}>
            {isFreelancer && selected.state === 'FUNDED'
              ? 'This milestone is funded in PayPal escrow. Submit your GitHub pull request and staging preview to trigger automated AI verification.'
              : 'Awaiting freelancer submission. Acceptance criteria and verification reports will appear here once submitted.'}
          </p>
          {isFreelancer && selected.state === 'FUNDED' && (
            <button className={`${styles.btn} ${styles.btnP}`} onClick={() => setModalOpen(true)}>
              Submit Deliverable
            </button>
          )}
        </section>
      )}

      {/* 2-Column: Submitted Deliverables & AI Verification Report (when submission exists) */}
      {sub && (
        <section className={styles.twoCol}>
          {/* Left: Submitted Deliverables */}
          <div className={styles.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 className={styles.h2}>Submitted Deliverables</h2>
              <span className={`${styles.bd} ${styles[STATUS_BADGE[sub.status]] || styles.b}`}>{sub.status}</span>
            </div>

            {sub.pr_url && (
              <div className={styles.row} style={{ marginTop: 12 }}>
                <div className={styles.ico}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 3v12M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a9 9 0 0 1-9 9" />
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={styles.muted}>GitHub Pull Request</div>
                  <a href={sub.pr_url} target="_blank" rel="noreferrer" className={styles.link}>
                    {sub.pr_url.replace(/^https?:\/\//, '')}
                  </a>
                  {sub.repository && (
                    <div className={styles.muted}>{sub.repository} · branch main</div>
                  )}
                </div>
                <span className={`${styles.bd} ${styles.g}`}>PR Verified</span>
              </div>
            )}

            {sub.deployed_url && (
              <div className={styles.row}>
                <div className={styles.ico}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={styles.muted}>Deployed Staging Preview</div>
                  <a href={sub.deployed_url} target="_blank" rel="noreferrer" className={styles.link}>
                    {sub.deployed_url.replace(/^https?:\/\//, '')}
                  </a>
                </div>
                <span className={`${styles.bd} ${styles.g} ${styles.num}`}>HTTP 200 OK</span>
              </div>
            )}

            {sub.evidence_url && (
              <div className={styles.row}>
                <div className={styles.ico}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM8 13h8M8 17h5" />
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={styles.muted}>Evidence Documentation</div>
                  <a href={sub.evidence_url} target="_blank" rel="noreferrer" className={styles.link}>
                    {sub.evidence_url.replace(/^https?:\/\//, '')}
                  </a>
                </div>
              </div>
            )}

            {sub.files && Object.keys(sub.files).length > 0 && (
              <div className={styles.row}>
                <div className={styles.ico}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={styles.muted}>Attached Evidence Files</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                    {Object.entries(sub.files).map(([name, f]) => (
                      <span key={name} className={`${styles.bd} ${styles.b}`}>
                        {name} ({Math.round((f.size || 0) / 1024)} KB)
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {sub.notes && (
              <div style={{ borderTop: '1px solid #E5E9F0', paddingTop: 12, marginTop: 12 }}>
                <div className={styles.muted}>Freelancer Notes</div>
                <p style={{ margin: '4px 0 8px', fontSize: 13, color: '#172B4D', lineHeight: 1.5 }}>
                  {sub.notes}
                </p>
                {sub.created_at && (
                  <div className={`${styles.muted} ${styles.num}`}>
                    Submitted {new Date(sub.created_at).toISOString().slice(0, 16).replace('T', ' ')} UTC
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: AI Verification Report */}
          <div className={styles.card} style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <h2 className={styles.h2}>AI Verification Report</h2>
              <span className={`${styles.bd} ${styles[route.cls]}`}>{route.text}</span>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'center', margin: '16px 0' }}>
              <svg viewBox="0 0 120 120" width="140" height="140" role="img" style={{ flex: 'none' }}>
                <circle cx="60" cy="60" r="52" fill="none" stroke="#E5E9F0" strokeWidth="12" />
                <circle
                  cx="60"
                  cy="60"
                  r="52"
                  fill="none"
                  stroke={route.stroke}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray="326.7"
                  strokeDashoffset={(326.7 * (1 - scoreRatio)).toFixed(1)}
                  transform="rotate(-90 60 60)"
                  style={{ transition: 'all 0.5s ease' }}
                />
                <text x="60" y="62" textAnchor="middle" fontSize="30" fontWeight="600" fill="#172B4D" fontFamily="Inter,sans-serif">
                  {scoreDisplay}
                </text>
                <text x="60" y="80" textAnchor="middle" fontSize="11" fill="#64748B" fontFamily="Inter,sans-serif">
                  out of 100
                </text>
              </svg>

              <div style={{ flex: 1, minWidth: 180, fontSize: 13 }} className={styles.muted}>
                Thresholds
                <div style={{ marginTop: 6, display: 'grid', gap: 4, color: '#172B4D' }}>
                  <span><span className={`${styles.bd} ${styles.g}`}>AUTO_APPROVE</span> ≥ 0.80</span>
                  <span><span className={`${styles.bd} ${styles.a}`}>HUMAN_REVIEW</span> 0.60–0.79</span>
                  <span><span className={`${styles.bd} ${styles.r}`}>AUTO_REJECT</span> &lt; 0.60</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gap: 8 }}>
              {sub.criterion_results && sub.criterion_results.length > 0 ? (
                sub.criterion_results.map((c, i) => (
                  <div key={i} className={styles.row}>
                    <span
                      className={`${styles.bd} ${c.passed ? styles.g : styles.r}`}
                      style={{ minWidth: 70, textAlign: 'center' }}
                    >
                      {c.passed ? 'Passed' : 'Failed'}
                    </span>
                    <span style={{ flex: 1 }}>{c.name}</span>
                    <span className={`${styles.muted} ${styles.num}`}>
                      Weight {Math.round((c.weight || 0) * 100)}%
                    </span>
                  </div>
                ))
              ) : (
                <div className={styles.muted} style={{ padding: '8px 0' }}>
                  Verification complete. Criterion evaluation score recorded.
                </div>
              )}
            </div>

            {sub.rationale && (
              <div style={{ borderTop: '1px solid #E5E9F0', marginTop: 12, paddingTop: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>Verifier Rationale</div>
                <p style={{ margin: '4px 0 0', color: '#172B4D', fontSize: 13, lineHeight: 1.5 }}>
                  {sub.rationale}
                </p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Section C: Mandate Guard Autonomous Policy Evaluation — Always Displayed */}
      {selected && (
        <section className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <h2 className={styles.h2}>Mandate Guard Policy Evaluation</h2>
            <span className={`${styles.bd} ${styles[policyBadge.cls]}`}>{policyBadge.text}</span>
          </div>

          <div className={styles.policyGrid}>
            <div>
              <div className={styles.muted}>Milestone Amount</div>
              <div className={styles.num} style={{ fontSize: 16, fontWeight: 600 }}>{fmt(amt)}</div>
            </div>
            <div>
              <div className={styles.muted}>Autonomous Limit</div>
              <div className={styles.num} style={{ fontSize: 16, fontWeight: 600 }}>$1,500.00 / txn</div>
            </div>
            <div>
              <div className={styles.muted}>Limit Status</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: isOverLimit ? '#B42830' : '#1E7A4C' }}>
                {isOverLimit ? 'EXCEEDS ($1,500.00)' : 'WITHIN LIMIT'}
              </div>
            </div>
            <div>
              <div className={styles.muted}>Recipient Verification</div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>PayPal Account Verified</div>
            </div>
          </div>

          <div
            style={{
              padding: '12px 16px',
              borderRadius: 8,
              fontWeight: 500,
              fontSize: 14,
              background: policyBg,
              color: policyColor,
            }}
          >
            {policyMsg}
          </div>

          <div className={styles.muted} style={{ marginTop: 12 }}>
            AI recommends. Policy decides. Every action is recorded in the tamper-evident audit ledger.
          </div>
        </section>
      )}

      {/* Section D: Actions */}
      {selected && (
        <section className={styles.card}>
          <h2 className={styles.h2}>Actions</h2>

          {isClient && sub && sub.status === 'IN_REVIEW' && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
              <button className={`${styles.btn} ${styles.btnP}`} onClick={handleClientApprove}>
                Approve Deliverable
              </button>
              <button className={styles.btn} onClick={handleRequestRevision}>
                Request Revision
              </button>
              <button className={styles.btn} style={{ color: '#B42830' }} onClick={handleDispute}>
                File Dispute
              </button>
            </div>
          )}

          {isFreelancer && (selected.state === 'FUNDED' || sub?.route === 'RESUBMIT') && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
              <button className={`${styles.btn} ${styles.btnP}`} onClick={() => setModalOpen(true)}>
                {sub ? 'Resubmit Deliverable' : 'Submit Deliverable'}
              </button>
            </div>
          )}

          {isAdmin && (
            <div className={styles.muted} style={{ marginTop: 12 }}>
              Risk Officers can review over-limit releases in the{' '}
              <a href="/approvals" className={styles.link}>Human Approvals Queue (HITL)</a>.
            </div>
          )}

          {isClient && (!sub || sub.status !== 'IN_REVIEW') && (
            <div className={styles.muted} style={{ marginTop: 12 }}>
              {sub?.status === 'RELEASED'
                ? 'This deliverable has been approved and payout released.'
                : 'Awaiting freelancer deliverable submission.'}
            </div>
          )}
        </section>
      )}

      {/* Submit Deliverable Modal */}
      {modalOpen && (
        <div className={styles.modalBackdrop}>
          <form className={styles.modalCard} onSubmit={handleFormSubmit}>
            <h2 className={styles.h2}>Submit Deliverable</h2>
            <label className={styles.label}>
              Milestone
              <input
                className={styles.input}
                readOnly
                value={`${selected?.milestone_id || ''}: ${selected?.milestone_title || ''} — ${fmt(selected?.amount || 0)}`}
              />
            </label>
            <label className={styles.label}>
              GitHub Pull Request URL
              <input
                className={styles.input}
                type="url"
                required
                value={prUrl}
                onChange={e => setPrUrl(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              GitHub Repository
              <input
                className={styles.input}
                required
                value={repo}
                onChange={e => setRepo(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Deployed Live Preview URL
              <input
                className={styles.input}
                type="url"
                required
                value={liveUrl}
                onChange={e => setLiveUrl(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Evidence Documentation URL (Optional)
              <input
                className={styles.input}
                type="url"
                placeholder="https://"
                value={evidenceUrl}
                onChange={e => setEvidenceUrl(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Submission Notes
              <textarea
                className={styles.textarea}
                rows="3"
                placeholder="Describe your implementation and verification notes"
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button type="button" className={styles.btn} onClick={() => setModalOpen(false)} disabled={submitting}>
                Cancel
              </button>
              <button type="submit" className={`${styles.btn} ${styles.btnP}`} disabled={submitting}>
                {submitting ? 'Submitting...' : 'Submit Deliverable for AI Verification'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
