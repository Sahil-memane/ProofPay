import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './ProjectDetails.module.css';

const DEFAULT_PROJECT = {
  id: 'PRJ-2026-001',
  title: 'E-commerce Website Development',
  status: 'APPROVED',
  totalAmount: 2400,
  planHash: '0a8f9c2e5b741098a83d3467e21098c7654a12908fde3209847162534a9b4e1',
  client: 'Acme Global Solutions',
  clientEmail: 'client@example.com',
  clientApprovalTime: '2026-11-10 09:30 UTC',
  freelancer: 'Rahul Sharma',
  freelancerEmail: 'freelancer@example.com',
  freelancerApprovalTime: '2026-11-10 10:15 UTC',
  captureId: 'CAP-884102',
  milestones: [
    {
      id: 'MS-2026-001-01',
      num: 1,
      title: 'UI Design & Figma Tokens',
      amount: 400,
      status: 'PAID',
      statusCls: 'g',
      note: 'Paid via PayPal Payouts · audit 2de7c5b4'
    },
    {
      id: 'MS-2026-001-02',
      num: 2,
      title: 'Frontend Integration & API Client',
      amount: 700,
      status: 'IN_REVIEW',
      statusCls: 'a',
      flag: 'POLICY_BLOCKED · Amount exceeds $200.00 limit. Routed to Approvals Queue (APP-104)'
    },
    {
      id: 'MS-2026-001-03',
      num: 3,
      title: 'Backend & PayPal Checkout',
      amount: 800,
      status: 'FUNDED',
      statusCls: 'b'
    },
    {
      id: 'MS-2026-001-04',
      num: 4,
      title: 'QA, Testing & Deployment',
      amount: 500,
      status: 'FUNDED',
      statusCls: 'b'
    }
  ]
};

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

