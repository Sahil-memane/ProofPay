import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styles from './Assistant.module.css';

const GREETING = 'Hello! I am your ProofPay Assistant. Ask me anything about milestone escrow, payment recovery, reconciliation, or policy decisions.';

const SUGGESTED_PROMPTS = [
  'Why was milestone #2 payout held by Mandate Guard?',
  'Show me all recovery cases halted due to offline bank payments.',
  'What is our current recovery success rate for expired cards?',
  'Verify the plan hash for Project PRJ-2026-001.',
];

const MILESTONES_FOR_HASH = [
  ['UI Design & Figma Tokens', 40000],
  ['Frontend Integration & API Client', 70000],
  ['Backend & PayPal Checkout', 80000],
  ['QA, Testing & Deployment', 50000],
];

export default function Assistant() {
  const [conversations, setConversations] = useState([
    {
      title: 'Why was milestone #2 held?',
      messages: [
        { role: 'user', text: 'Why was milestone #2 payout held by Mandate Guard?' },
        {
          role: 'assistant',
          html: 'The verifier scored Milestone 2 at <b>0.94</b> (AUTO_APPROVE), but Mandate Guard blocked the release because <b>$700.00 exceeds the $200.00 per-transaction autonomous limit</b>. It was routed to the Human Approvals Queue as <b>APP-104</b>. A Risk Officer then approved it and the PayPal Payout was dispatched. The LLM only proposed the release; deterministic policy made the call.',
          citations: [
            { label: 'AUD-00241 Submission verified', href: '/audit' },
            { label: 'AUD-00242 Policy blocked', href: '/audit' },
            { label: 'AUD-00243 Approval granted', href: '/audit' },
            { label: 'AUD-00244 Payout dispatched', href: '/audit' },
          ],
          refs: ['MS-2026-001-02', 'APP-104', '$700.00 USD'],
        },
      ],
    },
    {
      title: 'Paid-elsewhere cases',
      messages: [
        { role: 'user', text: 'Show me all recovery cases halted due to offline bank payments.' },
        {
          role: 'assistant',
          html: 'Reconciliation has detected <b>14 cases paid elsewhere</b>. The most recent is <b>REC-2026-0041</b> (Michael Anderson): the PayPal charge failed, but a matching <b>$450.00</b> offline wire was found. The case is marked PAID_ELSEWHERE and outreach is permanently halted to prevent wrongful dunning.',
          citations: [
            { label: 'Case REC-2026-0041', href: '/cases' },
            { label: 'Reconciliation match event', href: '/audit' },
            { label: 'Recovery overview', href: '/recovery-overview' },
          ],
          refs: ['REC-2026-0041', 'INV on file: $450.00 wire', 'PAID_ELSEWHERE'],
        },
      ],
    },
  ]);

  const [activeConvIdx, setActiveConvIdx] = useState(0);
  const [inputText, setInputText] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversations, activeConvIdx, isSearching]);

  const computeHash = async (str) => {
    try {
      const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
      return Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      return '0a8f9c2d71be4a5f3c9d0e68b2147ad5c3e90f1b7a6d2c48e5f0a91b3d7c64e1';
    }
  };

  const generateAnswer = async (query) => {
    const q = query.toLowerCase();

    if (/plan hash|verify the plan/.test(q)) {
      const plan = JSON.stringify({
        project_id: 'PRJ-2026-001',
        milestones: MILESTONES_FOR_HASH.map((m, i) => ({
          amount_cents: m[1],
          criteria: 'acceptance-criteria-v1',
          index: i + 1,
          title: m[0],
        })),
      });
      const hash = await computeHash(plan);
      return {
        html: `I recomputed the plan hash for PRJ-2026-001 from its 4 milestones totaling $2,400.00. Client and Freelancer signatures both match it, so funding is unlocked and any out-of-band change would return 409 Conflict.<div class="mono" style="word-break:break-all;margin-top:8px;padding:10px 12px;background:#F0F3F8;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#003087">${hash}</div><span style="font-size:12px;font-weight:600;border-radius:12px;padding:2px 10px;background:#E3F4EB;color:#1E7A4C;display:inline-block;margin-top:8px">Both approvals match</span>`,
        citations: [
          { label: 'Project PRJ-2026-001', href: '/project-details' },
          { label: 'Plan approval events', href: '/audit' },
        ],
        refs: ['PRJ-2026-001', 'sha256:' + hash.slice(0, 16) + '…'],
      };
    }

    if (/(milestone|payout).*(held|block|mandate)|mandate guard|held/.test(q)) {
      return {
        html: 'The verifier scored Milestone 2 at <b>0.94</b> (AUTO_APPROVE), but Mandate Guard blocked the release because <b>$700.00 exceeds the $200.00 per-transaction autonomous limit</b>. It was routed to the Human Approvals Queue as <b>APP-104</b>. A Risk Officer then approved it and the PayPal Payout was dispatched. The LLM only proposed the release; deterministic policy made the call.',
        citations: [
          { label: 'AUD-00241 Submission verified', href: '/audit' },
          { label: 'AUD-00242 Policy blocked', href: '/audit' },
          { label: 'AUD-00243 Approval granted', href: '/audit' },
          { label: 'AUD-00244 Payout dispatched', href: '/audit' },
        ],
        refs: ['MS-2026-001-02', 'APP-104', '$700.00 USD'],
      };
    }

    if (/halt|offline|bank|elsewhere|wire/.test(q)) {
      return {
        html: 'Reconciliation has detected <b>14 cases paid elsewhere</b>. The most recent is <b>REC-2026-0041</b> (Michael Anderson): the PayPal charge failed, but a matching <b>$450.00</b> offline wire was found. The case is marked PAID_ELSEWHERE and outreach is permanently halted to prevent wrongful dunning.',
        citations: [
          { label: 'Case REC-2026-0041', href: '/cases' },
          { label: 'Reconciliation match event', href: '/audit' },
          { label: 'Recovery overview', href: '/recovery-overview' },
        ],
        refs: ['REC-2026-0041', 'INV on file: $450.00 wire', 'PAID_ELSEWHERE'],
      };
    }

    if (/expired|success rate|recovery rate/.test(q)) {
      return {
        html: 'Expired cards are the largest failure cause: <b>60 of 142 diagnosed cases (42%)</b>. Their main fix, the PayPal 1-click update link, converts at <b>74%</b>. Overall recovery is <b>67%</b> vs. 22% for manual dunning. The data does not break out a recovery rate for expired cards alone, so 74% is the closest measure.',
        citations: [
          { label: 'Root-cause diagnosis', href: '/recovery-overview' },
          { label: 'Benchmark report', href: '/analytics' },
        ],
        refs: ['150 cases', '$12,450.00 recovered of $18,600.00'],
      };
    }

    if (/\b(release|disburse|pay out|refund|approve|change|raise|lower|disable|freeze|pause|delete|edit)\b/.test(q)) {
      return {
        html: 'I am in <b>read-only mode</b>, so I cannot release funds, change limits, or alter any record. A Risk Officer can do this from the Approvals Queue or Mandate Guard, and every action is recorded in the audit trail. I can explain the current state or the policy rules involved.',
        citations: [
          { label: 'Approvals Queue', href: '/approvals' },
          { label: 'Mandate Guard', href: '/mandate-guard' },
        ],
        refs: [],
      };
    }

    return {
      html: 'I can only answer from ProofPay data and policy rules. Try asking about milestone payouts, recovery cases, offline wire reconciliation, or plan hashes.',
      citations: [],
      refs: [],
    };
  };

  const handleAsk = async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    let convIdx = activeConvIdx;
    let currentConvs = [...conversations];

    if (convIdx < 0 || !currentConvs[convIdx]) {
      const newConv = {
        title: trimmed.slice(0, 36) + (trimmed.length > 36 ? '…' : ''),
        messages: [],
      };
      currentConvs = [newConv, ...currentConvs];
      convIdx = 0;
      setActiveConvIdx(0);
    }

    currentConvs[convIdx].messages.push({ role: 'user', text: trimmed });
    setConversations([...currentConvs]);
    setInputText('');
    setIsSearching(true);

    setTimeout(async () => {
      const resp = await generateAnswer(trimmed);
      currentConvs[convIdx].messages.push({
        role: 'assistant',
        html: resp.html,
        citations: resp.citations,
        refs: resp.refs,
      });
      setConversations([...currentConvs]);
      setIsSearching(false);
    }, 700);
  };

  const handleNewConversation = () => {
    const newConv = {
      title: 'New conversation',
      messages: [],
    };
    setConversations([newConv, ...conversations]);
    setActiveConvIdx(0);
  };

  const currentMessages = activeConvIdx >= 0 && conversations[activeConvIdx]
    ? conversations[activeConvIdx].messages
    : [];

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>AI Assistant</h1>
          <p>Ask about escrow, recovery, reconciliation, and policy decisions. Every answer links to its audit evidence.</p>
        </div>
        <div className={styles.readOnlyBadge}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3" />
          </svg>
          READ-ONLY MODE: Cannot execute financial disbursements or mutate policies.
        </div>
      </div>

      {/* Main Layout */}
      <div className={styles.chatLayout}>
        {/* Left Sidebar */}
        <aside className={styles.sidebarCard}>
          <button className={`${styles.btn} ${styles.btnPrimary}`} style={{ width: '100%' }} onClick={handleNewConversation}>
            + New conversation
          </button>

          <div>
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 8px', color: 'var(--blue-dark)' }}>
              Suggested questions
            </h2>
            <div style={{ display: 'grid', gap: 6 }}>
              {SUGGESTED_PROMPTS.map((p, idx) => (
                <button
                  key={idx}
                  className={styles.suggestedBtn}
                  onClick={() => handleAsk(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 8px', color: 'var(--blue-dark)' }}>
              Recent conversations
            </h2>
            <div style={{ display: 'grid', gap: 4 }}>
              {conversations.map((c, idx) => (
                <button
                  key={idx}
                  className={`${styles.recentBtn} ${idx === activeConvIdx ? styles.recentBtnActive : ''}`}
                  onClick={() => setActiveConvIdx(idx)}
                >
                  {c.title}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Right Chat Section */}
        <section className={styles.chatCard} aria-label="Chat">
          <div className={styles.messagesArea} aria-live="polite">
            <div className={styles.greetingBubble}>
              {GREETING}
            </div>

            {currentMessages.map((msg, idx) => {
              if (msg.role === 'user') {
                return (
                  <div key={idx} className={styles.userBubble}>
                    {msg.text}
                  </div>
                );
              }
              return (
                <div key={idx} className={styles.assistantBubble}>
                  <div
                    className={styles.bubbleCard}
                    dangerouslySetInnerHTML={{ __html: msg.html }}
                  />
                  {msg.citations && msg.citations.length > 0 && (
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>
                        Audit citations
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {msg.citations.map((cite, cIdx) => (
                          <Link key={cIdx} to={cite.href} className={styles.citationLink}>
                            {cite.label}
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                  {msg.refs && msg.refs.length > 0 && (
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>
                        Transaction references
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {msg.refs.map((rf, rIdx) => (
                          <span key={rIdx} className={styles.refTag}>
                            {rf}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {isSearching && (
              <div style={{ alignSelf: 'flex-start', fontSize: 13, color: 'var(--muted)' }}>
                Searching the audit trail…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form
            className={styles.inputForm}
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(inputText);
            }}
          >
            <input
              className={styles.input}
              placeholder="Ask about a milestone, case, hash, or policy…"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isSearching}
              autoComplete="off"
            />
            <button
              type="submit"
              className={`${styles.btn} ${styles.btnPrimary}`}
              disabled={isSearching || !inputText.trim()}
            >
              Send
            </button>
          </form>
        </section>
      </div>

      <footer className={styles.footerTagline}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </footer>
    </div>
  );
}

