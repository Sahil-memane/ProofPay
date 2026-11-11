import { useState } from 'react';
import { toast } from '../components/ui/Toast';
import styles from './Help.module.css';

const SECTIONS = [
  { id: 'start', title: '1. Getting Started' },
  { id: 'escrow', title: '2. Freelance Escrow' },
  { id: 'verification', title: '3. AI Verification & HITL' },
  { id: 'recovery', title: '4. Revenue Recovery' },
  { id: 'recon', title: '5. Reconciliation Engine' },
  { id: 'mandate', title: '6. Mandate Guard' },
  { id: 'audit', title: '7. Cryptographic Auditing' },
  { id: 'faq', title: '8. Frequently Asked Questions' },
  { id: 'support', title: '9. Contact Support' },
];

export default function Help() {
  const [activeSec, setActiveSec] = useState('start');
  const [searchQuery, setSearchQuery] = useState('');
  const [ticketSubject, setTicketSubject] = useState('');
  const [ticketMessage, setTicketMessage] = useState('');

  const scrollToSection = (id) => {
    setActiveSec(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSupportSubmit = (e) => {
    e.preventDefault();
    if (!ticketSubject || !ticketMessage) return;
    toast.success('Support ticket submitted. Ticket ID #SUP-8821 created.');
    setTicketSubject('');
    setTicketMessage('');
  };

  return (
    <div className={styles.container}>
      {/* Top Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>Help &amp; Support</h1>
          <p>Guides for escrow, recovery, and governance, plus a direct line to the ProofPay support team.</p>
        </div>
        <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={() => scrollToSection('support')}>
          Contact Support
        </button>
      </div>

      {/* Search KB */}
      <section className={styles.searchCard}>
        <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500 }}>
          Search the knowledge base
        </label>
        <input
          className={styles.input}
          placeholder="e.g. plan hash, quiet hours, $200 limit, payout, webhook…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </section>

      {/* Main Layout */}
      <div className={styles.layout}>
        {/* Sticky Sidebar TOC */}
        <nav className={styles.tocCard} aria-label="Help sections">
          {SECTIONS.map(s => (
            <button
              key={s.id}
              className={`${styles.tocBtn} ${activeSec === s.id ? styles.tocBtnActive : ''}`}
              onClick={() => scrollToSection(s.id)}
            >
              {s.title}
            </button>
          ))}
        </nav>

        {/* Content Column */}
        <div className={styles.contentCol}>
          {/* Section 1: Getting Started */}
          <section id="start" className={styles.secCard}>
            <h2 className={styles.secTitle}>1. Getting Started</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              ProofPay has two engines, <b>Escrow PREVENT</b> and <b>Revenue RECOVER</b>, that share one deterministic trust layer.
            </p>
            <div className={styles.twoCols}>
              <div className={styles.stepItem}>
                <span className={styles.stepNum}>1</span>
                <div>
                  <div style={{ fontWeight: 600 }}>Pick your persona</div>
                  <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                    Client, Freelancer, Merchant, or Risk Officer. Each sees only the actions it is allowed to take.
                  </div>
                </div>
              </div>
              <div className={styles.stepItem}>
                <span className={styles.stepNum}>2</span>
                <div>
                  <div style={{ fontWeight: 600 }}>Start a flow</div>
                  <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                    Create an escrow project, or ingest failed charges and overdue invoices for recovery.
                  </div>
                </div>
              </div>
              <div className={styles.stepItem}>
                <span className={styles.stepNum}>3</span>
                <div>
                  <div style={{ fontWeight: 600 }}>Watch the guardrails</div>
                  <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                    Mandate Guard shows every allow, block, and escalation. Large payouts go to the Approvals Queue.
                  </div>
                </div>
              </div>
              <div className={styles.stepItem}>
                <span className={styles.stepNum}>4</span>
                <div>
                  <div style={{ fontWeight: 600 }}>Verify the proof</div>
                  <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                    Every state change has a SHA-256 hash link in the Audit Trail.
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Freelance Escrow */}
          <section id="escrow" className={styles.secCard}>
            <h2 className={styles.secTitle}>2. Freelance Escrow</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              Contract setup requires mutual consent through cryptographic dual approvals before funds are collected.
            </p>
            <div className={styles.details}>
              <div className={styles.summary}>Dual-Approved Plan Hash</div>
              <p className={styles.detailsText}>
                The plan hash is the SHA-256 digest of canonical milestone metadata (titles, amounts, criteria). Both client and freelancer must approve the exact hash. If either party alters the scope, the hash diverges and PayPal escrow funding is blocked with HTTP 409.
              </p>
            </div>
            <div className={styles.details}>
              <div className={styles.summary}>PayPal Escrow Funding</div>
              <p className={styles.detailsText}>
                Clients fund the total contract balance via PayPal Orders API v2. ProofPay captures the order and maintains milestone custody until acceptance criteria are satisfied.
              </p>
            </div>
          </section>

          {/* Section 3: AI Verification */}
          <section id="verification" className={styles.secCard}>
            <h2 className={styles.secTitle}>3. AI Verification &amp; Human-in-the-Loop</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              Submissions are inspected automatically by LangGraph AI Verifiers before any disbursement proposal is generated.
            </p>
            <div className={styles.callout}>
              <b>Deterministic Gating:</b> The AI Verifier proposes a confidence score (0.00 to 1.00) based on code diffs, CI build logs, and staging endpoints. However, Mandate Guard enforces a strict $200 per-transaction cap. Any payout over $200 is automatically blocked and escalated to the Human Approvals Queue.
            </div>
          </section>

          {/* Section 4: Revenue Recovery */}
          <section id="recovery" className={styles.secCard}>
            <h2 className={styles.secTitle}>4. Revenue Recovery</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              Autonomous 3-stage contact ladder for failed subscriptions and overdue invoices.
            </p>
            <div className={styles.details}>
              <div className={styles.summary}>Quiet Hours Compliance</div>
              <p className={styles.detailsText}>
                Under TCPA regulations and merchant policy, no automated emails or SMS outreach may be sent between 21:00 and 08:00 in the customer&apos;s local timezone. Scheduled attempts entering this window are held in `QUIET_HOURS_PAUSED` status until morning.
              </p>
            </div>
            <div className={styles.details}>
              <div className={styles.summary}>Root-Cause Diagnostics</div>
              <p className={styles.detailsText}>
                Payment failures are classified into EXPIRED_CARD, INSUFFICIENT_FUNDS, BANK_AUTH_FAILED, or GATEWAY_ERROR. Each path receives a tailored action: 1-click update links for expired cards, or smart payday-synchronized retries for insufficient funds.
              </p>
            </div>
          </section>

          {/* Section 5: Reconciliation */}
          <section id="recon" className={styles.secCard}>
            <h2 className={styles.secTitle}>5. Reconciliation Engine</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              Prevents wrongful dunning by reconciling PayPal gateway logs with merchant ERP invoices and bank statements.
            </p>
            <div className={styles.callout}>
              If a customer pays an overdue invoice via offline bank wire or ACH credit, ProofPay&apos;s 3-way fuzzy matcher detects the deposit, flags the record as `PAID_ELSEWHERE`, and permanently halts recovery outreach.
            </div>
          </section>

          {/* Section 6: Mandate Guard */}
          <section id="mandate" className={styles.secCard}>
            <h2 className={styles.secTitle}>6. Mandate Guard</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              Zero-trust policy engine that inspects every action before PayPal execution.
            </p>
            <div className={styles.details}>
              <div className={styles.summary}>Core Policies Enforced</div>
              <p className={styles.detailsText}>
                1. Single transaction cap: $200.00 max for autonomous release.<br />
                2. Daily volume cap: $5,000.00 max total disbursements in 24 hours.<br />
                3. Dual signature match: plan hash must match both client and freelancer keys.<br />
                4. Recipient verification: payout email must be verified on PayPal.<br />
                5. Dispute circuit breaker: freezes escrow immediately upon receiving `CUSTOMER.DISPUTE.CREATED`.
              </p>
            </div>
          </section>

          {/* Section 7: Cryptographic Auditing */}
          <section id="audit" className={styles.secCard}>
            <h2 className={styles.secTitle}>7. Cryptographic Auditing</h2>
            <p style={{ margin: '4px 0 12px', fontSize: 13, color: 'var(--muted)' }}>
              Every decision, verification score, approval, and PayPal transaction is linked into a SHA-256 hash chain.
            </p>
            <div className={styles.details}>
              <div className={styles.summary}>Chain Verification</div>
              <p className={styles.detailsText}>
                Any evaluator can recalculate the hash chain directly in the browser via `crypto.subtle.digest`. If any record is tampered with, the SHA-256 sequence breaks and displays an instant alert.
              </p>
            </div>
          </section>

          {/* Section 8: FAQ */}
          <section id="faq" className={styles.secCard}>
            <h2 className={styles.secTitle}>8. Frequently Asked Questions</h2>
            <div className={styles.details}>
              <div className={styles.summary}>Can an AI agent directly release a $1,000 milestone?</div>
              <p className={styles.detailsText}>
                No. Mandate Guard enforces a hard $200 limit on autonomous payouts. Any milestone release above $200 is automatically blocked and requires approval from a human Risk Officer in the Approvals Queue.
              </p>
            </div>
            <div className={styles.details}>
              <div className={styles.summary}>What happens when a dispute is filed on PayPal?</div>
              <p className={styles.detailsText}>
                PayPal delivers a `CUSTOMER.DISPUTE.CREATED` webhook. Mandate Guard instantly locks the milestone escrow, freezes all scheduled payouts, and opens an Evidence Pack generator for dispute defense.
              </p>
            </div>
          </section>

          {/* Section 9: Contact Support */}
          <section id="support" className={styles.secCard}>
            <h2 className={styles.secTitle}>9. Contact Support</h2>
            <p style={{ margin: '4px 0 16px', fontSize: 13, color: 'var(--muted)' }}>
              Submit an issue directly to the ProofPay developer and security operations desk.
            </p>
            <form onSubmit={handleSupportSubmit} style={{ display: 'grid', gap: 14, maxWidth: 600 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500 }}>Subject</label>
                <input
                  className={styles.input}
                  placeholder="e.g. Question about milestone escrow release #MS-002"
                  value={ticketSubject}
                  onChange={(e) => setTicketSubject(e.target.value)}
                  required
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500 }}>Message</label>
                <textarea
                  className={styles.input}
                  style={{ height: 120, padding: 12, resize: 'vertical' }}
                  placeholder="Describe your issue or question in detail…"
                  value={ticketMessage}
                  onChange={(e) => setTicketMessage(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`} style={{ justifySelf: 'start' }}>
                Submit Support Ticket
              </button>
            </form>
          </section>
        </div>
      </div>

      <footer className={styles.footerTagline}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </footer>
    </div>
  );
}
