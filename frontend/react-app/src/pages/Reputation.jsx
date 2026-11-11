import { useState, useEffect } from 'react';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { showToast } from '../components/ui/Toast';
import styles from './Reputation.module.css';

const MONTHS = ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'];

const SUBJECTS = [
  {
    name: 'Rahul Sharma',
    role: 'Freelancer',
    email: 'freelancer@example.com',
    user: '@rahul.sharma',
    wallet: 'PPW-7K2M-91XQ',
    score: 98,
    m: 24,
    ot: 96,
    otL: 'On-Time Delivery Rate',
    av: 94.2,
    d: 0,
    vol: 42800,
    b: [99, 97, 96],
    ts: [82, 84, 85, 88, 90, 91, 93, 94, 95, 96, 97, 98],
    hash: 'a91f3c07d2e84b165c0f9a3e7d18b2c4'
  },
  {
    name: 'Acme Global Solutions',
    role: 'Client',
    email: 'client@example.com',
    user: '@acme.global',
    wallet: 'PPW-3A8D-55LZ',
    score: 91,
    m: 31,
    ot: 89,
    otL: 'On-Time Approval Rate',
    av: null,
    d: 1,
    vol: 61250,
    b: [88, 95, 90],
    ts: [88, 89, 89, 90, 92, 93, 92, 91, 90, 91, 91, 91],
    hash: '4be07d92c1a53f86e0d7b4a912c3f58e'
  },
  {
    name: 'Northwind SaaS',
    role: 'Merchant',
    email: 'billing@northwind.example',
    user: '@northwind',
    wallet: 'PPW-9C4F-20RT',
    score: 86,
    m: 0,
    ot: 79,
    otL: 'Recovery Success Rate',
    av: null,
    d: 2,
    vol: 18600,
    b: [0, 88, 82],
    ts: [78, 79, 80, 82, 81, 83, 84, 85, 85, 86, 86, 86],
    hash: 'c2d8e51f07a39b64d1e8f20a5c7b3694'
  },
  {
    name: 'Tom Becker',
    role: 'Client',
    email: 'tom.becker@example.com',
    user: '@tbecker',
    wallet: 'PPW-5E1B-77HN',
    score: 72,
    m: 6,
    ot: 70,
    otL: 'On-Time Approval Rate',
    av: null,
    d: 0,
    vol: 5400,
    b: [68, 74, 75],
    ts: [60, 62, 64, 66, 65, 68, 69, 70, 71, 71, 72, 72],
    hash: '7c31e0b9a4d85f126e9b30c7d1a58f42'
  },
  {
    name: 'Lena Ortiz',
    role: 'Merchant customer',
    email: 'lena@example.com',
    user: '@lortiz',
    wallet: 'PPW-2D9A-48KC',
    score: 58,
    m: 0,
    ot: 52,
    otL: 'On-Time Payment Rate',
    av: null,
    d: 1,
    vol: 1275,
    b: [0, 55, 60],
    ts: [74, 72, 70, 68, 66, 64, 62, 61, 60, 59, 58, 58],
    hash: '0a8f9c2d71be4a5f3c9d0e68b2147ad5'
  }
];

function getTier(score) {
  if (score >= 95) return ['PLATINUM TRUST TIER', 'pl'];
  if (score >= 85) return ['GOLD TRUST TIER', 'a'];
  if (score >= 70) return ['SILVER TRUST TIER', 'gy'];
  return ['WATCHLIST', 'r'];
}

const fmt = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';

