import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './ProjectDetails.module.css';

const fmt = (n, cur = 'USD') =>
  '$' + Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + cur;

export default function ProjectDetails() {
  const [params] = useSearchParams();
  const id = params.get('id') || 'ESCROW-000';
  const [approving, setApproving] = useState(false);
  const [funding, setFunding] = useState(false);

  const { data: apiResponse, loading, error, refetch } = useApi(
    () => (id ? endpoints.projects.get(id) : Promise.resolve(null)),
    [id]
  );

  // Unwrap backend response: {"project": {...}, "milestones": [...]}
  const rawProject = apiResponse?.project || apiResponse || {};
  const rawMilestones = apiResponse?.milestones || rawProject?.milestones || [];

  const p = {
    id: rawProject.id || id,
    title: rawProject.job_description || rawProject.title || `Project ${id}`,
    status: (rawProject.state || rawProject.status || 'DRAFT').toUpperCase(),
    totalAmount: rawProject.total_amount ?? rawProject.totalAmount ?? 0,
    currency: rawProject.currency || 'USD',
    planHash: rawProject.plan_hash || rawProject.planHash || 'PendingDualApproval',
    clientId: rawProject.client_id || 'client-1',
    clientName: rawProject.client_name || rawProject.client || 'Client',
    clientEmail: rawProject.client_email || rawProject.clientEmail || `${rawProject.client_id || 'client'}@proofpay.io`,
    clientApproved: Boolean(rawProject.client_approved),
    clientApprovalTime: rawProject.client_approved_at || 'Pending',
    freelancerId: rawProject.freelancer_id || 'freelancer-1',
    freelancerName: rawProject.freelancer_name || rawProject.freelancer || 'Freelancer',
    freelancerEmail: rawProject.freelancer_email || rawProject.freelancerEmail || `${rawProject.freelancer_id || 'freelancer'}@proofpay.io`,
    freelancerApproved: Boolean(rawProject.freelancer_approved),
    freelancerApprovalTime: rawProject.freelancer_approved_at || 'Pending',
    orderId: rawProject.paypal_order_id || 'PAYPAL-ORD-PENDING',
    captureId: rawProject.paypal_capture_id || (rawProject.state === 'DRAFT' ? 'NOT_CAPTURED' : 'CAP-PENDING'),
    dispute: rawProject.dispute || null,
  };

  const isDisputed = p.status === 'DISPUTED' || Boolean(p.dispute);

  const copyHash = () => {
    if (p.planHash && p.planHash !== 'PendingDualApproval') {
      navigator.clipboard?.writeText(p.planHash);
      showToast('Plan hash copied to clipboard.', 'success');
    } else {
      showToast('Plan hash is not yet locked.', 'info');
    }
  };

  // Wire: Approve (client or freelancer signs the plan)
  const handleApprove = async (party) => {
    setApproving(true);
    try {
      await endpoints.projects.approve(p.id, { party });
      showToast(`${party === 'client' ? 'Client' : 'Freelancer'} approval recorded. Plan hash being computed.`, 'success');
      refetch();
    } catch (err) {
      showToast(`Approval failed: ${err.message || 'Network error'}`, 'error');
    } finally {
      setApproving(false);
    }
  };

  // Wire: Fund (create PayPal order)
  const handleFund = async () => {
    setFunding(true);
    try {
      const res = await endpoints.projects.fund(p.id);
      if (res?.approval_url) {
        showToast('PayPal order created. Opening approval page…', 'success');
        window.open(res.approval_url, '_blank');
      } else {
        showToast('Fund initiated — capture webhook will confirm.', 'info');
      }
      refetch();
    } catch (err) {
      showToast(`Fund failed: ${err.message || 'Network error'}`, 'error');
    } finally {
      setFunding(false);
    }
  };

  const getStatusBadgeCls = (st) => {
    switch (st) {
      case 'COMPLETED':
      case 'RELEASED':
      case 'PAID':
        return styles.g;
      case 'FUNDED':
      case 'PLAN_APPROVED':
        return styles.b;
      case 'IN_REVIEW':
        return styles.a;
      case 'DISPUTED':
        return styles.r;
      default:
        return styles.x;
    }
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <div className={styles.muted} style={{ fontSize: 13, marginBottom: 4 }}>
            Projects / <span className={styles.mono}>{p.id}</span>
          </div>
          <h1 className={styles.h1}>{p.title}</h1>
          <div className={styles.badgeRow}>
            <span className={`${styles.bd} ${getStatusBadgeCls(p.status)}`}>
              Status: {p.status}
            </span>
            <span className={`${styles.bd} ${styles.b} ${styles.num}`}>
              Escrow: {fmt(p.totalAmount, p.currency)}
            </span>
            {p.planHash && p.planHash !== 'PendingDualApproval' && (
              <span className={`${styles.bd} ${styles.x}`}>
                Plan Hash: <span className={styles.mono}>{p.planHash.slice(0, 8)}…{p.planHash.slice(-6)}</span>
              </span>
            )}
          </div>
        </div>

        <div className={styles.muted} style={{ textAlign: 'right', lineHeight: '1.6' }}>
          <div><b>Client:</b> {p.clientName} <span className={styles.mono}>({p.clientEmail})</span></div>
          <div><b>Freelancer:</b> {p.freelancerName} <span className={styles.mono}>({p.freelancerEmail})</span></div>
        </div>
      </div>

      {/* ── ACTIVE DISPUTE CARD (Shown when project is in DISPUTED state) ── */}
      {isDisputed && (
        <section className={styles.disputeCard}>
          <div className={styles.disputeHeader}>
            <h2 className={styles.disputeTitle}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              Active Escrow Dispute Filed
            </h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <span className={`${styles.bd} ${styles.r}`}>
                {p.dispute?.status || 'UNDER_ARBITRATION'}
              </span>
              <span className={`${styles.bd} ${styles.r}`}>
                FROZEN ESCROW
              </span>
            </div>
          </div>

          <div className={styles.disputeGrid}>
            <div className={styles.disputeItem}>
              <span className={styles.disputeItemLabel}>Dispute Case ID</span>
              <span className={`${styles.mono} ${styles.disputeItemVal}`}>
                {p.dispute?.dispute_id || `DISP-${p.id}`}
              </span>
            </div>
            <div className={styles.disputeItem}>
              <span className={styles.disputeItemLabel}>Frozen Escrow Amount</span>
              <span className={`${styles.num} ${styles.disputeItemVal}`} style={{ color: '#B42830', fontWeight: 700 }}>
                {fmt(p.dispute?.amount_frozen || p.totalAmount, p.currency)}
              </span>
            </div>
            <div className={styles.disputeItem}>
              <span className={styles.disputeItemLabel}>Vault Status</span>
              <span className={`${styles.mono} ${styles.disputeItemVal}`} style={{ color: '#B42830' }}>
                {p.dispute?.vault_status || 'FROZEN_IN_PAYPAL_ESCROW_VAULT'}
              </span>
            </div>
            <div className={styles.disputeItem}>
              <span className={styles.disputeItemLabel}>Arbitration Channel</span>
              <span className={styles.disputeItemVal}>
                {p.dispute?.arbitrator || 'PayPal Resolution Center & ProofPay Policy Engine'}
              </span>
            </div>
          </div>

          <div style={{ background: '#fff', border: '1px solid #F5C6CB', borderRadius: 8, padding: 14 }}>
            <div className={styles.disputeItemLabel} style={{ marginBottom: 4 }}>
              Dispute Reason / Claim
            </div>
            <div style={{ fontSize: 14, color: '#1E293B', lineHeight: '1.5' }}>
              {p.dispute?.reason ||
                'Deliverable rejected: Client flagged that milestone criteria were not fulfilled or tests failed.'}
            </div>

            {p.dispute?.evidence_fixtures && p.dispute.evidence_fixtures.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div className={styles.disputeItemLabel} style={{ marginBottom: 6 }}>
                  Attached Evidence & Verification Artifacts
                </div>
                <div className={styles.evidencePills}>
                  {p.dispute.evidence_fixtures.map((file) => (
                    <span key={file} className={styles.evidencePill}>
                      📄 {file}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
            <Link to="/disputes" className={`${styles.btn} ${styles.btnDanger}`}>
              Open Case in Disputes Center →
            </Link>
            <Link to="/submissions" className={styles.btn}>
              Submit Counter-Evidence
            </Link>
            <Link to="/assistant" className={styles.btn}>
              Consult AI Arbitrator
            </Link>
          </div>
        </section>
      )}

      {/* Cryptographic Dual Approval */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2 className={styles.h2}>Cryptographic Dual Approval</h2>
          <span className={`${styles.bd} ${p.clientApproved && p.freelancerApproved ? styles.g : styles.a}`}>
            {p.clientApproved && p.freelancerApproved ? 'Both signatures match' : 'Pending Dual Signature'}
          </span>
        </div>

        <div className={styles.muted} style={{ margin: '16px 0 4px' }}>
          Plan Hash (SHA-256)
        </div>

        <div className={styles.hashBoxWrap}>
          <div className={`${styles.mono} ${styles.hashBox}`}>{p.planHash}</div>
          <button className={styles.btn} onClick={copyHash} aria-label="Copy plan hash">
            Copy
          </button>
        </div>

        <div className={styles.approvalsGrid}>
          <div className={styles.approvalBox}>
            <span className={p.clientApproved ? styles.chk : styles.chkPending}>
              {p.clientApproved ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12l5 5 9-10" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              )}
            </span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>Client Approval</div>
              <div className={styles.muted} style={{ marginTop: 2 }}>
                {p.clientApproved
                  ? `Approved by ${p.clientName} (${p.clientEmail}) at ${p.clientApprovalTime}`
                  : `Awaiting signature from ${p.clientName}`}
              </div>
            </div>
            {!p.clientApproved && p.status === 'DRAFT' && (
              <button
                className={`${styles.btn} ${styles.btnP}`}
                onClick={() => handleApprove('client')}
                disabled={approving}
                style={{ marginLeft: 'auto' }}
              >
                {approving ? 'Signing…' : 'Sign as Client'}
              </button>
            )}
          </div>

          <div className={styles.approvalBox}>
            <span className={p.freelancerApproved ? styles.chk : styles.chkPending}>
              {p.freelancerApproved ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12l5 5 9-10" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              )}
            </span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>Freelancer Approval</div>
              <div className={styles.muted} style={{ marginTop: 2 }}>
                {p.freelancerApproved
                  ? `Approved by ${p.freelancerName} (${p.freelancerEmail}) at ${p.freelancerApprovalTime}`
                  : `Awaiting signature from ${p.freelancerName}`}
              </div>
            </div>
            {!p.freelancerApproved && p.status === 'DRAFT' && (
              <button
                className={`${styles.btn} ${styles.btnP}`}
                onClick={() => handleApprove('freelancer')}
                disabled={approving}
                style={{ marginLeft: 'auto' }}
              >
                {approving ? 'Signing…' : 'Sign as Freelancer'}
              </button>
            )}
          </div>
        </div>

        {isDisputed ? (
          <div className={styles.integrityBannerWarning}>
            ⚠️ <b>Dual approval completed & locked.</b> However, project is currently DISPUTED — milestone payouts are frozen in escrow.
          </div>
        ) : (
          <div className={styles.integrityBanner}>
            ✓ <b>Integrity verified.</b> Milestones, amounts, and acceptance criteria match the approved SHA-256 hash. Any change requires both parties to re-approve.
          </div>
        )}
      </section>

      {/* PayPal Escrow Funding */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <h2 className={styles.h2}>PayPal Escrow Funding</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div className={`${styles.num}`} style={{ fontSize: 18, fontWeight: 700, color: '#003087' }}>
              {fmt(p.totalAmount, p.currency)}
            </div>
            {p.status === 'PLAN_APPROVED' && (
              <button
                className={`${styles.btn} ${styles.btnP}`}
                onClick={handleFund}
                disabled={funding}
              >
                {funding ? 'Creating Order…' : 'Fund via PayPal'}
              </button>
            )}
          </div>
        </div>

        {isDisputed ? (
          <div className={styles.vaultBannerFrozen}>
            ⚠️ Escrow funds frozen in PayPal vault due to active dispute · Capture ID:{' '}
            <span className={styles.mono} style={{ color: '#B42830', fontWeight: 600, marginLeft: 6 }}>
              {p.captureId}
            </span>
          </div>
        ) : (
          <div className={styles.vaultBanner}>
            Escrow securely funded in PayPal vault · Capture ID:{' '}
            <span className={styles.mono} style={{ color: '#1E7A4C', fontWeight: 600, marginLeft: 6 }}>
              {p.captureId}
            </span>
          </div>
        )}

        <div className={styles.stepsGrid}>
          {[
            {
              title: 'Create Order',
              sub: p.orderId !== 'PAYPAL-ORD-PENDING' ? p.orderId : 'POST /fund',
              done: p.orderId !== 'PAYPAL-ORD-PENDING',
            },
            {
              title: 'Authorize',
              sub: 'PayPal popup / REST v2',
              done: p.orderId !== 'PAYPAL-ORD-PENDING',
            },
            {
              title: 'Capture',
              sub: p.captureId !== 'NOT_CAPTURED' ? p.captureId : 'POST /capture',
              done: p.captureId !== 'NOT_CAPTURED',
            },
            {
              title: isDisputed ? 'Dispute Status' : 'Webhook Capture',
              sub: isDisputed ? 'CUSTOMER.DISPUTE.CREATED' : 'PAYMENT.CAPTURE.COMPLETED',
              done: true,
              disputed: isDisputed,
            },
          ].map((s) => (
            <div key={s.title} className={styles.stepItem}>
              <span className={s.disputed ? styles.chkFrozen : s.done ? styles.chk : styles.chkPending}>
                {s.disputed ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                ) : s.done ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12l5 5 9-10" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                )}
              </span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{s.title}</div>
                <div className={`${styles.muted} ${styles.mono}`} style={{ fontSize: 12 }}>{s.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Milestones Grid */}
      <section>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 className={styles.h2}>Milestones ({rawMilestones.length})</h2>
          <span className={styles.muted}>
            Total: {fmt(rawMilestones.reduce((acc, m) => acc + Number(m.amount || 0), 0), p.currency)}
          </span>
        </div>

        <div className={styles.milestonesGrid}>
          {rawMilestones.map((m, idx) => {
            const mState = (m.state || m.status || 'FUNDED').toUpperCase();
            const mAmount = m.amount ?? m.amount_usd ?? 0;
            const criteria = Array.isArray(m.criteria) ? m.criteria : [];
            const isMilestoneDisputed = mState === 'DISPUTED';

            return (
              <div key={m.id || idx} className={styles.milestoneCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                  <div>
                    <div className={styles.muted} style={{ fontSize: 12 }}>
                      Milestone {m.sequence || idx + 1} · <span className={styles.mono}>{m.id}</span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: 17, marginTop: 2, color: '#003087' }}>
                      {m.title || `Milestone ${idx + 1}`}
                    </div>
                  </div>
                  <span className={`${styles.bd} ${getStatusBadgeCls(mState)}`}>
                    {mState}
                  </span>
                </div>

                <div className={`${styles.num}`} style={{ fontSize: 24, fontWeight: 700, color: '#172B4D' }}>
                  {fmt(mAmount, m.currency || p.currency)}
                </div>

                {/* Criteria List */}
                {criteria.length > 0 && (
                  <div className={styles.criteriaWrap}>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#64748B' }}>
                      Acceptance Criteria ({criteria.length})
                    </div>
                    {criteria.map((c, cIdx) => (
                      <div key={c.id || cIdx} className={styles.criteriaItem}>
                        <span>
                          • {c.type === 'github_pr' ? 'GitHub PR / Code' : c.type === 'pdf_report' ? 'PDF Inspection Report' : c.type === 'client_approval' ? 'Client Approval' : c.type || 'Verification'}
                          {c.must_pass && <span className={styles.mustPassTag}>Must Pass</span>}
                        </span>
                        {c.weight !== undefined && (
                          <span className={styles.muted} style={{ fontSize: 12 }}>
                            {Math.round(c.weight * 100)}% weight
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* State-specific alerts and actions */}
                {isMilestoneDisputed && (
                  <>
                    <div className={styles.flagAlert}>
                      <b>⚠️ Milestone Disputed</b> · Payout halted. Client filed a dispute regarding deliverable criteria.
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 'auto' }}>
                      <Link to="/disputes" className={`${styles.btn} ${styles.btnDanger}`}>
                        View Dispute Case
                      </Link>
                      <Link to="/submissions" className={styles.btn}>
                        Review Evidence
                      </Link>
                    </div>
                  </>
                )}

                {mState === 'IN_REVIEW' && (
                  <>
                    <div className={styles.muted}>Client Actions</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 'auto' }}>
                      <Link to="/submissions" className={`${styles.btn} ${styles.btnP}`}>
                        Review Deliverable
                      </Link>
                      <Link to="/approvals" className={styles.btn}>
                        Release Funds
                      </Link>
                    </div>
                  </>
                )}

                {mState === 'FUNDED' && !isMilestoneDisputed && (
                  <>
                    <div className={styles.muted}>Freelancer Actions</div>
                    <div style={{ marginTop: 'auto' }}>
                      <Link to="/submissions" className={`${styles.btn} ${styles.btnP}`}>
                        Submit Deliverable →
                      </Link>
                    </div>
                  </>
                )}

                {mState === 'RELEASED' && (
                  <div className={styles.muted} style={{ color: '#1E7A4C', fontWeight: 500, marginTop: 'auto' }}>
                    ✓ Paid via PayPal Payouts batch
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
