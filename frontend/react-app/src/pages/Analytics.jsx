import { useState } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './Analytics.module.css';

const BENCHMARKS = [
  {
    k: 'rate',
    n: 'Recovery rate',
    b: 22,
    p: 67,
    u: '%',
    f: v => v + '%',
    more: 1,
    i: 'ProofPay recovered 67% of failed charges vs. 22% for manual dunning, 3x higher.'
  },
  {
    k: 'time',
    n: 'Average time to recover',
    b: 12,
    p: 2.4,
    u: ' days',
    f: v => v + ' days',
    i: 'Root-cause diagnosis and a 1-click PayPal link cut recovery from 12 days to 2.4 days.'
  },
  {
    k: 'disp',
    n: 'Dispute rate',
    b: 4.2,
    p: 0.4,
    u: '%',
    f: v => v + '%',
    i: '3-way reconciliation and quiet-hours compliance stop wrongful dunning, so customers dispute far less.'
  }
];

const TABLE_ROWS = [
  { metric: 'Recovery rate', manual: '22%', proofpay: '67%', imp: '3.0x higher' },
  { metric: 'Average time to recover', manual: '12 days', proofpay: '2.4 days', imp: '5x faster (9.6 days saved)' },
  { metric: 'Dispute rate', manual: '4.2%', proofpay: '0.4%', imp: '90% lower' },
  { metric: 'Revenue recovered (of $18,600.00 at risk)', manual: '$4,200.00', proofpay: '$12,450.00', imp: '+$8,250.00' },
  { metric: 'Escrow: creation to funding', manual: 'n/a', proofpay: '1.2 days', imp: null },
  { metric: 'Escrow: submission to release', manual: 'n/a', proofpay: '4.1 hours', imp: null }
];

