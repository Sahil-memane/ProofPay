import { useState } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import styles from './MandateGuard.module.css';

const CAP = 200;

function evaluateLocal(amount, hour) {
  if (amount > CAP) return { allowed: false, reason: `Amount $${amount} exceeds autonomous cap of $${CAP}. Routes to HITL queue.` };
  if (hour >= 21 || hour < 8) return { allowed: false, reason: `Quiet hours (21:00–08:00). Outreach suspended.` };
  return { allowed: true, reason: `Within policy: amount ≤ $${CAP} and business hours.` };
}

export default function MandateGuard() {
  const { data: audit, loading } = useApi(() => endpoints.audit.list({ limit: 100 }));
  const [simAmt, setSimAmt] = useState('150');
  const [simHour, setSimHour] = useState('10');
  const [simResult, setSimResult] = useState(null);

  const policyEvents = (audit ?? []).filter(e =>
    e.event_type?.toLowerCase().includes('policy') ||
    e.event_type?.toLowerCase().includes('mandate') ||
    e.event_type?.toLowerCase().includes('guard') ||
    e.event_type?.toLowerCase().includes('approval')
  );

  function simulate(e) {
    e.preventDefault();
    const result = evaluateLocal(parseFloat(simAmt), parseInt(simHour));
    setSimResult(result);
  }

  return (
    <div className={styles.page}>
      <div>
        <h1 className={styles.h1}>Mandate Guard</h1>
        <p className={styles.sub}>AI-enforced policy layer controlling autonomous payout authority.</p>
      </div>

      {/* Policy rules */}
      <div className={styles.rulesGrid}>
        {[
          { label: 'Autonomous Cap', value: '$200.00 USD', icon: '🛡️', desc: 'Payouts ≤ $200 auto-approved. Above routes to HITL.' },
          { label: 'Quiet Hours', value: '21:00 – 08:00', icon: '🌙', desc: 'No outreach during quiet hours. Scheduler respects local time.' },
          { label: 'Max Contacts', value: '3 Attempts', icon: '📞', desc: 'Stage 1 → 2 → 3. HALTED after 3 failed attempts.' },
          { label: 'Wrongful Contact Rate', value: '0%', icon: '✅', desc: 'Paid-elsewhere cases blocked before any outreach.' },
        ].map(r => (
          <Card key={r.label} className={styles.ruleCard}>
            <div className={styles.ruleIcon}>{r.icon}</div>
            <div className={styles.ruleLabel}>{r.label}</div>
            <div className={styles.ruleValue}>{r.value}</div>
            <div className={styles.ruleDesc}>{r.desc}</div>
          </Card>
        ))}
      </div>

      <div className={styles.columns}>
        {/* Decision history */}
        <Card noPadding className={styles.historyCard}>
          <div className={styles.tableHeader}>Policy Decision History</div>
          {loading ? <PageLoader /> : (
            <div style={{ overflowX: 'auto' }}>
              <table className={styles.table}>
                <thead><tr><th>Event</th><th>Subject</th><th>Decision</th><th>Time</th></tr></thead>
                <tbody>
                  {policyEvents.map((ev, i) => (
                    <tr key={i}>
                      <td><Badge variant="info">{ev.event_type}</Badge></td>
                      <td className="mono">{ev.case_id ?? ev.project_id ?? '—'}</td>
                      <td><Badge variant={ev.decision === 'DENIED' ? 'danger' : 'success'}>{ev.decision ?? 'EVALUATED'}</Badge></td>
                      <td className="muted">{ev.ts ? new Date(ev.ts).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                  {policyEvents.length === 0 && (
                    <tr><td colSpan={4} style={{ textAlign: 'center', padding: 24, color: 'var(--muted)' }}>No policy events yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Policy Simulator */}
        <Card className={styles.simCard}>
          <div className={styles.simTitle}>Policy Simulator</div>
          <form onSubmit={simulate} className={styles.simForm}>
            <div className={styles.field}>
              <label>Amount (USD)</label>
              <input type="number" min="1" step="0.01" value={simAmt} onChange={e => setSimAmt(e.target.value)} className={styles.input} />
            </div>
            <div className={styles.field}>
              <label>Hour of Day (0–23)</label>
              <input type="number" min="0" max="23" value={simHour} onChange={e => setSimHour(e.target.value)} className={styles.input} />
            </div>
            <Button type="submit" variant="primary" size="sm">Simulate</Button>
          </form>
          {simResult && (
            <div className={`${styles.simResult} ${simResult.allowed ? styles.allowed : styles.denied}`}>
              <div className={styles.simDecision}>{simResult.allowed ? '✓ ALLOWED' : '✗ DENIED'}</div>
              <div className={styles.simReason}>{simResult.reason}</div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
