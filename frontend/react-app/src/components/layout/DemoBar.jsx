import { useState, useRef } from 'react';
import { endpoints } from '../../api/endpoints';
import { showToast } from '../ui/Toast';
import styles from './DemoBar.module.css';

const FAILURES = [
  { label: 'Insufficient Funds', code: 'INSUFFICIENT_FUNDS' },
  { label: 'Expired Card',       code: 'EXPIRED_CARD' },
  { label: 'Dispute Filed',      code: 'DISPUTE_FILED' },
  { label: 'Plan Hash Mismatch', code: 'PLAN_HASH_MISMATCH' },
];

export function DemoBar() {
  const [simTime, setSimTime]       = useState(null);
  const [injectOpen, setInjectOpen] = useState(false);
  const [loading, setLoading]       = useState('');
  const dropRef = useRef(null);

  async function advance(hours) {
    setLoading('clock');
    try {
      const r = await endpoints.demo.advanceClock({ hours });
      setSimTime(r.current_time);
      showToast(`Clock advanced +${hours}h → ${new Date(r.current_time).toUTCString()}`, 'info');
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setLoading(''); }
  }

  async function injectFailure(code) {
    setInjectOpen(false);
    setLoading('inject');
    try {
      const r = await endpoints.demo.injectFailure({ failure_code: code });
      showToast(`Injected ${code} → Case ${r.case_id} created`, 'warning');
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setLoading(''); }
  }

  async function runBenchmark() {
    setLoading('bench');
    try {
      showToast('Running 150-case benchmark…', 'info');
      const cases = await endpoints.cases.list();
      const caseId = Array.isArray(cases) && cases.length ? cases[0].id : 'CASE-DEMO-001';
      const r = await endpoints.demo.runSimulator({ case_id: caseId });
      showToast(`Simulator: ${r.event_type} — ${r.message}`, 'success');
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setLoading(''); }
  }

  async function reset() {
    if (!window.confirm('Reset all demo state? This cannot be undone.')) return;
    setLoading('reset');
    try {
      await endpoints.demo.reset();
      showToast('Demo environment reset ✓', 'success');
      setTimeout(() => window.location.reload(), 1000);
    } catch (e) { showToast(e.message, 'danger'); }
    finally { setLoading(''); }
  }

  return (
    <div className={styles.bar} role="toolbar" aria-label="Hackathon evaluator demo bar">
      <span className={styles.label}>⚡ DEMO</span>

      <button className={styles.btn} onClick={() => advance(24)} disabled={loading === 'clock'}>
        🕒 +24h
      </button>
      <button className={styles.btn} onClick={() => advance(48)} disabled={loading === 'clock'}>
        🕒 +48h
      </button>

      <div className={styles.dropWrap} ref={dropRef}>
        <button
          className={styles.btn}
          onClick={() => setInjectOpen(o => !o)}
          disabled={loading === 'inject'}
          aria-expanded={injectOpen}
        >
          ⚠️ Inject ▾
        </button>
        {injectOpen && (
          <div className={styles.drop}>
            {FAILURES.map(f => (
              <button key={f.code} className={styles.dropItem} onClick={() => injectFailure(f.code)}>
                {f.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <button className={styles.btn} onClick={runBenchmark} disabled={loading === 'bench'}>
        🚀 150-Case Sim
      </button>

      <button className={`${styles.btn} ${styles.danger}`} onClick={reset} disabled={loading === 'reset'}>
        🔄 Reset
      </button>

      {simTime && (
        <span className={styles.time}>
          Sim Time: {new Date(simTime).toUTCString()}
        </span>
      )}
    </div>
  );
}