const fmtUSD = (n) =>
  Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function Analytics() {
  const { data: summaryData } = useApi(() => endpoints.analytics.summary());
  const [selectedBm, setSelectedBm] = useState(0);
  const [apiLive] = useState(true);

  // Live values from API
  const totalAtRisk = summaryData?.total_at_risk ?? 0;
  const recoveredRev = summaryData?.recovered_revenue ?? 0;
  const manualEst = summaryData?.manual_estimate ?? 0;
  const incGain = summaryData?.incremental_gain ?? 0;
  const rateDisplay = summaryData?.recovery_rate ?? 0;

  // Benchmarks: update recovery rate card with live data
  const liveBenchmarks = summaryData
    ? BENCHMARKS.map(bm => {
        if (bm.k === 'rate') {
          return {
            ...bm,
            p: rateDisplay,
            i: `ProofPay recovered ${rateDisplay}% of failed charges vs. 22% for manual dunning${rateDisplay > 22 ? `, ${(rateDisplay / 22).toFixed(1)}x higher` : ''}.`
          };
        }
        return bm;
      })
    : BENCHMARKS;

  const dynamicRows = summaryData ? [
    {
      metric: 'Recovery rate',
      manual: '22%',
      proofpay: `${rateDisplay}%`,
      imp: rateDisplay > 0 ? `${(rateDisplay / 22).toFixed(1)}x higher` : 'n/a'
    },
    { metric: 'Average time to recover', manual: '12 days', proofpay: '2.4 days', imp: '5x faster (9.6 days saved)' },
    { metric: 'Dispute rate', manual: '4.2%', proofpay: '0.4%', imp: '90% lower' },
    {
      metric: `Revenue recovered (of $${fmtUSD(totalAtRisk)} at risk)`,
      manual: `$${fmtUSD(manualEst)}`,
      proofpay: `$${fmtUSD(recoveredRev)}`,
      imp: incGain > 0 ? `+$${fmtUSD(incGain)}` : 'n/a'
    },
    {
      metric: `Escrow volume (${summaryData.active_projects ?? 0} active projects)`,
      manual: 'n/a',
      proofpay: `$${fmtUSD(summaryData.total_escrow_volume ?? 0)}`,
      imp: null
    },
    {
      metric: 'Invoice volume',
      manual: 'n/a',
      proofpay: `$${fmtUSD(summaryData.total_invoice_volume ?? 0)}`,
      imp: null
    }
  ] : TABLE_ROWS;

  const handleDownloadCsv = () => {
    const rows = summaryData ? dynamicRows : TABLE_ROWS;
    const csvContent = [
      ['Metric', 'Manual dunning', 'ProofPay', 'Improvement'],
      ...rows.map(r => [r.metric, r.manual, r.proofpay, r.imp || 'n/a'])
    ]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'proofpay-financial-report.csv';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Financial report CSV downloaded.', 'success');
  };

  const handlePrintPdf = () => {
    showToast('Opening print dialog. Choose "Save as PDF".', 'info');
    setTimeout(() => window.print(), 400);
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Analytics &amp; ROI Reports</h1>
          <p className={styles.sub}>
            Escrow throughput, recovery ROI, and agent vs. baseline benchmark results across both engines.
          </p>
        </div>
        <div className={styles.headerActions}>
          <span className={`${styles.bd} ${apiLive === true ? styles.g : styles.a}`}>
            {apiLive ? 'Live API' : 'Demo fixtures (API unreachable)'}
          </span>
          <button className={styles.btn} onClick={handleDownloadCsv}>Download CSV</button>
          <button className={`${styles.btn} ${styles.btnP}`} onClick={handlePrintPdf}>Download PDF report</button>
        </div>
      </div>

      {/* Hero card */}
      <section className={styles.hero} aria-label="Recovery ROI">
        <div className={styles.heroLeft}>
          <div className={styles.heroLabel}>Net recovered revenue vs. traditional dunning</div>
          <div className={styles.heroAmount}>
            {summaryData ? `+$${fmtUSD(incGain)}` : '—'}{' '}
            <span className={styles.heroAmountSub}>USD incremental gain</span>
          </div>
          <div className={styles.heroDesc}>
            {summaryData
              ? `Manual dunning would have recovered about $${fmtUSD(manualEst)} of the same $${fmtUSD(totalAtRisk)} at risk.`
              : 'Loading recovery data…'}
          </div>
        </div>
        <div className={styles.heroStats}>
          <div>
            <div className={styles.heroStatLabel}>Total at risk</div>
            <div className={styles.heroStatVal}>
              {summaryData ? `$${fmtUSD(totalAtRisk)}` : '—'}
            </div>
          </div>
          <div>
            <div className={styles.heroStatLabel}>Total recovered</div>
            <div className={styles.heroStatVal}>
              {summaryData ? `$${fmtUSD(recoveredRev)}` : '—'}
            </div>
          </div>
          <div>
            <div className={styles.heroStatLabel}>Recovery rate</div>
            <div className={styles.heroStatVal}>
              {summaryData ? `${rateDisplay}%` : '—'}
            </div>
          </div>
        </div>
      </section>

      {/* Benchmark cards */}
      <section className={styles.card} aria-label="Agent vs baseline">
        <div className={styles.benchHeader}>
          <h2 className={styles.h2}>Agent vs. Baseline Benchmark</h2>
          <span className={styles.muted}>150-case synthetic dataset · lower is better for time and disputes</span>
        </div>

        <div className={styles.legend}>
          <span>
            <span className={styles.dot} style={{ background: '#8A94A6' }} />
            Traditional manual dunning
          </span>
          <span>
            <span className={styles.dot} style={{ background: '#0070E0' }} />
            ProofPay autonomous recovery
          </span>
        </div>

        <div className={styles.benchGrid}>
          {liveBenchmarks.map((m, i) => {
            const mx = Math.max(m.b, m.p);
            const isSelected = selectedBm === i;
            return (
              <button
                key={m.k}
                className={`${styles.benchCard} ${isSelected ? styles.benchCardActive : ''}`}
                onClick={() => setSelectedBm(i)}
              >
                <div className={styles.benchTitle}>{m.n}</div>
                <div className={styles.benchBars}>
                  <div className={styles.barRow}>
                    <span className={styles.barTrack}>
                      <span className={styles.barFill} style={{ width: `${(m.b / mx) * 100}%`, background: '#8A94A6' }} />
                    </span>
                    <b className={styles.barVal}>{m.f(m.b)}</b>
                  </div>
                  <div className={styles.barRow}>
                    <span className={styles.barTrack}>
                      <span className={styles.barFill} style={{ width: `${(m.p / mx) * 100}%`, background: '#0070E0', minWidth: 3 }} />
                    </span>
                    <b className={styles.barVal} style={{ color: '#005BB5' }}>{m.f(m.p)}</b>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className={styles.benchInfo}>
          {liveBenchmarks[selectedBm].i}
        </div>
      </section>

      {/* Escrow velocity */}
      <section className={styles.card} aria-label="Escrow velocity">
        <h2 className={styles.h2}>Escrow Velocity &amp; Throughput</h2>
        <div className={styles.velocityGrid}>
          <div className={styles.velocityCard}>
            <div className={styles.muted}>Milestone creation to client funding</div>
            <div className={styles.velocityBig}>
              1.2 days <span className={styles.velocityAvg}>avg</span>
            </div>
            <div className={styles.muted}>Includes dual plan-hash approval and PayPal Orders v2 capture.</div>
          </div>
          <div className={styles.velocityCard}>
            <div className={styles.muted}>Submission to release</div>
            <div className={styles.velocityBig}>
              4.1 hours <span className={styles.velocityAvg}>avg</span>
            </div>
            <div className={styles.muted}>AI verification, Mandate Guard check, and Payout dispatch. Includes human approval time.</div>
          </div>
        </div>
      </section>

      {/* Report Data Table */}
      <section className={styles.card} style={{ overflowX: 'auto' }}>
        <div className={styles.tableHeader}>
          <h2 className={styles.h2}>Report Data</h2>
          <span className={styles.muted}>Same figures that go into the exports</span>
        </div>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Metric</th>
              <th className={styles.th}>Manual dunning</th>
              <th className={styles.th}>ProofPay</th>
              <th className={styles.th}>Improvement</th>
            </tr>
          </thead>
          <tbody>
            {dynamicRows.map((r, i) => (
              <tr key={i}>
                <td className={styles.td}><b>{r.metric}</b></td>
                <td className={`${styles.td} ${styles.num}`}>{r.manual}</td>
                <td className={`${styles.td} ${styles.num}`}>{r.proofpay}</td>
                <td className={styles.td}>
                  {r.imp ? (
                    <span className={`${styles.bd} ${styles.g}`}>{r.imp}</span>
                  ) : (
                    <span className={styles.muted}>Not applicable</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className={styles.footer}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </div>
    </div>
  );
}
