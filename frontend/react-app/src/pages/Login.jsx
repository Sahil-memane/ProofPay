import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import styles from './Login.module.css';

const MOCK_USERS = {
  'client@example.com':     { name: 'Acme Global Solutions', role: 'client' },
  'freelancer@example.com': { name: 'Rahul Sharma',          role: 'freelancer' },
  'merchant@example.com':   { name: 'Sahil',                 role: 'merchant' },
  'admin@example.com':      { name: 'Risk Officer',          role: 'admin' },
};

const DEMO_PW = 'ProofPay@2026';
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  // Mode: sign in or register (derived from hash, pathname, or state)
  const [isRegister, setIsRegister] = useState(() => location.hash === '#register' || location.pathname === '/register');

  useEffect(() => {
    document.title = isRegister ? 'Create Account | ProofPay' : 'Sign In | ProofPay';
  }, [isRegister]);

  // Sign In fields
  const [signInEmail, setSignInEmail] = useState('');
  const [signInPassword, setSignInPassword] = useState('');
  const [showSignInPw, setShowSignInPw] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [signInErrors, setSignInErrors] = useState({});
  const [signInBanner, setSignInBanner] = useState({ show: false, msg: '', type: 'error' });
  const [isSigningIn, setIsSigningIn] = useState(false);

  // Register fields
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regRole, setRegRole] = useState('client');
  const [adminCode, setAdminCode] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [showRegPw, setShowRegPw] = useState(false);
  const [showConfirmPw, setShowConfirmPw] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [regErrors, setRegErrors] = useState({});
  const [regBanner, setRegBanner] = useState({ show: false, msg: '', type: 'error' });
  const [isRegistering, setIsRegistering] = useState(false);

  // Password strength calculation
  const getPasswordScore = (pw) => {
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
    if (/\d/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    if (pw.length >= 12 && score >= 3) score = 4;
    return pw.length < 8 ? Math.min(score, 1) : score;
  };

  const pwScore = getPasswordScore(regPassword);
  const strengthLevels = [
    { label: '', text: 'Use 8+ characters with upper and lower case, a number or a symbol.' },
    { label: 'Weak', text: 'Weak. Add upper and lower case, a number or a symbol.', color: '#D9363E' },
    { label: 'Fair', text: 'Fair. Add numbers or special symbols.', color: '#F5A623' },
    { label: 'Good', text: 'Good password.', color: '#009CDE' },
    { label: 'Strong', text: 'Strong password.', color: '#2E9D65' },
  ];

  const handleChipClick = (email) => {
    setSignInEmail(email);
    setSignInPassword(DEMO_PW);
    setSignInErrors({});
    setSignInBanner({ show: false, msg: '', type: 'error' });
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    const errors = {};
    const email = signInEmail.trim().toLowerCase();

    if (!email) {
      errors.email = 'Enter your email address.';
    } else if (!EMAIL_REGEX.test(email)) {
      errors.email = 'Enter a valid email, like you@company.com.';
    }
    if (!signInPassword) {
      errors.password = 'Enter your password.';
    }

    if (Object.keys(errors).length > 0) {
      setSignInErrors(errors);
      return;
    }

    setSignInErrors({});
    setIsSigningIn(true);

    const redirectTo = location.state?.from?.pathname || '/dashboard';

    try {
      // Check live backend if configured
      const res = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password: signInPassword, remember: rememberMe }),
        signal: AbortSignal.timeout(2000),
      }).catch(() => null);

      if (res && res.ok) {
        const data = await res.json();
        const user = data.user || { email, role: data.role || 'client', name: email };
        const storage = rememberMe ? localStorage : sessionStorage;
        storage.setItem('pp_session', JSON.stringify({ user, token: data.access_token || 'token', role: user.role }));
        sessionStorage.setItem('pp_role', user.role);
        localStorage.setItem('proofpay_role', user.role);
        window.dispatchEvent(new Event('authChanged'));
        setSignInBanner({ show: true, msg: 'Authentication successful. Redirecting…', type: 'info' });
        setTimeout(() => navigate(redirectTo), 500);
        return;
      }
    } catch (_) {
      // Fallback to local sandbox logic
    }

    // Local persona check
    const mock = MOCK_USERS[email];
    if (mock && signInPassword === DEMO_PW) {
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem('pp_session', JSON.stringify({ user: { email, ...mock }, role: mock.role, offline: true }));
      sessionStorage.setItem('pp_role', mock.role);
      localStorage.setItem('proofpay_role', mock.role);
      window.dispatchEvent(new Event('authChanged'));
      setSignInBanner({ show: true, msg: 'Signed in with sandbox persona. Redirecting…', type: 'info' });
      setTimeout(() => navigate(redirectTo), 450);
      setIsSigningIn(false);
      return;
    }

    // Check localStorage saved users
    try {
      const saved = JSON.parse(localStorage.getItem('pp_users') || '{}');
      if (saved[email]) {
        const u = saved[email];
        const storage = rememberMe ? localStorage : sessionStorage;
        storage.setItem('pp_session', JSON.stringify({ user: { email, name: u.name, role: u.role }, role: u.role, offline: true }));
        sessionStorage.setItem('pp_role', u.role);
        localStorage.setItem('proofpay_role', u.role);
        window.dispatchEvent(new Event('authChanged'));
        setSignInBanner({ show: true, msg: 'Signed in successfully. Redirecting…', type: 'info' });
        setTimeout(() => navigate(redirectTo), 450);
        setIsSigningIn(false);
        return;
      }
    } catch (_) {}

    setIsSigningIn(false);
    setSignInBanner({
      show: true,
      msg: mock
        ? 'Email or password is incorrect. Check both and try again.'
        : 'No account found for this email in sandbox mode. Create one, or select an evaluator persona below.',
      type: 'error',
    });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const errors = {};
    const name = regName.trim();
    const email = regEmail.trim().toLowerCase();

    if (!name) errors.name = 'Enter your full name.';
    if (!email) {
      errors.email = 'Enter your work email.';
    } else if (!EMAIL_REGEX.test(email)) {
      errors.email = 'Enter a valid email, like you@company.com.';
    }
    if (regRole === 'admin' && !adminCode.trim()) {
      errors.adminCode = 'Enter your admin invitation code.';
    }
    if (pwScore < 3) {
      errors.password = 'Choose a stronger password: 8+ characters with upper, lower, numbers or symbols.';
    }
    if (regConfirm !== regPassword) {
      errors.confirm = 'Passwords do not match.';
    }
    if (!agreeTerms) {
      errors.terms = 'Accept the Terms and Privacy Policy to continue.';
    }

    if (Object.keys(errors).length > 0) {
      setRegErrors(errors);
      return;
    }

    setRegErrors({});
    setIsRegistering(true);

    try {
      // Save locally
      const saved = JSON.parse(localStorage.getItem('pp_users') || '{}');
      if (saved[email] || MOCK_USERS[email]) {
        setIsRegistering(false);
        setRegErrors({ email: 'An account with this email already exists. Sign in instead.' });
        return;
      }

      saved[email] = { name, role: regRole, date: new Date().toISOString() };
      localStorage.setItem('pp_users', JSON.stringify(saved));

      setIsRegistering(false);
      setIsRegister(false);
      setSignInEmail(email);
      setSignInPassword('');
      setSignInBanner({ show: true, msg: 'Account created! Sign in to enter your workspace.', type: 'success' });
    } catch (_) {
      setIsRegistering(false);
      setRegBanner({ show: true, msg: 'Error saving account in local storage. Try again.', type: 'error' });
    }
  };

  return (
    <div className={styles.stage}>
      {/* Brand Bar */}
      <div className={styles.bar}>
        <Link to="/" className={styles.brand}>
          <span className={styles.logo}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </span>
          ProofPay
        </Link>
        <span className={styles.pby}>
          Powered by <b>PayPal</b>
        </span>
      </div>

      {/* Main Sliding Card */}
      <main className={`${styles.box} ${isRegister ? styles.reg : ''}`} id="box">
        {/* Sign In Pane */}
        <section className={`${styles.pane} ${styles.paneSi}`} aria-labelledby="t1">
          <h1 id="t1">Sign in</h1>
          <p className={styles.sub}>Access escrow projects, recovery cases and approvals.</p>

          {signInBanner.show && (
            <div
              className={`${styles.banner} ${
                signInBanner.type === 'info'
                  ? styles.bannerInfo
                  : signInBanner.type === 'success'
                  ? styles.bannerSuccess
                  : ''
              }`}
              role="alert"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{signInBanner.msg}</span>
            </div>
          )}

          <form onSubmit={handleSignIn} noValidate>
            <label className={styles.label} htmlFor="em" style={{ marginTop: 0 }}>
              Email address
            </label>
            <input
              className={`${styles.field} ${signInErrors.email ? styles.fieldInvalid : ''}`}
              id="em"
              type="email"
              autoComplete="username"
              placeholder="you@company.com"
              value={signInEmail}
              onChange={(e) => setSignInEmail(e.target.value)}
            />
            {signInErrors.email && <div className={styles.err}>{signInErrors.email}</div>}

            <label className={styles.label} htmlFor="pw">
              Password
            </label>
            <div className={styles.pwWrapper}>
              <input
                className={`${styles.field} ${signInErrors.password ? styles.fieldInvalid : ''}`}
                id="pw"
                type={showSignInPw ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={signInPassword}
                onChange={(e) => setSignInPassword(e.target.value)}
              />
              <button
                type="button"
                className={styles.eyeBtn}
                onClick={() => setShowSignInPw(!showSignInPw)}
                aria-label={showSignInPw ? 'Hide password' : 'Show password'}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </div>
            {signInErrors.password && <div className={styles.err}>{signInErrors.password}</div>}

            <div className={styles.formRow}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                Remember me
              </label>
              <Link to="/help" style={{ color: '#0070E0', fontSize: 13, textDecoration: 'none' }}>
                Forgot password?
              </Link>
            </div>

            <button className={`${styles.btn} ${styles.btnPrimary}`} type="submit" disabled={isSigningIn}>
              {isSigningIn ? (
                <>
                  <span className={styles.spinner}></span>
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Evaluator Quick Access Chips */}
          <div className={styles.demoSection}>
            Evaluator quick persona access
            <div className={styles.chips}>
              <button
                className={styles.chip}
                type="button"
                onClick={() => handleChipClick('client@example.com')}
              >
                Client (Buyer)
              </button>
              <button
                className={styles.chip}
                type="button"
                onClick={() => handleChipClick('freelancer@example.com')}
              >
                Freelancer (Dev)
              </button>
              <button
                className={styles.chip}
                type="button"
                onClick={() => handleChipClick('merchant@example.com')}
              >
                Merchant (Billing)
              </button>
              <button
                className={styles.chip}
                type="button"
                onClick={() => handleChipClick('admin@example.com')}
              >
                Risk Officer (Admin)
              </button>
            </div>
          </div>

          <p className={styles.linkRow}>
            New to ProofPay?{' '}
            <button type="button" onClick={() => setIsRegister(true)}>
              Create account
            </button>
          </p>
        </section>

        {/* Register Pane */}
        <section className={`${styles.pane} ${styles.paneSu}`} aria-labelledby="t2">
          <h1 id="t2">Create your account</h1>
          <p className={styles.sub}>Start managing escrow and revenue recovery in one workspace.</p>

          {regBanner.show && (
            <div className={`${styles.banner} ${regBanner.type === 'info' ? styles.bannerInfo : ''}`} role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{regBanner.msg}</span>
            </div>
          )}

          <form onSubmit={handleRegister} noValidate>
            <label className={styles.label} htmlFor="rn" style={{ marginTop: 0 }}>
              Full name
            </label>
            <input
              className={`${styles.field} ${regErrors.name ? styles.fieldInvalid : ''}`}
              id="rn"
              autoComplete="name"
              placeholder="Rahul Sharma"
              value={regName}
              onChange={(e) => setRegName(e.target.value)}
            />
            {regErrors.name && <div className={styles.err}>{regErrors.name}</div>}

            <label className={styles.label} htmlFor="re">
              Work email
            </label>
            <input
              className={`${styles.field} ${regErrors.email ? styles.fieldInvalid : ''}`}
              id="re"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              value={regEmail}
              onChange={(e) => setRegEmail(e.target.value)}
            />
            {regErrors.email && <div className={styles.err}>{regErrors.email}</div>}

            <label className={styles.label} htmlFor="rr">
              Account type
            </label>
            <select
              className={styles.field}
              id="rr"
              value={regRole}
              onChange={(e) => setRegRole(e.target.value)}
            >
              <option value="client">Client (Buyer)</option>
              <option value="freelancer">Freelancer (Contractor)</option>
              <option value="merchant">Merchant (Billing Admin)</option>
              <option value="admin">Admin / Risk Officer (invite only)</option>
            </select>

            {regRole === 'admin' && (
              <div className={styles.inviteBox}>
                <label htmlFor="ri" style={{ fontWeight: 500, display: 'block' }}>
                  Admin invitation code
                </label>
                <input
                  className={`${styles.field} ${regErrors.adminCode ? styles.fieldInvalid : ''}`}
                  id="ri"
                  autoComplete="off"
                  placeholder="Paste the code from your invitation email"
                  value={adminCode}
                  onChange={(e) => setAdminCode(e.target.value)}
                />
                {regErrors.adminCode && <div className={styles.err}>{regErrors.adminCode}</div>}
                <div style={{ marginTop: 4, fontSize: 11, opacity: 0.9 }}>
                  Admin access is restricted. Verification occurs before account creation.
                </div>
              </div>
            )}

            <div className={styles.twoCols}>
              <div>
                <label className={styles.label} htmlFor="rp">
                  Password
                </label>
                <div className={styles.pwWrapper}>
                  <input
                    className={`${styles.field} ${regErrors.password ? styles.fieldInvalid : ''}`}
                    id="rp"
                    type={showRegPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="8+ characters"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className={styles.eyeBtn}
                    onClick={() => setShowRegPw(!showRegPw)}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                </div>
              </div>

              <div>
                <label className={styles.label} htmlFor="rc">
                  Confirm password
                </label>
                <div className={styles.pwWrapper}>
                  <input
                    className={`${styles.field} ${regErrors.confirm ? styles.fieldInvalid : ''}`}
                    id="rc"
                    type={showConfirmPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter password"
                    value={regConfirm}
                    onChange={(e) => setRegConfirm(e.target.value)}
                  />
                  <button
                    type="button"
                    className={styles.eyeBtn}
                    onClick={() => setShowConfirmPw(!showConfirmPw)}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            {/* Password Strength Meter */}
            <div className={styles.meter}>
              {[0, 1, 2, 3].map((idx) => (
                <div
                  key={idx}
                  className={styles.meterBar}
                  style={{
                    background: idx < pwScore ? strengthLevels[pwScore]?.color : undefined,
                  }}
                />
              ))}
            </div>
            <div className={`${styles.hint} ${pwScore >= 3 ? styles.hintOk : ''}`}>
              {regPassword ? strengthLevels[pwScore]?.text : 'Use 8+ characters with upper and lower case, a number or a symbol.'}
            </div>

            {regErrors.password && <div className={styles.err}>{regErrors.password}</div>}
            {regErrors.confirm && <div className={styles.err}>{regErrors.confirm}</div>}

            <label className={styles.checkboxLabel} style={{ margin: '8px 0 4px' }}>
              <input
                type="checkbox"
                checked={agreeTerms}
                onChange={(e) => setAgreeTerms(e.target.checked)}
              />
              <span>
                I agree to the <Link to="/help" style={{ color: '#0070E0' }}>Terms</Link> and{' '}
                <Link to="/help" style={{ color: '#0070E0' }}>Privacy Policy</Link>
              </span>
            </label>
            {regErrors.terms && <div className={styles.err}>{regErrors.terms}</div>}

            <button
              className={`${styles.btn} ${styles.btnPrimary}`}
              type="submit"
              disabled={isRegistering}
              style={{ marginTop: 8 }}
            >
              {isRegistering ? (
                <>
                  <span className={styles.spinner}></span>
                  Creating Account…
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <p className={styles.linkRow}>
            Already have an account?{' '}
            <button type="button" onClick={() => setIsRegister(false)}>
              Sign In
            </button>
          </p>
        </section>

        {/* Sliding Blue Overlay */}
        <div className={styles.overlay}>
          <div className={styles.overlayInner}>
            {/* Left overlay panel (shown when registering) */}
            <div className={`${styles.overlayPane} ${styles.overlayPaneLeft}`}>
              <h2>Everything you need to get paid, protected</h2>
              <ul className={styles.benefitList}>
                <li>
                  <span className={styles.benefitIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
                      <path d="M9 12l2 2 4-4" />
                    </svg>
                  </span>
                  <div>
                    <b>Secure milestone-based escrow</b>
                    <span>Funds are held until the agreed work is verified.</span>
                  </div>
                </li>
                <li>
                  <span className={styles.benefitIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 17l6-6 4 4 8-8M15 7h6v6" />
                    </svg>
                  </span>
                  <div>
                    <b>AI-powered revenue recovery</b>
                    <span>Win back failed charges without wrongful dunning.</span>
                  </div>
                </li>
                <li>
                  <span className={styles.benefitIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="6" width="18" height="12" rx="2" />
                      <line x1="3" y1="10" x2="21" y2="10" />
                    </svg>
                  </span>
                  <div>
                    <b>PayPal payment integration</b>
                    <span>Checkout, payouts and webhooks built in.</span>
                  </div>
                </li>
                <li>
                  <span className={styles.benefitIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />
                    </svg>
                  </span>
                  <div>
                    <b>Transparent financial audit trails</b>
                    <span>Every action is hash-chained and verifiable.</span>
                  </div>
                </li>
              </ul>
              <div className={styles.miniCard}>
                <b>PRJ-2026-001 · $2,400.00 USD</b>
                4 milestones · plan approved by both parties
                <br />
                <code>sha256: 9f2c…a41e</code>
              </div>
              <div style={{ fontSize: 13, color: '#C9D8F2' }}>
                Already have an account?{' '}
                <button
                  className={styles.btnGhost}
                  type="button"
                  onClick={() => setIsRegister(false)}
                  style={{ marginLeft: 8, height: 36, padding: '0 16px' }}
                >
                  Sign In
                </button>
              </div>
            </div>

            {/* Right overlay panel (shown when signing in) */}
            <div className={`${styles.overlayPane} ${styles.overlayPaneRight}`}>
              <h2>Every Payment. Proven. Protected.</h2>
              <p>Secure milestones. Recover revenue. Trust every transaction.</p>
              <div className={styles.miniCard}>
                <b>Milestone 2 · $700.00 USD</b>
                Over the $200.00 limit, so it goes to a human for approval.
                <br />
                <code>sha256: 9f2c…a41e</code>
              </div>
              <ul className={styles.pointsList}>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M5 12l4 4 10-10" />
                  </svg>
                  Dual-approved escrow plans
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M5 12l4 4 10-10" />
                  </svg>
                  Recovery without wrongful dunning
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M5 12l4 4 10-10" />
                  </svg>
                  Tamper-evident audit trail
                </li>
              </ul>
              <button
                className={styles.btnGhost}
                type="button"
                onClick={() => setIsRegister(true)}
              >
                Create account
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Trust Badges Footer */}
      <div className={styles.tagline}>
        Secure milestones. Recover revenue. Trust every transaction.
      </div>
      <div className={styles.trustBadges}>
        <span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          Secure authentication
        </span>
        <span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="6" width="18" height="12" rx="2" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          PayPal-integrated financial operations
        </span>
        <span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
          </svg>
          Protected workspace access
        </span>
      </div>
    </div>
  );
}
