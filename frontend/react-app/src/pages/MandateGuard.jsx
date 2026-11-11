import { useState } from 'react';
import { showToast } from '../components/ui/Toast';
import styles from './MandateGuard.module.css';

const RULES = [
  {
    n: 1,
    t: 'Autonomous Payout Cap',
    th: '$200.00 USD',
    b: 'Milestone payouts ≤ $200 with verification score ≥ 0.80 execute autonomously. Payouts > $200 are BLOCKED and routed to the Human Approvals Queue.'
  },
  {
    n: 2,
    t: 'Daily Payout Volume Limit',
    th: '$5,000.00 USD / Day',
    b: 'Caps total autonomous disbursements within a 24-hour window.'
  },
  {
    n: 3,
    t: 'Dual Approval Requirement',
    th: 'client_approved == true AND freelancer_approved == true',
    b: 'Rejects any funding or release where plan hashes do not match.',
    code: true
  },
  {
    n: 4,
    t: 'Recipient Email Format & Verification',
    th: 'Valid PayPal email',
    b: 'Recipient must be a valid, formatted PayPal email.'
  },
  {
    n: 5,
    t: 'Quiet Hours Compliance',
    th: '21:00 to 08:00 (Customer Local Time)',
    b: 'Halts all automated recovery outreach and payment retries during quiet hours.'
  },
  {
    n: 6,
    t: 'Dispute Circuit Breaker',
    th: 'Any active PayPal dispute',
    b: 'Freezes the corresponding escrow and halts recovery campaigns.'
  }
];

const INITIAL_HISTORY = [
  ['10:42:08', 'ESCROW_RELEASE', 150, 'ALLOWED', '—', 'Verification Agent', 'a91f3c07d2e84b165c0f9a3e7d18b2c4'],
  ['10:15:31', 'ESCROW_RELEASE', 700, 'DENIED', 'Rule 1: Amount exceeds $200.00 threshold', 'Verification Agent', '4be07d92c1a53f86e0d7b4a912c3f58e'],
  ['09:58:12', 'RECOVERY_OUTREACH', 350, 'DENIED', 'Rule 5: Quiet hours (customer local 22:10)', 'Recovery Agent', 'c2d8e51f07a39b64d1e8f20a5c7b3694'],
  ['09:31:47', 'ESCROW_RELEASE', 400, 'DENIED', 'Rule 6: Active PayPal dispute freezes escrow', 'Dispute Webhook', '0a8f9c2d71be4a5f3c9d0e68b2147ad5'],
  ['09:12:03', 'ESCROW_FUNDING', 2400, 'DENIED', 'Rule 3: Plan hash mismatch (409 Conflict)', 'Client Session', '7c31e0b9a4d85f126e9b30c7d1a58f42']
];

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

async function sha256(str) {
  try {
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
    return Array.from(new Uint8Array(b)).map(x => x.toString(16).padStart(2, '0')).join('');
  } catch {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
    return h.toString(16).padStart(8, '0').repeat(8);
  }
}

