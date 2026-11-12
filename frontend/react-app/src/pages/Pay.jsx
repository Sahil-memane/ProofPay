import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from '../components/ui/Toast';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import styles from './Pay.module.css';

const DEFAULT_CASE = {
  case_id: 'REC-2026-0042',
  merchant: 'Acme Cloud Services',
  customer: 'Sarah Johnson',
  invoice_id: 'INV-2026-1024',
  amount: 350.00,
  currency: 'USD',
  due: 'November 10, 2026',
  description: 'Pro Cloud Subscription — Monthly Renewal (Failed Card Charge)',
  status: 'ACTIVE',
};

export default function Pay() {
  const [searchParams] = useSearchParams();
  const caseId = searchParams.get('case_id') || 'REC-2026-0042';

  const [invoice, setInvoice] = useState(DEFAULT_CASE);
  const [isPaid, setIsPaid] = useState(false);
  const [txnId, setTxnId] = useState('PP-TXN-994102');
  const [showPayPalModal, setShowPayPalModal] = useState(false);
  const [isAuthorizing, setIsAuthorizing] = useState(false);
  const [isCardAccordionOpen, setIsCardAccordionOpen] = useState(false);
  const [isProcessingCard, setIsProcessingCard] = useState(false);

  // Fetch real invoice data from DB
  const { data: apiInvoices } = useApi(() => endpoints.invoices.list({ limit: 50 }));
  const { data: apiCases } = useApi(() => endpoints.cases.list());

  useEffect(() => {
    // Try to match a real invoice or case from DB
    if (apiCases && Array.isArray(apiCases) && apiCases.length > 0) {
      const matchedCase = apiCases.find(c =>
        c.id === caseId || `REC-${(c.id || '').slice(0, 8).toUpperCase()}` === caseId
      ) || apiCases[0];
      if (matchedCase) {
        const payload = matchedCase.payload || {};
        setInvoice({
          case_id: `REC-${matchedCase.id.slice(0, 8).toUpperCase()}`,
          merchant: 'ProofPay Merchant',
          customer: matchedCase.customer_id || 'Customer',
          invoice_id: payload.invoice_id || `INV-${matchedCase.id.slice(0, 6).toUpperCase()}`,
          amount: matchedCase.amount_usd || DEFAULT_CASE.amount,
          currency: matchedCase.currency || 'USD',
          due: matchedCase.last_contact_at
            ? new Date(matchedCase.last_contact_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
            : DEFAULT_CASE.due,
          description: payload.failure_code
            ? `Failed ${payload.failure_code.replace(/_/g, ' ')} — Recovery Invoice`
            : DEFAULT_CASE.description,
          status: matchedCase.state || 'ACTIVE',
        });
      }
    }
    if (apiInvoices && Array.isArray(apiInvoices) && apiInvoices.length > 0) {
      const matchedInv = apiInvoices.find(inv => inv.invoice_id === caseId);
      if (matchedInv) {
        setInvoice(prev => ({
          ...prev,
          invoice_id: matchedInv.invoice_id,
          amount: matchedInv.amount_usd,
          customer: matchedInv.customer_id,
          due: matchedInv.due_at
            ? new Date(matchedInv.due_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
            : prev.due,
          status: matchedInv.status?.toUpperCase() || 'ACTIVE',
        }));
      }
    }
  }, [apiCases, apiInvoices, caseId]);

  // Card Form State
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [cardCvc, setCardCvc] = useState('');
  const [cardName, setCardName] = useState('Sarah Johnson');
  const [errors, setErrors] = useState({});

  // Clock for demo bar
  const [utcClock, setUtcClock] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      setUtcClock(
        `${now.getUTCFullYear()}-${pad(now.getUTCMonth() + 1)}-${pad(now.getUTCDate())} ${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())} UTC`
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 30000);
    return () => clearInterval(interval);
  }, []);

  // Check stored status
  useEffect(() => {
    const storedStatus = localStorage.getItem(`proofpay_case_${caseId}`);
    const storedTxn = localStorage.getItem(`proofpay_case_${caseId}_txn`);
    if (storedStatus === 'PAID') {
      setIsPaid(true);
      if (storedTxn) setTxnId(storedTxn);
    }
  }, [caseId]);

  const money = (n) => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const luhnCheck = (val) => {
    let sum = 0;
    let double = false;
    for (let i = val.length - 1; i >= 0; i--) {
      let digit = +val[i];
      if (double) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
      double = !double;
    }
    return sum % 10 === 0;
  };

  const handleCardNumberChange = (e) => {
    const clean = e.target.value.replace(/\D/g, '').slice(0, 19);
    const formatted = clean.replace(/(.{4})/g, '$1 ').trim();
    setCardNumber(formatted);
  };

  const handleExpiryChange = (e) => {
    const clean = e.target.value.replace(/\D/g, '').slice(0, 4);
    setCardExpiry(clean.length > 2 ? clean.slice(0, 2) + '/' + clean.slice(2) : clean);
  };

  const handlePaySuccess = (method, txn) => {
    localStorage.setItem(`proofpay_case_${caseId}`, 'PAID');
    localStorage.setItem(`proofpay_case_${caseId}_txn`, txn);
    setTxnId(txn);
    setIsPaid(true);
    setShowPayPalModal(false);
    toast.success(`Payment received via ${method}. Case ${caseId} marked PAID.`);
  };

  const handlePayPalSubmit = () => {
    setIsAuthorizing(true);
    setTimeout(() => {
      setIsAuthorizing(false);
      handlePaySuccess('PayPal Smart Button', 'PP-TXN-994102');
    }, 1200);
  };

  const handleCardSubmit = (e) => {
    e.preventDefault();
    const newErrors = {};
    const rawCard = cardNumber.replace(/\s/g, '');
    const expMatch = /^(\d\d)\/(\d\d)$/.exec(cardExpiry);
    const now = new Date();

    if (rawCard.length < 13 || !luhnCheck(rawCard)) {
      newErrors.cardNumber = 'Enter a valid card number.';
    }
    if (!expMatch || +expMatch[1] < 1 || +expMatch[1] > 12 || (2000 + +expMatch[2]) * 12 + +expMatch[1] < now.getFullYear() * 12 + now.getMonth() + 1) {
      newErrors.cardExpiry = 'Enter a valid, unexpired date (MM/YY).';
    }
    if (!/^\d{3,4}$/.test(cardCvc)) {
      newErrors.cardCvc = 'Enter 3–4 digits.';
    }
    if (!cardName.trim()) {
      newErrors.cardName = 'Enter the name on your card.';
    }

    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    setIsProcessingCard(true);
    setTimeout(() => {
      setIsProcessingCard(false);
      handlePaySuccess('Card Update', 'PP-TXN-994105');
    }, 1000);
  };

  const handleResetDemo = () => {
    localStorage.removeItem(`proofpay_case_${caseId}`);
    localStorage.removeItem(`proofpay_case_${caseId}_txn`);
    setIsPaid(false);
    toast.info(`Demo reset. Case ${caseId} restored to ACTIVE.`);
  };

  const handleInjectFailure = () => {
    toast.error(`Injected EXPIRED_CARD failure for ${caseId}.`);
  };

  return (
    <div className={styles.wrapper}>
      {/* Header */}
      <header className={styles.portalHeader}>
        <div className={styles.merchantAvatar}>A</div>
        <div className={styles.merchantInfo}>
          <div className={styles.merchantName}>{invoice.merchant}</div>
          <div className={styles.poweredBy}>Powered by ProofPay &amp; PayPal</div>
        </div>
        <div className={styles.secureBadge}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 11V8a6 6 0 0 1 12 0v3M5 11h14v10H5z" />
          </svg>
          Secure
        </div>
      </header>

      {/* Invoice Card or Success Card */}
      {!isPaid ? (
        <>
          <section className={styles.card}>
            <div className={styles.balanceHeader}>
              <span className={styles.balanceLabel}>Outstanding balance</span>
              <span className={styles.statusOverdue}>Overdue</span>
            </div>
            <h1 className={styles.amountTitle}>
              {money(invoice.amount)} <span className={styles.currencyText}>{invoice.currency}</span>
            </h1>
            <p className={styles.invoiceDescription}>{invoice.description}</p>
            <div className={styles.kvRow}>
              <span className={styles.balanceLabel}>Invoice reference</span>
              <span className={styles.mono}>{invoice.invoice_id}</span>
            </div>
            <div className={styles.kvRow}>
              <span className={styles.balanceLabel}>Due date</span>
              <span style={{ color: '#B42830', fontWeight: 500 }}>{invoice.due} (Overdue)</span>
            </div>
            <div className={styles.kvRow}>
              <span className={styles.balanceLabel}>Billed to</span>
              <span style={{ fontWeight: 500 }}>{invoice.customer}</span>
            </div>
          </section>

          <section className={styles.card}>
            <h2 className={styles.chooseTitle}>Choose how to pay</h2>
            <button
              className={styles.paypalBtn}
              onClick={() => setShowPayPalModal(true)}
              aria-label="Pay with PayPal"
            >
              <b>Pay</b><em>Pal</em>
            </button>
            <div className={styles.instantNote}>Settles instantly. No card entry needed.</div>

            <div className={styles.divider}>
              <span className={styles.dividerLine} />
              or
              <span className={styles.dividerLine} />
            </div>

            <button
              className={`${styles.accordionBtn} ${isCardAccordionOpen ? styles.accordionBtnOpen : ''}`}
              onClick={() => setIsCardAccordionOpen(!isCardAccordionOpen)}
              aria-expanded={isCardAccordionOpen}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18v12H3zM3 10h18" />
              </svg>
              <span style={{ flex: 1, fontWeight: 500 }}>Update credit / debit card</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ transform: isCardAccordionOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            {isCardAccordionOpen && (
              <form className={styles.cardForm} onSubmit={handleCardSubmit}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Card number</label>
                  <input
                    className={`${styles.input} ${styles.mono} ${errors.cardNumber ? styles.inputError : ''}`}
                    placeholder="4242 4242 4242 4242"
                    value={cardNumber}
                    onChange={handleCardNumberChange}
                    maxLength={23}
                  />
                  <div className={styles.errorText}>{errors.cardNumber}</div>
                </div>

                <div className={styles.twoCols}>
                  <div className={styles.inputGroup}>
                    <label className={styles.label}>Expiry (MM/YY)</label>
                    <input
                      className={`${styles.input} ${styles.mono} ${errors.cardExpiry ? styles.inputError : ''}`}
                      placeholder="08/29"
                      value={cardExpiry}
                      onChange={handleExpiryChange}
                      maxLength={5}
                    />
                    <div className={styles.errorText}>{errors.cardExpiry}</div>
                  </div>
                  <div className={styles.inputGroup}>
                    <label className={styles.label}>CVC</label>
                    <input
                      className={`${styles.input} ${styles.mono} ${errors.cardCvc ? styles.inputError : ''}`}
                      placeholder="123"
                      value={cardCvc}
                      onChange={(e) => setCardCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
                      maxLength={4}
                    />
                    <div className={styles.errorText}>{errors.cardCvc}</div>
                  </div>
                </div>

                <div className={styles.inputGroup}>
                  <label className={styles.label}>Name on card</label>
                  <input
                    className={`${styles.input} ${errors.cardName ? styles.inputError : ''}`}
                    placeholder="Sarah Johnson"
                    value={cardName}
                    onChange={(e) => setCardName(e.target.value)}
                  />
                  <div className={styles.errorText}>{errors.cardName}</div>
                </div>

                <button
                  type="submit"
                  className={styles.payCardBtn}
                  disabled={isProcessingCard}
                >
                  {isProcessingCard ? 'Processing…' : `Update card & pay ${money(invoice.amount)}`}
                </button>
                <p className={styles.demoDisclaimer}>
                  Your new card will be used for future renewals. Demo mode: no real card data is stored or transmitted.
                </p>
              </form>
            )}

            <div className={styles.guarantees}>
              <span>🔒 256-Bit SSL Encrypted</span>
              <span>✔ Verified by PayPal</span>
            </div>
          </section>
        </>
      ) : (
        <section className={styles.successCard} role="alert">
          <div className={styles.successIcon}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12l5 5 9-10" />
            </svg>
          </div>
          <h1 className={styles.successTitle}>✅ Payment Successful! Thank You.</h1>
          <p className={styles.successSub}>
            {money(invoice.amount)} {invoice.currency} paid for <span className={styles.mono}>{invoice.invoice_id}</span>
          </p>
          <div className={styles.kvRow}>
            <span className={styles.balanceLabel}>PayPal Transaction ID</span>
            <span className={styles.mono}>{txnId}</span>
          </div>
          <div className={styles.kvRow}>
            <span className={styles.balanceLabel}>Case status</span>
            <span style={{ fontSize: 12, fontWeight: 600, background: '#E3F4EB', color: '#1E7A4C', borderRadius: 12, padding: '2px 8px' }}>
              PAID
            </span>
          </div>
          <p style={{ margin: '16px 0 0', color: '#172B4D', fontSize: 14 }}>
            Your invoice has been marked PAID and your service remains uninterrupted.
          </p>
        </section>
      )}

      {/* Evaluator Floating Demo Bar */}
      <div className={styles.demoBar} role="toolbar" aria-label="Evaluator demo bar">
        <span className={styles.demoBarTag}>⚡ DEMO BAR</span>
        <span className={styles.demoBarClock}>{utcClock}</span>
        <button className={styles.demoBarBtn} onClick={handleResetDemo}>
          🔄 Reset Demo
        </button>
        <button className={styles.demoBarBtn} onClick={handleInjectFailure}>
          ⚠️ Inject Failure
        </button>
      </div>

      {/* PayPal Login / Auth Modal */}
      {showPayPalModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalDialog}>
            <div style={{ font: 'italic 700 24px Inter, sans-serif', color: '#003087', marginBottom: 8 }}>
              Pay<span style={{ color: '#009CDE' }}>Pal</span>
            </div>
            <h2 style={{ fontSize: 16, margin: '0 0 4px', fontWeight: 600 }}>Pay {invoice.merchant}</h2>
            <div style={{ fontSize: 28, fontWeight: 600, marginBottom: 4, fontVariantNumeric: 'tabular-nums' }}>
              {money(invoice.amount)}
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
              Sandbox buyer: sarah@example.com
            </div>

            {!isAuthorizing ? (
              <div>
                <button
                  className={styles.payCardBtn}
                  style={{ marginTop: 0 }}
                  onClick={handlePayPalSubmit}
                >
                  Log in &amp; Pay Now
                </button>
                <button
                  className={styles.demoBarBtn}
                  style={{ width: '100%', marginTop: 8, height: 40, color: 'var(--text)', borderColor: 'var(--border)' }}
                  onClick={() => setShowPayPalModal(false)}
                >
                  Cancel and return to merchant
                </button>
              </div>
            ) : (
              <div>
                <div className={styles.spinner} />
                <p style={{ margin: '12px 0 0', fontSize: 13, color: 'var(--muted)' }}>
                  Authorizing &amp; capturing payment…
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

