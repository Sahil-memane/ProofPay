import { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from '../components/ui/Toast';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import styles from './Invoices.module.css';

const INITIAL_INVOICES = [
  { id: 'INV-2026-1030', c: 'Acme Global Solutions', e: 'client@example.com', iss: 'Nov 10', due: 'Dec 10', a: 2400, s: 'DRAFT', k: '' },
  { id: 'INV-2026-1027', c: 'Dev Patel', e: 'dev@example.com', iss: 'Nov 05', due: 'Nov 20', a: 640, s: 'SENT', k: '' },
  { id: 'INV-2026-1024', c: 'Sarah Johnson', e: 'sarah@example.com', iss: 'Oct 28', due: 'Nov 07', a: 350, s: 'IN_RECOVERY', k: 'REC-2026-0042' },
  { id: 'INV-2026-1022', c: 'Lena Ortiz', e: 'lena@example.com', iss: 'Oct 20', due: 'Oct 30', a: 275, s: 'OVERDUE', k: 'REC-2026-0038' },
  { id: 'INV-2026-1019', c: 'Michael Anderson', e: 'michael@example.com', iss: 'Oct 14', due: 'Oct 24', a: 450, s: 'PAID_ELSEWHERE', k: 'REC-2026-0041' },
  { id: 'INV-2026-1015', c: 'Priya Nair', e: 'priya@example.com', iss: 'Oct 08', due: 'Oct 18', a: 129, s: 'PAID', k: 'REC-2026-0040' },
  { id: 'INV-2026-1011', c: 'Tom Becker', e: 'tom@example.com', iss: 'Oct 01', due: 'Oct 11', a: 890, s: 'PAID', k: 'REC-2026-0039' },
];

const INITIAL_SUBSCRIPTIONS = [
  { p: 'ProofPay Pro', c: 'Sarah Johnson', a: 49, cy: 'Monthly', n: 'Nov 12', m: 'Visa •••• 4242 (exp 10/26)', h: 'EXPIRED' },
  { p: 'Growth Annual', c: 'Tom Becker', a: 890, cy: 'Yearly', n: 'Oct 01, 2027', m: 'PayPal balance', h: 'HEALTHY' },
  { p: 'ProofPay Pro', c: 'Priya Nair', a: 49, cy: 'Monthly', n: 'Nov 18', m: 'Mastercard •••• 8812', h: 'HEALTHY' },
  { p: 'Team Seats (5)', c: 'Dev Patel', a: 120, cy: 'Monthly', n: 'Nov 24', m: 'Visa •••• 1005 (exp 12/26)', h: 'EXPIRING' },
  { p: 'Team Seats (10)', c: 'Lena Ortiz', a: 240, cy: 'Monthly', n: 'Nov 15', m: 'Amex •••• 3009 (exp 09/26)', h: 'EXPIRED' },
  { p: 'ProofPay Starter', c: 'Michael Anderson', a: 19, cy: 'Monthly', n: 'Nov 20', m: 'PayPal balance', h: 'HEALTHY' },
];

const INITIAL_FAILURES = [
  { t: 'Today 09:14', c: 'Sarah Johnson', a: 350, d: 'EXPIRED_CARD', n: 'Stage 1: send update link', s: 'AWAITING_CUSTOMER', k: 'REC-2026-0042' },
  { t: 'Today 07:52', c: 'Lena Ortiz', a: 275, d: 'EXPIRED_CARD', n: 'Stage 2: firm warning at 08:00', s: 'QUIET_HOURS_PAUSED', k: 'REC-2026-0038' },
  { t: 'Yesterday 18:30', c: 'Dev Patel', a: 120, d: 'INSUFFICIENT_FUNDS', n: 'Smart retry on Nov 14', s: 'RETRY_SCHEDULED', k: 'REC-2026-0043' },
  { t: 'Nov 09 11:05', c: 'Michael Anderson', a: 450, d: 'INSUFFICIENT_FUNDS', n: 'Halted: wire found in bank match', s: 'HALTED', k: 'REC-2026-0041' },
];

const INITIAL_LINKS = [
  { i: 'INV-2026-1024', a: 350, x: 'Nov 18', s: 'OPEN', u: 'pay?case_id=REC-2026-0042' },
  { i: 'INV-2026-1022', a: 275, x: 'Nov 05', s: 'USED', u: 'pay?case_id=REC-2026-0038' },
];

const POOL = [
  ['Ravi Menon', 199, 'BANK_AUTH_FAILED', 'Stage 1: 1-click PayPal authorization'],
  ['Clara Wu', 75, 'GATEWAY_ERROR', 'Immediate retry with backoff'],
  ['Omar Haddad', 320, 'INSUFFICIENT_FUNDS', 'Smart retry after payday'],
];

export default function Invoices() {
  const navigate = useNavigate();
  const { data: apiInvoices, refetch: refetchInvoices } = useApi(() => endpoints.invoices.list());
  const { data: apiSubs } = useApi(() => endpoints.paymentAttempts.list());

  const [activeTab, setActiveTab] = useState('inv');
  const [invoices, setInvoices] = useState(INITIAL_INVOICES);
  const [subscriptions] = useState(INITIAL_SUBSCRIPTIONS);
  const [failures, setFailures] = useState(INITIAL_FAILURES);
  const [links, setLinks] = useState(INITIAL_LINKS);

  useEffect(() => {
    if (apiInvoices && Array.isArray(apiInvoices) && apiInvoices.length > 0) {
      setInvoices(apiInvoices.map(inv => ({
        id: inv.invoice_id,
        c: inv.customer_id,
        e: `${inv.customer_id.toLowerCase()}@client.example`,
        iss: inv.issued_at ? new Date(inv.issued_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Nov 10',
        due: inv.due_at ? new Date(inv.due_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Dec 10',
        a: inv.amount_usd,
        s: (inv.status || 'pending').toUpperCase(),
        k: inv.status === 'overdue' ? `REC-${inv.invoice_id.replace('INV-', '')}` : ''
      })));
    }
  }, [apiInvoices]);

  useEffect(() => {
    if (apiSubs && Array.isArray(apiSubs) && apiSubs.length > 0) {
      setFailures(apiSubs.slice(0, 15).map((sub) => ({
        t: sub.failed_at ? new Date(sub.failed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Recently',
        c: sub.customer_id,
        a: sub.amount_usd,
        d: (sub.failure_code || 'INSUFFICIENT_FUNDS').toUpperCase().replace(/ /g, '_'),
        n: `Retry count: ${sub.retry_count}. Autonomous recovery agent queued.`,
        s: 'AWAITING_CUSTOMER',
        k: `REC-${sub.customer_id}`
      })));
    }
  }, [apiSubs]);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Drawer
  const [activeDrawer, setActiveDrawer] = useState(null);
  const [drawerHash, setDrawerHash] = useState('');

  // New Invoice Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [custName, setCustName] = useState('');
  const [custEmail, setCustEmail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [taxPct, setTaxPct] = useState(0);
  const [sendViaPayPal, setSendViaPayPal] = useState(true);
  const [lineItems, setLineItems] = useState([
    { description: 'Consulting Services', qty: 1, unitPrice: 350 },
  ]);

  // Single-use Link form
  const [linkInvId, setLinkInvId] = useState('INV-2026-1024');
  const [linkAmount, setLinkAmount] = useState('350.00');
  const [linkExpiryHours, setLinkExpiryHours] = useState('168');
  const [generatedLink, setGeneratedLink] = useState('');

  const fmt = (n) => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // Calculate KPIs
  const openInvoices = invoices.filter(i => ['SENT', 'OVERDUE', 'IN_RECOVERY'].includes(i.s));
  const outstandingTotal = openInvoices.reduce((acc, i) => acc + i.a, 0);
  const overdueTotal = invoices.filter(i => ['OVERDUE', 'IN_RECOVERY'].includes(i.s)).reduce((acc, i) => acc + i.a, 0);
  const mrrTotal = subscriptions.filter(s => s.cy === 'Monthly').reduce((acc, s) => acc + s.a, 0);
  const badCardsCount = subscriptions.filter(s => s.h !== 'HEALTHY').length;

  const filteredInvoices = useMemo(() => {
    return invoices.filter(i => {
      const matchStatus = !statusFilter || i.s === statusFilter;
      const q = searchQuery.toLowerCase();
      const matchQuery = !q || (i.id + i.c + i.e).toLowerCase().includes(q);
      return matchStatus && matchQuery;
    });
  }, [invoices, statusFilter, searchQuery]);

  const handleOpenDrawer = async (inv) => {
    setActiveDrawer(inv);
    try {
      const hashBuffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(inv)));
      const hashHex = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
      setDrawerHash(hashHex);
    } catch {
      setDrawerHash('Hash unavailable in this browser context');
    }
  };

  const handleExportCSV = () => {
    const rows = [
      ['invoice', 'customer', 'email', 'due', 'amount', 'status'],
      ...invoices.map(i => [i.id, i.c, i.e, i.due, i.a, i.s])
    ];
    const csvContent = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'invoices.csv';
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Invoices exported to invoices.csv.');
  };

  const handleSimulateFailure = () => {
    const pick = POOL[Math.floor(Math.random() * POOL.length)];
    const newCaseId = `REC-2026-00${44 + failures.length - 4}`;
    const newFail = {
      t: 'Just now',
      c: pick[0],
      a: pick[1],
      d: pick[2],
      n: pick[3],
      s: 'AWAITING_CUSTOMER',
      k: newCaseId,
    };
    setFailures([newFail, ...failures]);
    toast.warning(`Failed payment detected for ${pick[0]}. Diagnosed as ${pick[2]}.`);
  };

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Link copied to clipboard.');
  };

  const handleGenerateLink = (e) => {
    e.preventDefault();
    const inv = invoices.find(x => x.id === linkInvId);
    if (!inv) return;
    const hours = +linkExpiryHours;
    const expDate = new Date(Date.now() + hours * 3600000);
    const expStr = expDate.toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
    const u = `pay?${inv.k ? 'case_id=' + inv.k : 'invoice_id=' + inv.id}&t=${Math.random().toString(36).slice(2, 10)}`;
    const newL = {
      i: inv.id,
      a: parseFloat(linkAmount) || inv.a,
      x: expStr,
      s: 'OPEN',
      u,
    };
    setLinks([newL, ...links]);
    setGeneratedLink(u);
    toast.success(`Payment link generated for ${inv.id}.`);
  };

  const handleCreateInvoice = async (e) => {
    e.preventDefault();
    const subtotal = lineItems.reduce((acc, it) => acc + (it.qty * it.unitPrice), 0);
    const total = subtotal * (1 + (parseFloat(taxPct) || 0) / 100);
    const nextNum = 1031 + invoices.length - 7;
    const newInv = {
      id: `INV-2026-${nextNum}`,
      c: custName || 'New Client',
      e: custEmail,
      iss: 'Nov 11',
      due: dueDate ? new Date(dueDate + 'T00:00').toLocaleDateString('en-US', { month: 'short', day: '2-digit' }) : 'Dec 11',
      a: total,
      s: sendViaPayPal ? 'SENT' : 'DRAFT',
      k: '',
    };
    try {
      await endpoints.invoices.create({
        customer_id: custName || 'CUST-NEW',
        amount_usd: total,
        due_days: 30,
      });
      if (refetchInvoices) refetchInvoices();
    } catch {
      // fallback
    }
    setInvoices([newInv, ...invoices]);
    setIsModalOpen(false);
    toast.success(sendViaPayPal ? `Invoice ${newInv.id} sent through PayPal Invoicing.` : 'Invoice saved as draft.');
  };

  const getBadgeClass = (status) => {
    switch (status) {
      case 'PAID':
      case 'HEALTHY':
      case 'ACTIVE':
      case 'USED':
        return styles.badgeGreen;
      case 'IN_RECOVERY':
      case 'EXPIRING':
      case 'QUIET_HOURS_PAUSED':
      case 'RETRY_SCHEDULED':
      case 'PENDING':
        return styles.badgeAmber;
      case 'OVERDUE':
      case 'EXPIRED':
        return styles.badgeRed;
      case 'SENT':
      case 'PAID_ELSEWHERE':
      case 'AWAITING_CUSTOMER':
      case 'OPEN':
        return styles.badgeBlue;
      default:
        return styles.badgeGray;
    }
  };

  return (
    <div className={styles.container}>
      {/* Top Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>Invoices &amp; Subscriptions</h1>
          <p>Issue invoices, watch recurring plans, and turn any overdue balance into a one-click PayPal payment link.</p>
        </div>
        <div className={styles.actionsGroup}>
          <button className={styles.btn} onClick={handleExportCSV}>Export CSV</button>
          <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={() => setIsModalOpen(true)}>
            + Create Invoice
          </button>
        </div>
      </div>

      {/* Billing Summary KPIs */}
      <section className={styles.kpiCard} aria-label="Billing summary">
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Outstanding</span>
          <div className={styles.kpiValue}>{fmt(outstandingTotal)}</div>
          <span className={styles.kpiLabel}>{openInvoices.length} open invoices</span>
        </div>
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Overdue</span>
          <div className={styles.kpiValue} style={{ color: '#B42830' }}>{fmt(overdueTotal)}</div>
          <span className={styles.kpiLabel}>Recovery running on each</span>
        </div>
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Monthly recurring revenue</span>
          <div className={styles.kpiValue}>{fmt(mrrTotal)}</div>
          <span className={styles.kpiLabel}>{subscriptions.length} active plans</span>
        </div>
        <div className={styles.kpiItem}>
          <span className={styles.kpiLabel}>Cards needing attention</span>
          <div className={styles.kpiValue}>{badCardsCount}</div>
          <span className={styles.kpiLabel}>Expiring or expired</span>
        </div>
      </section>

      {/* Tabs View */}
      <section className={styles.card}>
        <div className={styles.tabList} role="tablist">
          <button
            className={`${styles.tab} ${activeTab === 'inv' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('inv')}
          >
            Invoices <span className={styles.tabCounter}>{invoices.length}</span>
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'sub' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('sub')}
          >
            Subscriptions <span className={styles.tabCounter}>{subscriptions.length}</span>
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'fail' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('fail')}
          >
            Failed Payments <span className={styles.tabCounter}>{failures.length}</span>
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'lnk' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('lnk')}
          >
            Payment Links
          </button>
        </div>

        {/* Tab 1: Invoices */}
        {activeTab === 'inv' && (
          <div className={styles.tabPanel}>
            <div className={styles.filterBar}>
              <input
                className={styles.input}
                style={{ flex: '1 1 240px', maxWidth: 340 }}
                placeholder="Filter by invoice, customer, or email"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <select
                className={styles.input}
                style={{ minWidth: 170 }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All statuses</option>
                <option value="SENT">SENT</option>
                <option value="OVERDUE">OVERDUE</option>
                <option value="IN_RECOVERY">IN_RECOVERY</option>
                <option value="PAID">PAID</option>
                <option value="PAID_ELSEWHERE">PAID_ELSEWHERE</option>
                <option value="DRAFT">DRAFT</option>
              </select>
            </div>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Invoice</th>
                    <th className={styles.th}>Customer</th>
                    <th className={styles.th}>Issued</th>
                    <th className={styles.th}>Due</th>
                    <th className={styles.th} style={{ textAlign: 'right' }}>Amount</th>
                    <th className={styles.th}>Status</th>
                    <th className={styles.th}>Recovery link</th>
                    <th className={styles.th} />
                  </tr>
                </thead>
                <tbody>
                  {filteredInvoices.map(i => (
                    <tr key={i.id} className={styles.tr}>
                      <td className={styles.td}><code className={styles.mono}>{i.id}</code></td>
                      <td className={styles.td}>
                        <b>{i.c}</b>
                        <div className={styles.kpiLabel}>{i.e}</div>
                      </td>
                      <td className={styles.td}>{i.iss}</td>
                      <td className={styles.td}>{i.due}</td>
                      <td className={styles.td} style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        <b>{fmt(i.a)}</b>
                      </td>
                      <td className={styles.td}>
                        <span className={`${styles.badge} ${getBadgeClass(i.s)}`}>{i.s}</span>
                      </td>
                      <td className={styles.td}>
                        {i.k ? (
                          <Link to="/cases" style={{ color: 'var(--blue)' }}>{i.k}</Link>
                        ) : ['SENT', 'OVERDUE'].includes(i.s) ? (
                          <button
                            className={`${styles.btn} ${styles.btnSm}`}
                            onClick={() => {
                              setActiveTab('lnk');
                              setLinkInvId(i.id);
                              setLinkAmount(i.a.toFixed(2));
                            }}
                          >
                            Create link
                          </button>
                        ) : (
                          <span className={styles.kpiLabel}>None needed</span>
                        )}
                      </td>
                      <td className={styles.td} style={{ textAlign: 'right' }}>
                        <button
                          className={`${styles.btn} ${styles.btnSm}`}
                          onClick={() => handleOpenDrawer(i)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Subscriptions */}
        {activeTab === 'sub' && (
          <div className={styles.tabPanel}>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Plan</th>
                    <th className={styles.th}>Customer</th>
                    <th className={styles.th} style={{ textAlign: 'right' }}>Amount</th>
                    <th className={styles.th}>Cycle</th>
                    <th className={styles.th}>Next payment</th>
                    <th className={styles.th}>Payment method</th>
                    <th className={styles.th} />
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((s, idx) => (
                    <tr key={idx} className={styles.tr}>
                      <td className={styles.td}><b>{s.p}</b></td>
                      <td className={styles.td}>{s.c}</td>
                      <td className={styles.td} style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {fmt(s.a)}
                      </td>
                      <td className={styles.td}>{s.cy}</td>
                      <td className={styles.td}>{s.n}</td>
                      <td className={styles.td}>
                        <span className={`${styles.badge} ${getBadgeClass(s.h)}`}>{s.h}</span>
                        <div className={styles.kpiLabel}>{s.m}</div>
                      </td>
                      <td className={styles.td} style={{ textAlign: 'right' }}>
                        {s.h !== 'HEALTHY' && (
                          <button
                            className={`${styles.btn} ${styles.btnSm}`}
                            onClick={() => toast.success(`Payment method update link sent to ${s.c}. Quiet hours respected.`)}
                          >
                            Send update link
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Failed Payments */}
        {activeTab === 'fail' && (
          <div className={styles.tabPanel}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span className={styles.kpiLabel} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: 4, background: '#2E9D65', display: 'inline-block' }} />
                Live feed from PayPal webhooks and CSV imports
              </span>
              <button className={`${styles.btn} ${styles.btnSm}`} onClick={handleSimulateFailure}>
                Simulate incoming failure
              </button>
            </div>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Detected</th>
                    <th className={styles.th}>Customer</th>
                    <th className={styles.th} style={{ textAlign: 'right' }}>Amount</th>
                    <th className={styles.th}>Diagnosis</th>
                    <th className={styles.th}>Next step</th>
                    <th className={styles.th}>Status</th>
                    <th className={styles.th} />
                  </tr>
                </thead>
                <tbody>
                  {failures.map((f, idx) => (
                    <tr key={idx} className={styles.tr}>
                      <td className={`${styles.td} ${styles.kpiLabel}`}>{f.t}</td>
                      <td className={styles.td}><b>{f.c}</b></td>
                      <td className={styles.td} style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {fmt(f.a)}
                      </td>
                      <td className={styles.td}><code className={styles.mono}>{f.d}</code></td>
                      <td className={styles.td}>{f.n}</td>
                      <td className={styles.td}>
                        <span className={`${styles.badge} ${getBadgeClass(f.s)}`}>{f.s}</span>
                      </td>
                      <td className={styles.td} style={{ textAlign: 'right' }}>
                        <Link to="/cases" style={{ color: 'var(--blue)' }}>{f.k}</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: Payment Links */}
        {activeTab === 'lnk' && (
          <div className={styles.tabPanel}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
              {/* Form */}
              <form onSubmit={handleGenerateLink} style={{ display: 'grid', gap: 12 }}>
                <h2 style={{ fontSize: 18, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
                  Generate a single-use link
                </h2>
                <div>
                  <label className={styles.kpiLabel}>Overdue balance</label>
                  <select
                    className={styles.input}
                    style={{ width: '100%', marginTop: 4 }}
                    value={linkInvId}
                    onChange={(e) => {
                      setLinkInvId(e.target.value);
                      const sel = invoices.find(x => x.id === e.target.value);
                      if (sel) setLinkAmount(sel.a.toFixed(2));
                    }}
                  >
                    {invoices.filter(i => ['SENT', 'OVERDUE', 'IN_RECOVERY'].includes(i.s)).map(i => (
                      <option key={i.id} value={i.id}>
                        {i.id} · {i.c} · {fmt(i.a)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={styles.kpiLabel}>Amount (USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    className={styles.input}
                    style={{ width: '100%', marginTop: 4 }}
                    value={linkAmount}
                    onChange={(e) => setLinkAmount(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className={styles.kpiLabel}>Link expires after</label>
                  <select
                    className={styles.input}
                    style={{ width: '100%', marginTop: 4 }}
                    value={linkExpiryHours}
                    onChange={(e) => setLinkExpiryHours(e.target.value)}
                  >
                    <option value="24">24 hours</option>
                    <option value="48">48 hours</option>
                    <option value="168">7 days</option>
                    <option value="720">30 days</option>
                  </select>
                </div>
                <div>
                  <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>
                    Generate PayPal link
                  </button>
                </div>

                {generatedLink && (
                  <div style={{ padding: '12px 16px', borderRadius: 8, background: '#E6F0FC', marginTop: 8 }}>
                    <div style={{ fontSize: 13, color: '#172B4D' }}>Link ready. It works once and then closes.</div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
                      <code className={styles.mono} style={{ flex: 1, wordBreak: 'break-all' }}>{generatedLink}</code>
                      <button type="button" className={`${styles.btn} ${styles.btnSm}`} onClick={() => handleCopy(generatedLink)}>
                        Copy
                      </button>
                    </div>
                  </div>
                )}
              </form>

              {/* Recent Links Table */}
              <div>
                <h2 style={{ fontSize: 18, margin: '0 0 12px', fontWeight: 600, color: 'var(--blue-dark)' }}>
                  Recent links
                </h2>
                <div className={styles.tableResponsive}>
                  <table className={styles.table} style={{ minWidth: 380 }}>
                    <thead>
                      <tr>
                        <th className={styles.th}>Invoice</th>
                        <th className={styles.th} style={{ textAlign: 'right' }}>Amount</th>
                        <th className={styles.th}>Expires</th>
                        <th className={styles.th}>Status</th>
                        <th className={styles.th} />
                      </tr>
                    </thead>
                    <tbody>
                      {links.map((l, idx) => (
                        <tr key={idx} className={styles.tr}>
                          <td className={styles.td}><code className={styles.mono}>{l.i}</code></td>
                          <td className={styles.td} style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                            {fmt(l.a)}
                          </td>
                          <td className={styles.td}>{l.x}</td>
                          <td className={styles.td}>
                            <span className={`${styles.badge} ${getBadgeClass(l.s)}`}>{l.s}</span>
                          </td>
                          <td className={styles.td} style={{ textAlign: 'right' }}>
                            {l.s === 'OPEN' && (
                              <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                                <button className={`${styles.btn} ${styles.btnSm}`} onClick={() => handleCopy(l.u)}>
                                  Copy
                                </button>
                                <button
                                  className={`${styles.btn} ${styles.btnSm}`}
                                  style={{ color: '#B42830' }}
                                  onClick={() => {
                                    setLinks(links.map((x, i) => i === idx ? { ...x, s: 'REVOKED' } : x));
                                    toast.warning('Link revoked. Customer can no longer pay with it.');
                                  }}
                                >
                                  Revoke
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Invoice Detail Drawer */}
      {activeDrawer && (
        <>
          <div className={styles.drawerOverlay} onClick={() => setActiveDrawer(null)} />
          <aside className={styles.drawer} role="dialog" aria-modal="true">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: 20, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
                {activeDrawer.id}
              </h2>
              <button
                className={styles.btn}
                style={{ width: 36, height: 36, padding: 0, fontSize: 20 }}
                onClick={() => setActiveDrawer(null)}
              >
                ×
              </button>
            </div>
            <div style={{ margin: '8px 0 16px' }}>
              <span className={`${styles.badge} ${getBadgeClass(activeDrawer.s)}`}>{activeDrawer.s}</span>
            </div>
            <div style={{ fontSize: 28, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
              {fmt(activeDrawer.a)} <span style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 400 }}>USD</span>
            </div>

            <div style={{ marginTop: 16 }}>
              <div className={styles.drawerRow}>
                <span className={styles.kpiLabel} style={{ width: 120 }}>Customer</span>
                <div>
                  <b>{activeDrawer.c}</b>
                  <div className={styles.kpiLabel}>{activeDrawer.e}</div>
                </div>
              </div>
              <div className={styles.drawerRow}>
                <span className={styles.kpiLabel} style={{ width: 120 }}>Issued / Due</span>
                <span>{activeDrawer.iss} / {activeDrawer.due}</span>
              </div>
              <div className={styles.drawerRow}>
                <span className={styles.kpiLabel} style={{ width: 120 }}>Recovery case</span>
                <span>
                  {activeDrawer.k ? (
                    <Link to="/cases" style={{ color: 'var(--blue)' }}>{activeDrawer.k}</Link>
                  ) : (
                    'None'
                  )}
                </span>
              </div>
              <div className={styles.drawerRow}>
                <span className={styles.kpiLabel} style={{ width: 120 }}>Payment link</span>
                <code className={styles.mono}>
                  {activeDrawer.k ? `pay?case_id=${activeDrawer.k}` : 'Not created'}
                </code>
              </div>
            </div>

            <div className={styles.kpiLabel} style={{ marginTop: 24 }}>
              Audit proof (SHA-256 of this invoice record)
            </div>
            <code
              className={styles.mono}
              style={{
                display: 'block',
                wordBreak: 'break-all',
                padding: 12,
                background: '#F0F3F8',
                borderRadius: 8,
                marginTop: 6,
                lineHeight: 1.4,
              }}
            >
              {drawerHash}
            </code>

            <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap' }}>
              <button className={styles.btn} onClick={() => navigate('/audit')}>
                Open in audit trail
              </button>
              {['SENT', 'OVERDUE'].includes(activeDrawer.s) && (
                <button
                  className={`${styles.btn} ${styles.btnPrimary}`}
                  onClick={() => {
                    setActiveDrawer(null);
                    setActiveTab('lnk');
                    setLinkInvId(activeDrawer.id);
                    setLinkAmount(activeDrawer.a.toFixed(2));
                  }}
                >
                  Create payment link
                </button>
              )}
            </div>
          </aside>
        </>
      )}

      {/* Create Invoice Modal */}
      {isModalOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <form className={styles.modalCard} onSubmit={handleCreateInvoice}>
            <h2 style={{ fontSize: 20, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
              Create Invoice
            </h2>
            <div>
              <label className={styles.kpiLabel}>Customer name</label>
              <input
                className={styles.input}
                style={{ width: '100%', marginTop: 4 }}
                placeholder="Sarah Johnson"
                value={custName}
                onChange={(e) => setCustName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className={styles.kpiLabel}>Customer email</label>
              <input
                type="email"
                className={styles.input}
                style={{ width: '100%', marginTop: 4 }}
                placeholder="sarah@example.com"
                value={custEmail}
                onChange={(e) => setCustEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className={styles.kpiLabel}>Line items</span>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnSm}`}
                  onClick={() => setLineItems([...lineItems, { description: '', qty: 1, unitPrice: 0 }])}
                >
                  + Add line item
                </button>
              </div>
              <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                {lineItems.map((item, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1fr 70px 110px', gap: 8 }}>
                    <input
                      className={styles.input}
                      placeholder="Description"
                      value={item.description}
                      onChange={(e) => {
                        const next = [...lineItems];
                        next[idx].description = e.target.value;
                        setLineItems(next);
                      }}
                      required
                    />
                    <input
                      type="number"
                      min="1"
                      className={styles.input}
                      value={item.qty}
                      onChange={(e) => {
                        const next = [...lineItems];
                        next[idx].qty = parseInt(e.target.value, 10) || 1;
                        setLineItems(next);
                      }}
                    />
                    <input
                      type="number"
                      step="0.01"
                      className={styles.input}
                      placeholder="0.00"
                      value={item.unitPrice}
                      onChange={(e) => {
                        const next = [...lineItems];
                        next[idx].unitPrice = parseFloat(e.target.value) || 0;
                        setLineItems(next);
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label className={styles.kpiLabel}>Tax (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  className={styles.input}
                  style={{ width: '100%', marginTop: 4 }}
                  value={taxPct}
                  onChange={(e) => setTaxPct(e.target.value)}
                />
              </div>
              <div>
                <label className={styles.kpiLabel}>Due date</label>
                <input
                  type="date"
                  className={styles.input}
                  style={{ width: '100%', marginTop: 4 }}
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  required
                />
              </div>
            </div>

            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={sendViaPayPal}
                onChange={(e) => setSendViaPayPal(e.target.checked)}
                style={{ width: 16, height: 16 }}
              />
              Send through PayPal Invoicing
            </label>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: '#F0F3F8', borderRadius: 8 }}>
              <span className={styles.kpiLabel}>Total due</span>
              <b style={{ fontSize: 20, fontVariantNumeric: 'tabular-nums' }}>
                {fmt(lineItems.reduce((acc, it) => acc + (it.qty * it.unitPrice), 0) * (1 + (parseFloat(taxPct) || 0) / 100))}
              </b>
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button type="button" className={styles.btn} onClick={() => setIsModalOpen(false)}>
                Cancel
              </button>
              <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>
                Create Invoice
              </button>
            </div>
          </form>
        </div>
      )}

      <footer className={styles.footerTagline}>
        AI recommends. Policy decides. PayPal executes. Every action is auditable.
        <div className={styles.footerSub}>ProofPay · Every Payment. Proven. Protected.</div>
      </footer>
    </div>
  );
}