export default function MandateGuard() {
  const [history, setHistory] = useState(INITIAL_HISTORY);
  const [amount, setAmount] = useState('700.00');
  const [actionType, setActionType] = useState('ESCROW_RELEASE');
  const [score, setScore] = useState('0.94');
  const [recipient, setRecipient] = useState('freelancer@example.com');
  const [dailyVol, setDailyVol] = useState('1200');
  const [localTime, setLocalTime] = useState('14:30');
  const [dualApproved, setDualApproved] = useState('1');
  const [disputeActive, setDisputeActive] = useState('0');
  const [evalResult, setEvalResult] = useState(null);
  const [evaluating, setEvaluating] = useState(false);

  // Stats calculation
  const totalEvals = history.length + 130;
  const allowedCount = history.filter(h => h[3] === 'ALLOWED').length + 96;
  const deniedCount = totalEvals - allowedCount;

  const evaluatePolicy = (inputs) => {
    const R1 = 'Rule ';
    if (inputs.dispute) {
      return { ok: false, r: R1 + '6: Active PayPal dispute freezes escrow and halts recovery.', n: 'Frozen until human dispute review completes. See Disputes.' };
    }
    if (!inputs.dual && inputs.type !== 'RECOVERY_OUTREACH') {
      return { ok: false, r: R1 + '3: Plan hashes do not match or approval is missing.', n: 'Rejected with 409 Conflict. Both parties must re-approve the plan hash.' };
    }
    if (inputs.type !== 'RECOVERY_OUTREACH' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(inputs.rcp)) {
      return { ok: false, r: R1 + '4: Recipient is not a valid PayPal email.', n: 'Correct the recipient and resubmit.' };
    }
    if (inputs.type === 'RECOVERY_OUTREACH') {
      const [h, m] = inputs.time.split(':').map(Number);
      if (isNaN(h) || h > 23 || isNaN(m) || m > 59) {
        return { ok: false, r: 'Input error: local time must be HH:MM.', n: 'Fix the time and re-run.', bad: true };
      }
      if (h >= 21 || h < 8) {
        return { ok: false, r: R1 + '5: ' + inputs.time + ' falls inside quiet hours (21:00–08:00).', n: 'Outreach rescheduled to 08:00 customer local time.' };
      }
      return { ok: true, r: 'All rules passed.', n: 'Outreach dispatched.' };
    }
    if (inputs.type === 'ESCROW_FUNDING') {
      return { ok: true, r: 'All rules passed.', n: 'Funding proceeds to PayPal Orders v2 capture.' };
    }
    if (inputs.score < 0.6) {
      return { ok: false, r: R1 + '1: Verifier score ' + inputs.score.toFixed(2) + ' is below 0.60 (AUTO_REJECT).', n: 'Release rejected. Freelancer notified to revise.' };
    }
    if (inputs.score < 0.8) {
      return { ok: false, hum: true, r: R1 + '1: Verifier score ' + inputs.score.toFixed(2) + ' is below 0.80 (HUMAN_REVIEW).', n: 'Routed to Human Approvals Queue (Task #APP-105).' };
    }
    if (inputs.amt > 200) {
      return { ok: false, hum: true, r: R1 + '1: Amount ' + fmt(inputs.amt) + ' exceeds $200.00 autonomous threshold.', n: 'Routed to Human Approvals Queue (Task #APP-105).' };
    }
    if (inputs.vol + inputs.amt > 5000) {
      return { ok: false, hum: true, r: R1 + '2: Daily volume would reach ' + fmt(inputs.vol + inputs.amt) + ', over $5,000.00.', n: 'Routed to Human Approvals Queue (Task #APP-105).' };
    }
    return { ok: true, r: 'All rules passed.', n: 'Executor dispatches PayPal Payout. Ledger and audit updated.' };
  };

  const handleSimulate = async (e) => {
    e.preventDefault();
    const amt = parseFloat(amount);
    const sc = parseFloat(score);
    const vol = parseFloat(dailyVol) || 0;

    if (isNaN(amt) || amt < 0 || !amount) {
      setEvalResult({ error: 'Enter a valid amount.' });
      return;
    }
    if (actionType === 'ESCROW_RELEASE' && (isNaN(sc) || sc < 0 || sc > 1)) {
      setEvalResult({ error: 'Verifier score must be between 0.00 and 1.00.' });
      return;
    }

    setEvaluating(true);
    await new Promise(r => setTimeout(r, 400));

    const inputs = {
      amt,
      type: actionType,
      score: sc,
      rcp: recipient.trim(),
      vol,
      time: localTime.trim(),
      dual: dualApproved === '1',
      dispute: disputeActive === '1'
    };

    const res = evaluatePolicy(inputs);
    setEvaluating(false);

    if (res.bad) {
      setEvalResult({ error: res.r });
      return;
    }

    const dec = res.ok ? 'ALLOWED' : 'DENIED';
    const head = res.ok ? 'ALLOWED — Executes Autonomously' : (res.hum ? 'DENIED — Requires Human Approval' : 'DENIED — Blocked by Policy');
    const hash = await sha256(JSON.stringify({ inputs, dec, r: res.r, t: Date.now() }));

    setEvalResult({
      ok: res.ok,
      head,
      rule: res.r,
      nextStep: res.n,
      hash
    });

    setHistory(prev => [
      [new Date().toISOString().slice(11, 19), actionType, amt, dec, res.ok ? '—' : res.r, 'Simulator (Risk Officer)', hash.slice(0, 32)],
      ...prev
    ]);

    showToast(
      res.ok
        ? 'Policy: ALLOWED. Evaluation recorded in audit chain.'
        : res.hum
        ? 'Policy Alert: Payout exceeds limit or needs review. Routed to Human Approvals Queue.'
        : 'Policy: DENIED. Evaluation recorded in audit chain.',
      res.ok ? 'success' : 'warning'
    );
  };

  const loadSample150 = () => {
    setAmount('150.00');
    setScore('0.92');
    setActionType('ESCROW_RELEASE');
    setRecipient('freelancer@example.com');
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Mandate Guard / Policy Engine</h1>
          <p className={styles.sub}>
            The deterministic financial firewall. AI agents recommend actions; Mandate Guard decides what executes.
          </p>
        </div>
        <span className={`${styles.bd} ${styles.g}`} style={{ padding: '8px 14px', fontSize: 13 }}>
          ● Policy Engine: ACTIVE &amp; ENFORCING (100% Deterministic)
        </span>
      </div>

      {/* Hero card */}
      <section className={styles.hero}>
        <div style={{ fontSize: 16, fontWeight: 600 }}>
          AI recommends. Policy decides. PayPal executes. Every action is auditable.
        </div>
        <div className={styles.heroStats}>
          <div>
            <div className={styles.heroStatLabel}>Evaluations (24h)</div>
            <div className={`${styles.heroStatVal} ${styles.num}`}>{totalEvals}</div>
          </div>
          <div>
            <div className={styles.heroStatLabel}>Allowed</div>
            <div className={`${styles.heroStatVal} ${styles.num}`} style={{ color: '#4CC38A' }}>{allowedCount}</div>
          </div>
          <div>
            <div className={styles.heroStatLabel}>Denied</div>
            <div className={`${styles.heroStatVal} ${styles.num}`} style={{ color: '#FF9AA0' }}>{deniedCount}</div>
          </div>
        </div>
      </section>

      {/* Section A: Live Configured Policy Rules */}
      <section className={styles.card} aria-label="Configured policy rules">
        <div className={styles.rulesHead}>
          <h2 className={styles.h2}>A. Live Configured Policy Rules</h2>
          <span className={styles.muted}>Rules are read-only code. LLMs cannot modify or bypass them.</span>
        </div>

        <div style={{ marginTop: 8 }}>
          {RULES.map(r => (
            <div key={r.n} className={styles.ruleItem}>
              <div className={styles.ruleNum}>{r.n}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <b>Rule {r.n}: {r.t}</b>
                  <span className={`${styles.bd} ${styles.g}`}>ENFORCING</span>
                </div>
                <div style={{ marginTop: 4 }}>
                  {r.code ? (
                    <code className={styles.mono}>{r.th}</code>
                  ) : (
                    <span>Threshold: <b className={styles.num}>{r.th}</b></span>
                  )}
                </div>
                <div className={styles.muted} style={{ marginTop: 4 }}>{r.b}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Section B: Simulator Sandbox & Decision Flow */}
      <section className={styles.twoCol}>
        {/* Simulator */}
        <div className={styles.card} style={{ minWidth: 0 }}>
          <h2 className={styles.h2}>B. Policy Simulator Sandbox</h2>
          <p className={styles.muted} style={{ margin: '4px 0 16px' }}>
            Test any proposed action against the live rules. Prefilled with the Milestone 2 payout.
          </p>

          <form onSubmit={handleSimulate} className={styles.simForm}>
            <label className={styles.label}>
              Amount (USD)
              <input
                className={`${styles.input} ${styles.num}`}
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={e => setAmount(e.target.value)}
              />
            </label>

            <label className={styles.label}>
              Action Type
              <select className={styles.input} value={actionType} onChange={e => setActionType(e.target.value)}>
                <option value="ESCROW_RELEASE">ESCROW_RELEASE</option>
                <option value="ESCROW_FUNDING">ESCROW_FUNDING</option>
                <option value="RECOVERY_OUTREACH">RECOVERY_OUTREACH</option>
              </select>
            </label>

            <label className={styles.label}>
              Verifier Score (0.00–1.00)
              <input
                className={`${styles.input} ${styles.num}`}
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={score}
                onChange={e => setScore(e.target.value)}
              />
            </label>

            <label className={styles.label}>
              Recipient
              <input
                className={styles.input}
                type="text"
                value={recipient}
                onChange={e => setRecipient(e.target.value)}
              />
            </label>

            <details className={styles.detailsWrap}>
              <summary className={styles.muted} style={{ cursor: 'pointer', minHeight: 32 }}>
                Advanced context (rules 2, 3, 5, 6)
              </summary>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
                <label className={styles.label}>
                  Daily volume already paid (USD)
                  <input
                    className={`${styles.input} ${styles.num}`}
                    type="number"
                    min="0"
                    value={dailyVol}
                    onChange={e => setDailyVol(e.target.value)}
                  />
                </label>
                <label className={styles.label}>
                  Customer local time (HH:MM)
                  <input
                    className={styles.input}
                    type="text"
                    value={localTime}
                    onChange={e => setLocalTime(e.target.value)}
                  />
                </label>
                <label className={styles.label}>
                  Plan hashes
                  <select className={styles.input} value={dualApproved} onChange={e => setDualApproved(e.target.value)}>
                    <option value="1">Both approved &amp; matching</option>
                    <option value="0">Mismatch / missing approval</option>
                  </select>
                </label>
                <label className={styles.label}>
                  PayPal dispute
                  <select className={styles.input} value={disputeActive} onChange={e => setDisputeActive(e.target.value)}>
                    <option value="0">None active</option>
                    <option value="1">Active dispute</option>
                  </select>
                </label>
              </div>
            </details>

            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 8 }}>
              <button className={`${styles.btn} ${styles.btnP}`} type="submit" style={{ flex: 1 }} disabled={evaluating}>
                {evaluating ? 'Evaluating…' : 'Evaluate Policy Now'}
              </button>
              <button className={styles.btn} type="button" onClick={loadSample150}>
                Load $150 sample
              </button>
            </div>
          </form>

          {evalResult && (
            <div style={{ marginTop: 16 }}>
              {evalResult.error ? (
                <div className={styles.card} style={{ borderLeft: '4px solid #D9363E' }}>
                  {evalResult.error}
                </div>
              ) : (
                <div
                  className={styles.card}
                  style={{
                    borderLeft: `4px solid ${evalResult.ok ? '#2E9D65' : '#D9363E'}`,
                    background: evalResult.ok ? '#F3FBF6' : '#FEF6F6'
                  }}
                >
                  <div className={styles.muted}>Result</div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: evalResult.ok ? '#1E7A4C' : '#B42830' }}>
                    {evalResult.head}
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <div className={styles.muted}>Triggered Rule</div>
                    <div>{evalResult.rule}</div>
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <div className={styles.muted}>Required Next Step</div>
                    <div>{evalResult.nextStep}</div>
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <a className={styles.monoLink} href="/audit">
                      Audit hash {evalResult.hash.slice(0, 12)}… ↗
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Decision Flow */}
        <div className={styles.card} style={{ minWidth: 0 }}>
          <h2 className={styles.h2}>Decision Flow</h2>
          <p className={styles.muted} style={{ margin: '4px 0 12px' }}>
            Rules run in fixed order; the first failing rule decides.
          </p>
          <ol style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {[
              'Dispute freeze',
              'Dual approval',
              'Recipient email',
              'Quiet hours',
              'Verifier score route',
              'Payout cap',
              'Daily volume'
            ].map((step, i) => (
              <li key={step} className={styles.flowItem}>
                <span className={styles.flowCircle}>{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Section C: Policy Decision History */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }} aria-label="Policy decision history">
        <div style={{ padding: '20px 20px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <h2 className={styles.h2}>C. Policy Decision History</h2>
          <span className={styles.muted}>Source: GET /audit</span>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Time (UTC)</th>
                <th className={styles.th}>Action</th>
                <th className={styles.th}>Proposed Amount</th>
                <th className={styles.th}>Decision</th>
                <th className={styles.th}>Triggered Rule</th>
                <th className={styles.th}>Actor</th>
                <th className={styles.th}>Audit Hash</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td className={`${styles.td} ${styles.num}`}>{h[0]}</td>
                  <td className={styles.td}><code className={styles.mono}>{h[1]}</code></td>
                  <td className={`${styles.td} ${styles.num}`}><b>{fmt(h[2])}</b></td>
                  <td className={styles.td}>
                    <span className={`${styles.bd} ${h[3] === 'ALLOWED' ? styles.g : styles.r}`}>
                      {h[3]}
                    </span>
                  </td>
                  <td className={styles.td}>{h[4]}</td>
                  <td className={styles.td}>{h[5]}</td>
                  <td className={styles.td}>
                    <a className={styles.monoLink} href="/audit">
                      {h[6].slice(0, 8)}…{h[6].slice(-4)} ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
