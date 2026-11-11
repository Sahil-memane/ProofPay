import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { showToast } from '../components/ui/Toast';
import styles from './Submissions.module.css';

const SCENARIOS = {
  '0.95': {
    s: 94,
    c: ['p', 'p', 'p', 'h'],
    why: 'The PR builds and lints cleanly, the staging endpoint returns HTTP 200 with valid assets, and the layout is stable across breakpoints. Coverage is 78% against an 80% target, which costs a few points.'
  },
  '0.72': {
    s: 72,
    c: ['p', 'p', 'h', 'f'],
    why: 'Core functionality works, but layout shifts appear at tablet width and coverage is well below target. The result is borderline, so a human should review the evidence.'
  },
  '0.45': {
    s: 45,
    c: ['f', 'h', 'f', 'f'],
    why: 'The PR fails the build step and the staging endpoint serves incomplete assets. Most acceptance criteria are not met, so the deliverable is rejected.'
  }
};

const CRITERIA = [
  ['35%', 'GitHub PR exists, passes linting & build'],
  ['35%', 'Deployed endpoint returns HTTP 200 with valid UI assets'],
  ['20%', 'Responsive layout rendered without layout shifts'],
  ['10%', 'Unit test coverage at 78% (Target 80%)']
];

const STATUS_ICONS = {
  p: ['✅ Passed', 'g'],
  h: ['⚠️ Partial', 'a'],
  f: ['❌ Failed', 'r']
};