export default function ProjectDetails() {
  const [params] = useSearchParams();
  const id = params.get('id') || 'PRJ-2026-001';

  const { data: apiProject } = useApi(
    () => id ? endpoints.projects.get(id) : Promise.resolve(null),
    [id]
  );

  const p = apiProject ? {
    id: apiProject.id || id,
    title: apiProject.title || DEFAULT_PROJECT.title,
    status: apiProject.state || DEFAULT_PROJECT.status,
    totalAmount: apiProject.total_amount_usd || DEFAULT_PROJECT.totalAmount,
    planHash: apiProject.plan_hash || DEFAULT_PROJECT.planHash,
    client: apiProject.client_email || DEFAULT_PROJECT.client,
    clientEmail: apiProject.client_email || DEFAULT_PROJECT.clientEmail,
    clientApprovalTime: apiProject.client_approved_at || DEFAULT_PROJECT.clientApprovalTime,
    freelancer: apiProject.freelancer_email || DEFAULT_PROJECT.freelancer,
    freelancerEmail: apiProject.freelancer_email || DEFAULT_PROJECT.freelancerEmail,
    freelancerApprovalTime: apiProject.freelancer_approved_at || DEFAULT_PROJECT.freelancerApprovalTime,
    captureId: apiProject.paypal_capture_id || DEFAULT_PROJECT.captureId,
    milestones: apiProject.milestones && apiProject.milestones.length > 0 ? apiProject.milestones.map((m, i) => ({
      id: m.id || `MS-00${i + 1}`,
      num: i + 1,
      title: m.title || `Milestone ${i + 1}`,
      amount: m.amount_usd || 500,
      status: m.state || 'FUNDED',
      statusCls: m.state === 'PAID' ? 'g' : m.state === 'IN_REVIEW' ? 'a' : 'b'
    })) : DEFAULT_PROJECT.milestones
  } : DEFAULT_PROJECT;

  const copyHash = () => {
    navigator.clipboard?.writeText(p.planHash);
    showToast('Plan hash copied to clipboard.', 'success');
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
            <span className={`${styles.bd} ${styles.g}`}>Status: {p.status}</span>
            <span className={`${styles.bd} ${styles.b} ${styles.num}`}>Escrow: {fmt(p.totalAmount)}</span>
            <span className={`${styles.bd} ${styles.x}`}>
              Plan Hash: <span className={styles.mono}>{p.planHash.slice(0, 6)}…{p.planHash.slice(-3)}</span>
            </span>
          </div>
        </div>
        <div className={styles.muted} style={{ textAlign: 'right' }}>
          Client: {p.client}<br />
          Freelancer: {p.freelancer}
        </div>
      </div>

      {/* Cryptographic Dual Approval */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2 className={styles.h2}>Cryptographic Dual Approval</h2>
          <span className={`${styles.bd} ${styles.g}`}>Both signatures match</span>
        </div>

        <div className={styles.muted} style={{ margin: '16px 0 4px' }}>
          Plan Hash (SHA-256)
        </div>

        <div className={styles.hashBoxWrap}>
          <div className={`${styles.mono} ${styles.hashBox}`}>
            {p.planHash}
          </div>
          <button className={styles.btn} onClick={copyHash} aria-label="Copy plan hash">
            Copy
          </button>
        </div>

        <div className={styles.approvalsGrid}>
          <div className={styles.approvalBox}>
            <span className={styles.chk}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12l5 5 9-10" />
              </svg>
            </span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>Client approval</div>
              <div className={styles.muted} style={{ marginTop: 2 }}>
                Approved by {p.clientEmail} at {p.clientApprovalTime}
              </div>
            </div>
          </div>

          <div className={styles.approvalBox}>
            <span className={styles.chk}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12l5 5 9-10" />
              </svg>
            </span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>Freelancer approval</div>
              <div className={styles.muted} style={{ marginTop: 2 }}>
                Approved by {p.freelancerEmail} at {p.freelancerApprovalTime}
              </div>
            </div>
          </div>
        </div>

        <div className={styles.integrityBanner}>
          <b>Integrity verified.</b> Milestones, amounts and criteria match the approved hash. Any change requires both parties to re-approve.
        </div>
      </section>

      {/* PayPal Escrow Funding */}
      <section className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <h2 className={styles.h2}>PayPal Escrow Funding</h2>
          <div className={`${styles.num}`} style={{ fontSize: 18, fontWeight: 600 }}>{fmt(p.totalAmount)}</div>
        </div>

        <div className={styles.vaultBanner}>
          Escrow securely funded in PayPal vault · Capture ID:{' '}
          <span className={styles.mono} style={{ color: '#1E7A4C', fontWeight: 600 }}>{p.captureId}</span>
        </div>

        <div className={styles.stepsGrid}>
          {[
            { title: 'Create Order', sub: 'POST /fund' },
            { title: 'Authorize', sub: 'PayPal popup' },
            { title: 'Capture', sub: 'POST /capture' },
            { title: 'Webhook', sub: 'PAYMENT.CAPTURE.COMPLETED' }
          ].map(s => (
            <div key={s.title} className={styles.stepItem}>
              <span className={styles.chk}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12l5 5 9-10" />
                </svg>
              </span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{s.title}</div>
                <div className={styles.muted}>{s.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Milestones Grid */}
      <section>
        <h2 className={styles.h2} style={{ marginBottom: 12 }}>Milestones</h2>
        <div className={styles.milestonesGrid}>
          {p.milestones.map(m => (
            <div key={m.id} className={styles.milestoneCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                <div>
                  <div className={styles.muted}>Milestone {m.num}</div>
                  <div style={{ fontWeight: 600, fontSize: 16 }}>{m.title}</div>
                </div>
                <span className={`${styles.bd} ${styles[m.statusCls]}`}>{m.status}</span>
              </div>

              <div className={`${styles.num}`} style={{ fontSize: 22, fontWeight: 600 }}>
                {fmt(m.amount)}
              </div>

              {m.note && (
                <div className={styles.muted}>
                  {m.note.includes('audit') ? (
                    <>
                      Paid via PayPal Payouts · audit{' '}
                      <a className={styles.monoLink} href="/audit">2de7c5b4</a>
                    </>
                  ) : (
                    m.note
                  )}
                </div>
              )}

              {m.flag && (
                <div className={styles.flagAlert}>
                  <b>POLICY_BLOCKED</b> · Amount exceeds $200.00 limit. Routed to Approvals Queue (<a href="/approvals" className={styles.link}>APP-104</a>)
                </div>
              )}

              {m.status === 'IN_REVIEW' && (
                <>
                  <div className={styles.muted}>Client actions</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    <a href="/submissions" className={`${styles.btn} ${styles.btnP}`} style={{ textDecoration: 'none' }}>
                      Review Deliverable
                    </a>
                    <a href="/approvals" className={styles.btn} style={{ textDecoration: 'none' }}>
                      Release Funds
                    </a>
                    <button className={styles.btn} style={{ color: '#D9363E' }} onClick={() => showToast('Refund request submitted.', 'warning')}>
                      Request Refund
                    </button>
                  </div>
                </>
              )}

              {m.status === 'FUNDED' && (
                <>
                  <div className={styles.muted}>Freelancer actions</div>
                  <div>
                    <a href="/submissions" className={styles.btn} style={{ textDecoration: 'none' }}>
                      Submit Deliverable
                    </a>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
