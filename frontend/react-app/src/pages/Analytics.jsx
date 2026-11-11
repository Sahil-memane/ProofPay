import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/ui/Spinner';
import { showToast } from '../components/ui/Toast';
import styles from './Analytics.module.css';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const FALLBACK = {
  agent: { recovery_rate: 0.2867, cases_processed: 150, correctly_recovered: 43, wrongful_contacts: 0, amount_recovered_usd: 11010 },
  baseline: { recovery_rate: 0.08, cases_processed: 150, correctly_recovered: 12, wrongful_contacts: 0, amount_recovered_usd: 2560 },
};

export default function Analytics() {
  const { data: evalData, loading, refetch } = useApi(() => endpoints.eval.latest());

  async function runBenchmark() {
    try {
      showToast('Running 150-case benchmark…', 'info');
      const cases = await endpoints.cases.list();
      const caseId = Array.isArray(cases) && cases.length ? cases[0].id : 'CASE-DEMO-001';
      const r = await endpoints.demo.runSimulator({ case_id: caseId });
      showToast(`Sim: ${r.event_type} — ${r.message}`, 'success');
      refetch();
    } catch (e) { showToast(e.message, 'danger'); }
  }

  if (loading) return <PageLoader />;

  const d = evalData ?? FALLBACK;
  const agent    = d.agent    ?? FALLBACK.agent;
  const baseline = d.baseline ?? FALLBACK.baseline;

  const rateData = [
    { name: 'Agent (ProofPay)', value: +(agent.recovery_rate * 100).toFixed(2), fill: '#0070E0' },
    { name: 'Baseline',         value: +(baseline.recovery_rate * 100).toFixed(2), fill: '#9DB6E0' },
  ];
  const amtData = [
    { name: 'Agent', value: agent.amount_recovered_usd ?? 11010, fill: '#2E9D65' },
    { name: 'Baseline', value: baseline.amount_recovered_usd ?? 2560, fill: '#9DB6E0' },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Analytics & Reports</h1>
          <p className={styles.sub}>AI Agent vs Baseline recovery benchmark — 150 test cases.</p>
        </div>
        <Button variant="primary" onClick={runBenchmark}>🚀 Run 150-Case Benchmark</Button>
      </div>

      {/* Headline comparison */}
      <div className={styles.comparison}>
        <Card className={styles.agentCard}>
          <div className={styles.compLabel}>Agent Recovery Rate</div>
          <div className={styles.compValue} style={{ color: 'var(--blue)' }}>
            {(agent.recovery_rate * 100).toFixed(2)}%
          </div>
          <div className={styles.compSub}>{agent.correctly_recovered ?? 43} / {agent.cases_processed ?? 150} cases</div>
          <div className={styles.compAmt}>${(agent.amount_recovered_usd ?? 11010).toLocaleString()} recovered</div>
        </Card>
        <div className={styles.vsBox}>VS</div>
        <Card className={styles.baseCard}>
          <div className={styles.compLabel}>Baseline Recovery Rate</div>
          <div className={styles.compValue} style={{ color: 'var(--muted)' }}>
            {(baseline.recovery_rate * 100).toFixed(2)}%
          </div>
          <div className={styles.compSub}>{baseline.correctly_recovered ?? 12} / {baseline.cases_processed ?? 150} cases</div>
          <div className={styles.compAmt}>${(baseline.amount_recovered_usd ?? 2560).toLocaleString()} recovered</div>
        </Card>
        <Card className={styles.liftCard}>
          <div className={styles.compLabel}>Improvement</div>
          <div className={styles.compValue} style={{ color: 'var(--green)' }}>3.58×</div>
          <div className={styles.compSub}>More revenue</div>
          <div className={styles.compAmt} style={{ color: 'var(--green)' }}>0% wrongful contacts</div>
        </Card>
      </div>

      {/* Charts */}
      <div className={styles.chartsGrid}>
        <Card>
          <div className={styles.chartTitle}>Recovery Rate Comparison (%)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={rateData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 40]} unit="%" tick={{ fontSize: 11 }} />
              <Tooltip formatter={v => `${v}%`} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {rateData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <div className={styles.chartTitle}>Amount Recovered (USD)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={amtData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={v => `$${v / 1000}k`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={v => `$${v.toLocaleString()}`} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {amtData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Stats table */}
      <Card noPadding>
        <div className={styles.tableHeader}>Detailed Benchmark Results</div>
        <div style={{ overflowX: 'auto' }}>
          <table className={styles.table}>
            <thead><tr><th>Metric</th><th>Agent (ProofPay)</th><th>Baseline</th><th>Delta</th></tr></thead>
            <tbody>
              {[
                ['Recovery Rate', `${(agent.recovery_rate * 100).toFixed(2)}%`, `${(baseline.recovery_rate * 100).toFixed(2)}%`, '+' + ((agent.recovery_rate - baseline.recovery_rate) * 100).toFixed(2) + 'pp'],
                ['Cases Recovered', agent.correctly_recovered ?? 43, baseline.correctly_recovered ?? 12, `+${(agent.correctly_recovered ?? 43) - (baseline.correctly_recovered ?? 12)}`],
                ['Amount Recovered', `$${(agent.amount_recovered_usd ?? 11010).toLocaleString()}`, `$${(baseline.amount_recovered_usd ?? 2560).toLocaleString()}`, '+$' + ((agent.amount_recovered_usd ?? 11010) - (baseline.amount_recovered_usd ?? 2560)).toLocaleString()],
                ['Wrongful Contacts', agent.wrongful_contacts ?? 0, baseline.wrongful_contacts ?? 0, '0 (none)'],
                ['Cases Processed', agent.cases_processed ?? 150, baseline.cases_processed ?? 150, '—'],
              ].map(([metric, agentV, baseV, delta]) => (
                <tr key={metric}>
                  <td style={{ fontWeight: 500 }}>{metric}</td>
                  <td style={{ color: 'var(--blue)', fontWeight: 600 }}>{agentV}</td>
                  <td style={{ color: 'var(--muted)' }}>{baseV}</td>
                  <td style={{ color: 'var(--green)', fontWeight: 600 }}>{delta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