export default function Reputation() {
  const { data: apiRep } = useApi(() => endpoints.reputation.all());
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredMonth, setHoveredMonth] = useState(11);
  const [notFound, setNotFound] = useState(false);
  const [dbEvents, setDbEvents] = useState([]);

  useEffect(() => {
    if (apiRep && apiRep.events) {
      setDbEvents(apiRep.events);
    }
  }, [apiRep]);

  const subject = SUBJECTS[selectedIdx] || SUBJECTS[0];
  const tier = getTier(subject.score);

  const handleSearch = (e) => {
    e.preventDefault();
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      showToast('Enter an email, username, or wallet ID to search.', 'warning');
      return;
    }

    const idx = SUBJECTS.findIndex(x =>
      [x.email, x.user, x.wallet, x.name].some(v => v.toLowerCase() === q)
    );
    const partialIdx = idx >= 0 ? idx : SUBJECTS.findIndex(x =>
      [x.email, x.user, x.wallet, x.name].some(v => v.toLowerCase().includes(q))
    );

    if (partialIdx >= 0) {
      setSelectedIdx(partialIdx);
      setNotFound(false);
      showToast(`Loaded reputation for ${SUBJECTS[partialIdx].name}.`, 'success');
    } else {
      setNotFound(true);
    }
  };

  // SVG Chart parameters
  const W = 640;
  const H = 220;
  const L = 36;
  const B = 28;
  const T = 12;
  const mn = 40;
  const mx = 100;
  const px = (i) => L + (i * (W - L - 12)) / 11;
  const py = (v) => T + ((mx - v) / (mx - mn)) * (H - T - B);
  const pts = subject.ts.map((v, i) => `${px(i)},${py(v)}`).join(' ');

  const currentMonthDelta = hoveredMonth > 0 ? subject.ts[hoveredMonth] - subject.ts[hoveredMonth - 1] : 0;
  const deltaStr = hoveredMonth > 0 ? ` (${currentMonthDelta >= 0 ? '+' : ''}${currentMonthDelta} vs prior month)` : '';

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.h1}>Reputation Ledger</h1>
          <p className={styles.sub}>
            Cross-platform trust scores measuring milestone delivery, payment speed, and recovery responsiveness.
          </p>
        </div>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className={styles.searchForm}>
        <input
          className={styles.searchInput}
          list="sug"
          placeholder="Search by Email, Username, or Wallet ID (e.g. freelancer@example.com)"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          autoComplete="off"
        />
        <datalist id="sug">
          {SUBJECTS.map(x => <option key={x.email} value={x.email}>{x.name}</option>)}
        </datalist>
        <button className={`${styles.btn} ${styles.btnP}`} type="submit">
          Search Profile
        </button>
      </form>

      {notFound ? (
        <div className={styles.card} style={{ textAlign: 'center', padding: 40 }}>
          <b>No reputation record found</b>
          <div className={styles.muted} style={{ marginTop: 4 }}>
            Nothing matches “{searchQuery}”. Try freelancer@example.com, @acme.global or PPW-9C4F-20RT.
          </div>
        </div>
      ) : (
        <>
          {/* Subject Profile Card */}
          <section className={styles.card} aria-label="Subject profile">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <span className={styles.avatar}>
                  {subject.name[0]}
                </span>
                <div>
                  <h2 className={styles.h2}>{subject.name} - {subject.role}</h2>
                  <div className={styles.muted} style={{ marginTop: 2 }}>
                    {subject.email} · {subject.user} · <code className={styles.mono}>{subject.wallet}</code>
                  </div>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span className={`${styles.bd} ${styles[tier[1]]}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                  {tier[0]}
                </span>
                <div className={`${styles.num}`} style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>
                  {subject.score}<span style={{ fontSize: 16, color: '#64748B', fontWeight: 500 }}>/100</span>
                </div>
              </div>
            </div>

            {/* 5 KPI metrics */}
            <div className={styles.metricGrid}>
              <div className={styles.metricCard}>
                <div className={styles.muted}>Completed Milestones</div>
                <div className={`${styles.num} ${styles.metricVal}`}>{subject.m ? subject.m : '—'}</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.muted}>{subject.otL}</div>
                <div className={`${styles.num} ${styles.metricVal}`}>{subject.ot}%</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.muted}>Average Verification Score</div>
                <div className={`${styles.num} ${styles.metricVal}`}>{subject.av ? subject.av + '%' : '—'}</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.muted}>Disputes Incurred</div>
                <div
                  className={`${styles.num} ${styles.metricVal}`}
                  style={{ color: subject.d > 0 ? '#B42830' : undefined }}
                >
                  {subject.d}
                </div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.muted}>Total Volume Released via PayPal</div>
                <div className={`${styles.num} ${styles.metricVal}`}>{fmt(subject.vol)}</div>
              </div>
            </div>
          </section>

          {/* 2 Column: Historical Timeline & Score Breakdown */}
          <section className={styles.twoCol}>
            {/* Historical Trust Timeline */}
            <div className={styles.card} style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <h2 className={styles.h2}>Historical Trust Timeline</h2>
                <span className={styles.muted}>Past 12 months</span>
              </div>

              <div className={styles.chartTip}>
                {MONTHS[hoveredMonth]} — trust score {subject.ts[hoveredMonth]}/100{deltaStr}
              </div>

              <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" style={{ display: 'block' }}>
                {/* Horizontal Grid lines */}
                {[40, 60, 80, 100].map(v => (
                  <g key={v}>
                    <line x1={L} x2={W - 12} y1={py(v)} y2={py(v)} stroke="#E5E9F0" />
                    <text x={L - 6} y={py(v) + 4} textAnchor="end" fontSize="11" fill="#64748B" fontFamily="Inter,sans-serif">
                      {v}
                    </text>
                  </g>
                ))}
                {/* Platinum 95 dashed threshold */}
                <line x1={L} x2={W - 12} y1={py(95)} y2={py(95)} stroke="#009CDE" strokeDasharray="4 4" />
                <text x={W - 14} y={py(95) - 4} textAnchor="end" fontSize="11" fill="#005BB5" fontFamily="Inter,sans-serif">
                  Platinum 95
                </text>

                {/* Line and dots */}
                <polyline points={pts} fill="none" stroke="#0070E0" strokeWidth="2.5" />
                {subject.ts.map((v, i) => (
                  <circle
                    key={i}
                    cx={px(i)}
                    cy={py(v)}
                    r="5"
                    fill={hoveredMonth === i ? '#003087' : '#0070E0'}
                    stroke="#fff"
                    strokeWidth="2"
                    style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
                    onMouseEnter={() => setHoveredMonth(i)}
                    onClick={() => setHoveredMonth(i)}
                  />
                ))}

                {/* Month labels */}
                {MONTHS.map((m, i) => (
                  <text key={m} x={px(i)} y={H - 8} textAnchor="middle" fontSize="11" fill="#64748B" fontFamily="Inter,sans-serif">
                    {m}
                  </text>
                ))}
              </svg>
            </div>

            {/* Score Breakdown */}
            <div className={styles.card} style={{ minWidth: 0 }}>
              <h2 className={styles.h2}>Score Breakdown</h2>
              <div style={{ display: 'grid', gap: 16, marginTop: 16 }}>
                {[
                  ['Milestone delivery', subject.b[0]],
                  ['Payment speed', subject.b[1]],
                  ['Recovery responsiveness', subject.b[2]]
                ].map(b => (
                  <div key={b[0]}>
                    {b[1] ? (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                          <span>{b[0]}</span>
                          <b className={styles.num}>{b[1]}</b>
                        </div>
                        <div className={styles.breakdownTrack}>
                          <div
                            className={styles.breakdownFill}
                            style={{
                              width: `${b[1]}%`,
                              background: b[1] >= 85 ? '#2E9D65' : b[1] >= 70 ? '#F5A623' : '#D9363E'
                            }}
                          />
                        </div>
                      </>
                    ) : (
                      <div className={styles.muted} style={{ fontSize: 13 }}>{b[0]}: not applicable for this role</div>
                    )}
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #E5E9F0' }}>
                <div className={styles.muted}>Score snapshot anchored in audit chain</div>
                <a className={styles.monoLink} href="/audit">
                  {subject.hash.slice(0, 12)}…{subject.hash.slice(-4)} ↗
                </a>
              </div>
            </div>
          </section>
        </>
      )}

      {/* Ledger Directory */}
      <section className={styles.card} style={{ padding: 0, overflow: 'hidden' }} aria-label="Ledger directory">
        <div style={{ padding: '20px 20px 12px' }}>
          <h2 className={styles.h2}>Ledger Directory</h2>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Subject</th>
                <th className={styles.th}>Role</th>
                <th className={styles.th}>Score</th>
                <th className={styles.th}>Tier</th>
                <th className={styles.th}>Disputes</th>
              </tr>
            </thead>
            <tbody>
              {SUBJECTS.map((x, i) => {
                const trTier = getTier(x.score);
                const isSelected = selectedIdx === i;
                return (
                  <tr
                    key={x.email}
                    className={`${styles.dirRow} ${isSelected ? styles.dirRowActive : ''}`}
                    onClick={() => { setSelectedIdx(i); setNotFound(false); }}
                  >
                    <td className={styles.td}>
                      <b>{x.name}</b>
                      <div className={styles.muted}>{x.email}</div>
                    </td>
                    <td className={styles.td}>{x.role}</td>
                    <td className={`${styles.td} ${styles.num}`}>
                      <b>{x.score}</b>/100
                    </td>
                    <td className={styles.td}>
                      <span className={`${styles.bd} ${styles[trTier[1]]}`}>
                        {trTier[0].replace(' TRUST TIER', '')}
                      </span>
                    </td>
                    <td className={`${styles.td} ${styles.num}`}>{x.d}</td>
                  </tr>
                );
              })}
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