export default function Submissions() {
  const { role } = useAuth();
  const [scenarioKey, setScenarioKey] = useState('0.95');
  const [statusBadge, setStatusBadge] = useState({ text: 'SUBMITTED', cls: 'b' });
  const [amountOption, setAmountOption] = useState('700');
  const [modalOpen, setModalOpen] = useState(false);

  // Form inputs
  const [prUrl, setPrUrl] = useState('https://github.com/acme/shop/pull/42');
  const [repo, setRepo] = useState('acme/shop');
  const [liveUrl, setLiveUrl] = useState('https://preview-42.acme.app');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [notes, setNotes] = useState('');

  const scenario = SCENARIOS[scenarioKey];
  const amt = parseFloat(amountOption);
  const scoreRatio = scenario.s / 100;

  // Verification route
  const route = scoreRatio >= 0.8
    ? { text: 'AUTO_APPROVE', cls: 'g', stroke: '#2E9D65' }
    : scoreRatio >= 0.6
    ? { text: 'HUMAN_REVIEW', cls: 'a', stroke: '#F5A623' }
    : { text: 'AUTO_REJECT', cls: 'r', stroke: '#D9363E' };

  // Mandate Guard policy calculation
  let policyBadge = { text: 'ALLOWED', cls: 'g' };
  let policyMsg = '';
  let policyBg = '#E3F4EB';
  let policyColor = '#1E7A4C';

  if (route.text === 'AUTO_REJECT') {
    policyBadge = { text: 'NOT_EVALUATED', cls: 'b' };
    policyMsg = 'No payout proposed. Verification score is below 0.60, so the deliverable was auto-rejected and returned to the freelancer.';
    policyBg = '#E6F0FC';
    policyColor = '#005BB5';
  } else if (route.text === 'HUMAN_REVIEW') {
    policyBadge = { text: 'HUMAN_REVIEW', cls: 'a' };
    policyMsg = `Borderline score. Payout of $${amt.toFixed(2)} routed to the Human Approvals Queue (Task #APP-105).`;
    policyBg = '#FEF1D9';
    policyColor = '#8A5A00';
  } else if (amt <= 200) {
    policyBadge = { text: 'ALLOWED', cls: 'g' };
    policyMsg = 'ALLOWED — Within the $200.00 autonomous limit. Dispatched PayPal Payout batch ID: PAYOUT-BATCH-771.';
    policyBg = '#E3F4EB';
    policyColor = '#1E7A4C';
  } else {
    policyBadge = { text: 'DENIED', cls: 'r' };
    policyMsg = 'DENIED — Exceeds autonomous limit ($200.00). Sent to Human Approvals Queue (Task #APP-104).';
    policyBg = '#FBE5E6';
    policyColor = '#B42830';
  }

  const auditHash = {
    '0.95': 'sha256:7c1e…b94a',
    '0.72': 'sha256:3fa9…02de',
    '0.45': 'sha256:d81b…6c57'
  }[scenarioKey];

  const handleInject = (key) => {
    setScenarioKey(key);
    setStatusBadge({ text: 'VERIFIED', cls: 'b' });
    showToast(`Verifier injected: ${key} → ${SCENARIOS[key].s >= 80 ? 'AUTO_APPROVE' : SCENARIOS[key].s >= 60 ? 'HUMAN_REVIEW' : 'AUTO_REJECT'}`, 'info');
    if (key === '0.72' || (key === '0.95' && amt > 200)) {
      showToast('Policy Alert: Payout routed to Human Approvals Queue.', 'warning');
    }
  };

  const handleClientApprove = () => {
    if (policyBadge.text === 'ALLOWED') {
      showToast('Payout dispatched via PayPal Payouts (PAYOUT-BATCH-771).', 'success');
    } else {
      showToast('Policy Alert: Payout exceeds $200.00 limit. Routed to Human Approvals Queue.', 'warning');
    }
  };

  const handleRequestRevision = () => {
    setStatusBadge({ text: 'REVISION_REQUESTED', cls: 'a' });
    showToast('Revision requested. Freelancer notified.', 'warning');
  };

  const handleRefund = () => {
    showToast('Refund request submitted for review.', 'warning');
  };

  const handleDispute = () => {
    setStatusBadge({ text: 'DISPUTED', cls: 'r' });
    showToast('Dispute filed. Escrow frozen for this milestone.', 'danger');
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    setModalOpen(false);
    setStatusBadge({ text: 'VERIFYING', cls: 'b' });
    showToast('Success: Milestone deliverable submitted successfully.', 'success');
    setTimeout(() => {
      setStatusBadge({ text: 'VERIFIED', cls: 'b' });
    }, 1200);
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Submissions &amp; AI Verification</h1>
          <p className={styles.sub}>
            Milestone 2: Frontend Integration &amp; API Client · <span className={styles.num}>$700.00 USD</span> · PRJ-2026-001
          </p>
        </div>
        <div className={styles.headerActions}>
          {role === 'freelancer' && (
            <button className={`${styles.btn} ${styles.btnP}`} onClick={() => setModalOpen(true)}>
              Submit Deliverable
            </button>
          )}
        </div>
      </div>

      {/* 2-Column: Submitted Deliverables & AI Verification Report */}
      <section className={styles.twoCol}>
        {/* Left: Submitted Deliverables */}
        <div className={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 className={styles.h2}>Submitted Deliverables</h2>
            <span className={`${styles.bd} ${styles[statusBadge.cls]}`}>{statusBadge.text}</span>
          </div>

          <div className={styles.row} style={{ marginTop: 12 }}>
            <div className={styles.ico}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 3v12M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a9 9 0 0 1-9 9" />
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className={styles.muted}>GitHub Pull Request</div>
              <a href={prUrl} target="_blank" rel="noreferrer" className={styles.link}>
                github.com/acme/shop/pull/42
              </a>
              <div className={styles.muted}>acme/shop · branch feat/api-client · commit <code className={styles.mono}>9f8a12e</code></div>
            </div>
            <span className={`${styles.bd} ${styles.g}`}>Build passing</span>
          </div>

          <div className={styles.row}>
            <div className={styles.ico}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className={styles.muted}>Deployed Staging Preview</div>
              <a href={liveUrl} target="_blank" rel="noreferrer" className={styles.link}>
                preview-42.acme.app
              </a>
            </div>
            <span className={`${styles.bd} ${styles.g} ${styles.num}`}>HTTP 200 OK · 128ms</span>
          </div>

          <div className={styles.row}>
            <div className={styles.ico}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM8 13h8M8 17h5" />
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className={styles.muted}>Evidence</div>
              <a href="#" className={styles.link}>docs.acme.app/m2-evidence</a>
              <div className={styles.muted}>test-logs.zip (212 KB) · coverage-report.pdf (88 KB)</div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid #E5E9F0', paddingTop: 12, marginTop: 12 }}>
            <div className={styles.muted}>Freelancer notes · Rahul Sharma</div>
            <p style={{ margin: '4px 0 8px', fontSize: 13, color: '#172B4D' }}>
              Integrated the REST client with retry and error handling, wired product and cart views, and added responsive breakpoints. Remaining gap: two checkout hooks lack unit tests.
            </p>
            <div className={`${styles.muted} ${styles.num}`}>Submitted 2026-11-11 11:30 UTC</div>
          </div>
        </div>

        {/* Right: AI Verification Report */}
        <div className={styles.card} style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <h2 className={styles.h2}>AI Verification Report</h2>
            <span className={`${styles.bd} ${styles[route.cls]}`}>{route.text}</span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'center', margin: '16px 0' }}>
            <svg viewBox="0 0 120 120" width="150" height="150" role="img" style={{ flex: 'none' }}>
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
                {scenario.s}
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
            {CRITERIA.map((c, i) => {
              const statusKey = scenario.c[i];
              const [label, badgeClass] = STATUS_ICONS[statusKey];
              return (
                <div key={c[1]} className={styles.row}>
                  <span className={`${styles.bd} ${styles[badgeClass]}`} style={{ minWidth: 84, textAlign: 'center' }}>
                    {label}
                  </span>
                  <span style={{ flex: 1 }}>{c[1]}</span>
                  <span className={`${styles.muted} ${styles.num}`}>Weight {c[0]}</span>
                </div>
              );
            })}
          </div>

          <div style={{ borderTop: '1px solid #E5E9F0', marginTop: 12, paddingTop: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>Verifier rationale</div>
            <p style={{ margin: '4px 0 0', color: '#172B4D', fontSize: 13 }}>
              {scenario.why}
            </p>
          </div>
        </div>
      </section>

      {/* Section C: Mandate Guard Policy Evaluation */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <h2 className={styles.h2}>Mandate Guard Policy Evaluation</h2>
          <span className={`${styles.bd} ${styles[policyBadge.cls]}`}>{policyBadge.text}</span>
        </div>

        <div className={styles.policyGrid}>
          <div>
            <div className={styles.muted}>Payout amount</div>
            <div className={`${styles.num}`} style={{ fontSize: 16, fontWeight: 600 }}>${amt.toFixed(2)}</div>
          </div>
          <div>
            <div className={styles.muted}>Autonomous limit</div>
            <div className={`${styles.num}`} style={{ fontSize: 16, fontWeight: 600 }}>$200.00 / txn</div>
          </div>
          <div>
            <div className={styles.muted}>Daily volume</div>
            <div className={`${styles.num}`} style={{ fontSize: 16, fontWeight: 600 }}>$650.00 of $5,000.00</div>
          </div>
          <div>
            <div className={styles.muted}>Verified PayPal email</div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>freelancer@example.com ✓</div>
          </div>
        </div>

        <div
          style={{
            padding: '12px 16px',
            borderRadius: 8,
            fontWeight: 500,
            fontSize: 14,
            background: policyBg,
            color: policyColor
          }}
        >
          {policyMsg}
        </div>

        <div className={styles.muted} style={{ marginTop: 12 }}>
          AI recommends. Policy decides. Audit hash <code className={styles.mono}>{auditHash}</code> ·{' '}
          <a href="/audit" className={styles.link}>View in Audit Trail</a>
        </div>
      </section>

      {/* Section D: Role-specific Actions */}
      <section className={styles.card}>
        <h2 className={styles.h2}>Actions</h2>

        {role === 'client' && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
            <button className={`${styles.btn} ${styles.btnP}`} onClick={handleClientApprove}>
              Approve Payout
            </button>
            <button className={styles.btn} onClick={handleRequestRevision}>
              Request Revisions
            </button>
            <button className={styles.btn} style={{ color: '#B42830' }} onClick={handleRefund}>
              Request Refund
            </button>
            <button className={styles.btn} style={{ color: '#B42830' }} onClick={handleDispute}>
              Dispute
            </button>
          </div>
        )}

        {role === 'freelancer' && (
          <div className={styles.muted} style={{ marginTop: 12 }}>
            Freelancers can resubmit deliverables or track verification here. Switch to Client to review.
          </div>
        )}

        {role === 'admin' && (
          <div className={styles.muted} style={{ marginTop: 12 }}>
            Risk Officers decide over-limit releases in the <a href="/approvals" className={styles.link}>Approvals Queue</a>.
          </div>
        )}

        {role === 'admin' && (
          <div style={{ borderTop: '1px dashed #E5E9F0', marginTop: 16, paddingTop: 16 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
              <span className={`${styles.bd} ${styles.a}`}>⚡ DEMO</span>
              <span className={styles.muted}>POST /milestones/&#123;id&#125;/_inject_verification</span>
              <button className={styles.btn} onClick={() => handleInject('0.95')}>0.95 Auto-Approve</button>
              <button className={styles.btn} onClick={() => handleInject('0.72')}>0.72 Human Review</button>
              <button className={styles.btn} onClick={() => handleInject('0.45')}>0.45 Reject</button>
              <label className={styles.muted}>Milestone</label>
              <select
                className={styles.btn}
                style={{ fontWeight: 500 }}
                value={amountOption}
                onChange={e => setAmountOption(e.target.value)}
              >
                <option value="700">M2 · $700.00</option>
                <option value="150">Demo · $150.00</option>
              </select>
            </div>
          </div>
        )}
      </section>

      {/* Submit Deliverable Modal */}
      {modalOpen && (
        <div className={styles.modalBackdrop}>
          <form className={styles.modalCard} onSubmit={handleFormSubmit}>
            <h2 className={styles.h2}>Submit Deliverable</h2>
            <label className={styles.label}>
              Milestone
              <input className={styles.input} readOnly value="Milestone 2: Frontend Integration — $700.00 USD" />
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
              Deployed Live URL
              <input
                className={styles.input}
                type="url"
                required
                value={liveUrl}
                onChange={e => setLiveUrl(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Evidence Documentation URL
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
                placeholder="Summarize what was delivered"
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Files (test logs, zip, pdf)
              <input className={styles.input} type="file" multiple style={{ padding: '8px' }} />
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button type="button" className={styles.btn} onClick={() => setModalOpen(false)}>
                Cancel
              </button>
              <button type="submit" className={`${styles.btn} ${styles.btnP}`}>
                Submit Deliverable for AI Verification
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
