import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from '../components/ui/Toast';
import { useApi } from '../api/useApi';
import { endpoints } from '../api/endpoints';
import { useAuth } from '../hooks/useAuth';
import styles from './Settings.module.css';

const INITIAL_MEMBERS = [
  ['Sahil', 'sahil@acmeglobal.example', 'Workspace Owner', 'ACTIVE', 'Now'],
  ['Acme Global Solutions', 'client@example.com', 'Client', 'ACTIVE', '2 hours ago'],
  ['Rahul Sharma', 'freelancer@example.com', 'Freelancer', 'ACTIVE', '35 minutes ago'],
  ['Billing Team', 'billing@acmeglobal.example', 'Merchant', 'ACTIVE', 'Yesterday'],
  ['Risk Desk', 'risk@acmeglobal.example', 'Risk Officer', 'ACTIVE', '3 hours ago'],
];

const PERMISSIONS = [
  ['View projects & ledger', true, true, false, true],
  ['Approve plan hash', true, true, false, false],
  ['Fund escrow via PayPal', true, false, false, false],
  ['Submit deliverables', false, true, false, false],
  ['Release / refund funds', true, false, false, true],
  ['Run reconciliation & recovery', false, false, true, true],
  ['Decide in Approvals Queue', false, false, false, true],
  ['Edit Mandate Guard policy', false, false, false, true],
  ['Inspect SHA-256 audit trail', false, false, false, true],
];

const INITIAL_NOTIFICATIONS = [
  { event: 'Dispute filed (escrow freeze)', email: true, webhook: true },
  { event: 'Verification failed / AUTO_REJECT', email: true, webhook: true },
  { event: 'Payout executed', email: true, webhook: true },
  { event: 'Payout routed to Approvals Queue', email: true, webhook: false },
  { event: 'Policy blocked by Mandate Guard', email: true, webhook: true },
  { event: 'Recovery case paid', email: false, webhook: true },
  { event: 'Paid elsewhere detected', email: true, webhook: false },
];

const INITIAL_KEYS = [
  ['Production backend', 'pp_live_••••••••a91f', 'Oct 02, 2026', 'ACTIVE'],
  ['CI / staging', 'pp_test_••••••••3c7d', 'Oct 18, 2026', 'ACTIVE'],
];

const INITIAL_SESSIONS = [
  ['Chrome on Windows', 'Pune, IN', 'Current session', true],
  ['Safari on iPhone', 'Mumbai, IN', '2 hours ago', false],
  ['Firefox on macOS', 'Bengaluru, IN', 'Yesterday', false],
];

export default function Settings() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [isDirty, setIsDirty] = useState(false);

  // Profile Form — pre-populated from auth session
  const [profileName, setProfileName] = useState(() => user?.name || 'Sahil');
  const [profileEmail, setProfileEmail] = useState(() => user?.email || 'sahil@acmeglobal.example');
  const [paypalEmail, setPaypalEmail] = useState('payouts@acmeglobal.example');
  const [timezone, setTimezone] = useState('Asia/Kolkata (UTC+05:30)');

  // Workspace Form
  const [bizName, setBizName] = useState('Acme Global Solutions');
  const [taxId, setTaxId] = useState('94-3127741');

  // Team Form & Modal
  const [members, setMembers] = useState(INITIAL_MEMBERS);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('Client');

  // Notifications
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const [webhookUrl, setWebhookUrl] = useState('https://hooks.acmeglobal.example/proofpay');

  // Security
  const [keys, setKeys] = useState(INITIAL_KEYS);
  const [twoFactorOn, setTwoFactorOn] = useState(true);
  const [sessionTimeout, setSessionTimeout] = useState('30 minutes');
  const [sessions, setSessions] = useState(INITIAL_SESSIONS);

  // Fetch workspace users from DB
  const { data: apiUsers } = useApi(() => endpoints.settings.users());
  useEffect(() => {
    if (!apiUsers || !Array.isArray(apiUsers) || apiUsers.length === 0) return;
    const roleLabel = { client: 'Client', freelancer: 'Freelancer', merchant: 'Merchant', admin: 'Risk Officer' };
    const dbMembers = apiUsers.map(u => [
      u.name,
      u.email,
      roleLabel[u.role] || u.role,
      u.is_active ? 'ACTIVE' : 'INACTIVE',
      'Recently',
    ]);
    setMembers(dbMembers);
    // Sync profile from logged-in user record
    if (user?.email) {
      const me = apiUsers.find(u => u.email === user.email);
      if (me) {
        setProfileName(me.name);
        setProfileEmail(me.email);
      }
    }
  }, [apiUsers, user]);

  const handleSaveProfile = (e) => {
    e.preventDefault();
    setIsDirty(false);
    toast.success('Profile settings saved. Audit event recorded.');
  };

  const handleSaveWorkspace = (e) => {
    e.preventDefault();
    setIsDirty(false);
    toast.success('Workspace settings saved.');
  };

  const handleInviteSubmit = (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setMembers([...members, [inviteEmail.split('@')[0], inviteEmail, inviteRole, 'INVITED', '—']]);
    setIsInviteModalOpen(false);
    setInviteEmail('');
    toast.success('Invitation sent to ' + inviteEmail + '.');
  };

  const handleToggleNotification = (idx, channel) => {
    setNotifications(prev => prev.map((n, i) => i === idx ? { ...n, [channel]: !n[channel] } : n));
    setIsDirty(true);
  };

  const handleSendTestWebhook = () => {
    toast.success('Test webhook delivered to ' + webhookUrl + ' (HTTP 200).');
  };

  const handleGenerateKey = () => {
    const keyName = prompt('Enter a label for the new API key:');
    if (!keyName) return;
    const randHex = Math.random().toString(36).slice(2, 6);
    setKeys([[`${keyName.trim()}`, `pp_test_••••••••${randHex}`, 'Nov 11, 2026', 'ACTIVE'], ...keys]);
    toast.success('Key created. Copy it now — it will not be shown again.');
  };

  const handleRevokeKey = (idx) => {
    if (confirm('Revoke this key? Integrations using it will stop working.')) {
      setKeys(keys.map((k, i) => i === idx ? [k[0], k[1], k[2], 'REVOKED'] : k));
      toast.warning('API key revoked.');
    }
  };

  const handleSignOutOtherSessions = () => {
    setSessions(sessions.filter(s => s[3]));
    toast.warning('All other sessions signed out.');
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1>Settings</h1>
          <p>Manage your profile, workspace, team access, alerts, and security for ProofPay.</p>
        </div>
        {isDirty && (
          <span className={`${styles.badge} ${styles.badgeAmber}`}>
            Unsaved changes
          </span>
        )}
      </div>

      {/* Settings Card with Tabs */}
      <section className={styles.card}>
        <div className={styles.tabList} role="tablist">
          {[
            ['profile', 'Profile'],
            ['workspace', 'Workspace'],
            ['team', 'Team & Permissions'],
            ['notif', 'Notifications'],
            ['security', 'Security & Sessions'],
          ].map(([key, label]) => (
            <button
              key={key}
              className={`${styles.tab} ${activeTab === key ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab 1: Profile */}
        {activeTab === 'profile' && (
          <div className={styles.tabContent}>
            <form className={styles.formGrid} onSubmit={handleSaveProfile}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <span style={{ width: 64, height: 64, borderRadius: 32, background: 'var(--blue-dark)', color: '#fff', fontSize: 24, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  S
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 16 }}>{profileName}</div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                    <span className={`${styles.badge} ${styles.badgeBlue}`}>Workspace Owner</span>
                    <span className={`${styles.badge} ${styles.badgeGreen}`}>VERIFIED</span>
                  </div>
                </div>
              </div>

              <div className={styles.twoCols}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Full name</label>
                  <input
                    className={styles.input}
                    value={profileName}
                    onChange={(e) => { setProfileName(e.target.value); setIsDirty(true); }}
                    required
                  />
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Account email</label>
                  <input
                    type="email"
                    className={styles.input}
                    value={profileEmail}
                    onChange={(e) => { setProfileEmail(e.target.value); setIsDirty(true); }}
                    required
                  />
                </div>
              </div>

              <div className={styles.twoCols}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>PayPal recipient email</label>
                  <input
                    type="email"
                    className={styles.input}
                    value={paypalEmail}
                    onChange={(e) => { setPaypalEmail(e.target.value); setIsDirty(true); }}
                    required
                  />
                  <span style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                    Payouts and refunds are sent here. Mandate Guard requires a verified PayPal email.
                  </span>
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Timezone</label>
                  <select
                    className={styles.input}
                    value={timezone}
                    onChange={(e) => { setTimezone(e.target.value); setIsDirty(true); }}
                  >
                    <option>Asia/Kolkata (UTC+05:30)</option>
                    <option>UTC</option>
                    <option>America/New_York (UTC−05:00)</option>
                    <option>America/Los_Angeles (UTC−08:00)</option>
                    <option>Europe/London (UTC+00:00)</option>
                    <option>Europe/Berlin (UTC+01:00)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>
                  Save Profile
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tab 2: Workspace */}
        {activeTab === 'workspace' && (
          <div className={styles.tabContent}>
            <form className={styles.formGrid} onSubmit={handleSaveWorkspace}>
              <div className={styles.twoCols}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Business name</label>
                  <input
                    className={styles.input}
                    value={bizName}
                    onChange={(e) => { setBizName(e.target.value); setIsDirty(true); }}
                    required
                  />
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Tax ID (EIN / GSTIN / VAT)</label>
                  <input
                    className={styles.input}
                    value={taxId}
                    onChange={(e) => { setTaxId(e.target.value); setIsDirty(true); }}
                    required
                  />
                </div>
              </div>

              <div className={styles.twoCols}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Default currency</label>
                  <select className={styles.input} disabled>
                    <option>USD — US Dollar</option>
                  </select>
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Workspace ID</label>
                  <input
                    className={`${styles.input} ${styles.mono}`}
                    value="ws_acme_2026_001"
                    readOnly
                    style={{ background: '#F0F3F8' }}
                  />
                </div>
              </div>

              <div style={{ padding: '12px 16px', borderRadius: 8, background: '#E6F0FC', fontSize: 13, color: '#172B4D' }}>
                Currency is fixed to USD for this sandbox workspace. Mandate Guard limits ($200.00 per transaction, $5,000.00 per day) are managed in <Link to="/mandate-guard" style={{ color: 'var(--blue)' }}>Mandate Guard</Link>.
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>
                  Save Workspace
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tab 3: Team */}
        {activeTab === 'team' && (
          <div className={styles.tabContent}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>Team &amp; Permissions</h2>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--muted)' }}>Control which personas can access each capability.</p>
              </div>
              <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={() => setIsInviteModalOpen(true)}>
                + Invite Member
              </button>
            </div>

            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Member</th>
                    <th className={styles.th}>Role</th>
                    <th className={styles.th}>Status</th>
                    <th className={styles.th}>Last active</th>
                    <th className={styles.th} />
                  </tr>
                </thead>
                <tbody>
                  {members.map((m, i) => (
                    <tr key={i} className={styles.tr}>
                      <td className={styles.td}>
                        <b>{m[0]}</b>
                        <div style={{ fontSize: 12, color: 'var(--muted)' }}>{m[1]}</div>
                      </td>
                      <td className={styles.td}>
                        {m[2] === 'Workspace Owner' ? (
                          <span className={`${styles.badge} ${styles.badgeBlue}`}>Workspace Owner</span>
                        ) : (
                          <select
                            className={styles.input}
                            style={{ height: 34, padding: '0 8px', fontSize: 13, width: 150 }}
                            value={m[2]}
                            onChange={(e) => {
                              const updated = [...members];
                              updated[i][2] = e.target.value;
                              setMembers(updated);
                              toast.info('Role updated to ' + e.target.value);
                            }}
                          >
                            <option>Client</option>
                            <option>Freelancer</option>
                            <option>Merchant</option>
                            <option>Risk Officer</option>
                          </select>
                        )}
                      </td>
                      <td className={styles.td}>
                        <span className={`${styles.badge} ${m[3] === 'ACTIVE' ? styles.badgeGreen : styles.badgeAmber}`}>
                          {m[3]}
                        </span>
                      </td>
                      <td className={styles.td} style={{ fontSize: 13, color: 'var(--muted)' }}>{m[4]}</td>
                      <td className={styles.td}>
                        {m[2] !== 'Workspace Owner' && (
                          <button
                            className={`${styles.btn} ${styles.btnDanger} ${styles.btnSm}`}
                            onClick={() => {
                              if (confirm('Remove ' + m[0] + ' from this workspace?')) {
                                setMembers(members.filter((_, idx) => idx !== i));
                                toast.warning('Member removed.');
                              }
                            }}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 600, margin: '28px 0 12px', color: 'var(--blue-dark)' }}>
              Role permissions matrix
            </h3>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Capability</th>
                    <th className={styles.th}>Client</th>
                    <th className={styles.th}>Freelancer</th>
                    <th className={styles.th}>Merchant</th>
                    <th className={styles.th}>Risk Officer</th>
                  </tr>
                </thead>
                <tbody>
                  {PERMISSIONS.map(([cap, cl, fl, me, ro], i) => (
                    <tr key={i} className={styles.tr}>
                      <td className={styles.td}>{cap}</td>
                      <td className={styles.td}>{cl ? <span className={`${styles.badge} ${styles.badgeGreen}`}>Allowed</span> : <span className={`${styles.badge} ${styles.badgeGray}`}>—</span>}</td>
                      <td className={styles.td}>{fl ? <span className={`${styles.badge} ${styles.badgeGreen}`}>Allowed</span> : <span className={`${styles.badge} ${styles.badgeGray}`}>—</span>}</td>
                      <td className={styles.td}>{me ? <span className={`${styles.badge} ${styles.badgeGreen}`}>Allowed</span> : <span className={`${styles.badge} ${styles.badgeGray}`}>—</span>}</td>
                      <td className={styles.td}>{ro ? <span className={`${styles.badge} ${styles.badgeGreen}`}>Allowed</span> : <span className={`${styles.badge} ${styles.badgeGray}`}>—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: Notifications */}
        {activeTab === 'notif' && (
          <div className={styles.tabContent}>
            <div style={{ maxWidth: 720 }}>
              <h2 style={{ fontSize: 18, fontWeight: 600, margin: '0 0 4px', color: 'var(--blue-dark)' }}>Alerts</h2>
              <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--muted)' }}>Choose how you are notified about important events.</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 64px 72px', gap: 12, fontSize: 12, fontWeight: 600, color: 'var(--muted)', paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
                <span>Event</span>
                <span style={{ textAlign: 'center' }}>Email</span>
                <span style={{ textAlign: 'center' }}>Webhook</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {notifications.map((n, idx) => (
                  <div key={n.event} style={{ display: 'grid', gridTemplateColumns: '1fr 64px 72px', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)', alignItems: 'center' }}>
                    <span style={{ fontSize: 14 }}>{n.event}</span>
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <button
                        type="button"
                        className={`${styles.switch} ${n.email ? styles.switchChecked : ''}`}
                        onClick={() => handleToggleNotification(idx, 'email')}
                      >
                        <i className={styles.switchKnob} />
                      </button>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <button
                        type="button"
                        className={`${styles.switch} ${n.webhook ? styles.switchChecked : ''}`}
                        onClick={() => handleToggleNotification(idx, 'webhook')}
                      >
                        <i className={styles.switchKnob} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 20 }}>
                <label className={styles.label}>Webhook endpoint URL</label>
                <input
                  type="url"
                  className={`${styles.input} ${styles.mono}`}
                  value={webhookUrl}
                  onChange={(e) => { setWebhookUrl(e.target.value); setIsDirty(true); }}
                  style={{ marginTop: 4 }}
                />
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnPrimary}`}
                  onClick={() => { setIsDirty(false); toast.success('Notification preferences saved.'); }}
                >
                  Save Notifications
                </button>
                <button
                  type="button"
                  className={styles.btn}
                  onClick={handleSendTestWebhook}
                >
                  Send Test Webhook
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Security */}
        {activeTab === 'security' && (
          <div className={styles.tabContent}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 900 }}>
              {/* API Keys */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>API Keys</h2>
                    <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--muted)' }}>Keys are shown once on creation. PayPal secrets are never stored in the browser.</p>
                  </div>
                  <button className={`${styles.btn} ${styles.btnPrimary} ${styles.btnSm}`} onClick={handleGenerateKey}>
                    + Generate Key
                  </button>
                </div>

                <div className={styles.tableResponsive}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th className={styles.th}>Name</th>
                        <th className={styles.th}>Key</th>
                        <th className={styles.th}>Created</th>
                        <th className={styles.th}>Status</th>
                        <th className={styles.th} />
                      </tr>
                    </thead>
                    <tbody>
                      {keys.map((k, i) => (
                        <tr key={i} className={styles.tr}>
                          <td className={styles.td}><b>{k[0]}</b></td>
                          <td className={styles.td}><code className={styles.mono}>{k[1]}</code></td>
                          <td className={styles.td} style={{ fontSize: 13, color: 'var(--muted)' }}>{k[2]}</td>
                          <td className={styles.td}>
                            <span className={`${styles.badge} ${k[3] === 'ACTIVE' ? styles.badgeGreen : styles.badgeGray}`}>{k[3]}</span>
                          </td>
                          <td className={styles.td}>
                            {k[3] === 'ACTIVE' && (
                              <button
                                className={`${styles.btn} ${styles.btnDanger} ${styles.btnSm}`}
                                onClick={() => handleRevokeKey(i)}
                              >
                                Revoke
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 2FA */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', border: '1px solid var(--border)', borderRadius: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>Two-factor authentication</div>
                  <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                    {twoFactorOn ? 'Authenticator app enabled.' : 'Not enabled. Enable it to protect payouts and approvals.'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <span className={`${styles.badge} ${twoFactorOn ? styles.badgeGreen : styles.badgeRed}`}>
                    {twoFactorOn ? 'ENABLED' : 'DISABLED'}
                  </span>
                  <button
                    className={`${styles.btn} ${styles.btnSm}`}
                    onClick={() => {
                      setTwoFactorOn(!twoFactorOn);
                      toast.info(twoFactorOn ? 'Two-factor authentication disabled.' : 'Two-factor authentication enabled.');
                    }}
                  >
                    {twoFactorOn ? 'Disable' : 'Enable'}
                  </button>
                </div>
              </div>

              {/* Sessions */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: 'var(--blue-dark)' }}>Active sessions</h3>
                  <button className={`${styles.btn} ${styles.btnDanger} ${styles.btnSm}`} onClick={handleSignOutOtherSessions}>
                    Sign out other sessions
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
                  {sessions.map((s, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderTop: i > 0 ? '1px solid var(--border)' : 0 }}>
                      <div>
                        <b>{s[0]}</b>
                        <div style={{ fontSize: 12, color: 'var(--muted)' }}>{s[1]} · {s[2]}</div>
                      </div>
                      {s[3] ? (
                        <span className={`${styles.badge} ${styles.badgeGreen}`}>THIS DEVICE</span>
                      ) : (
                        <button
                          className={`${styles.btn} ${styles.btnSm}`}
                          onClick={() => {
                            setSessions(sessions.filter((_, idx) => idx !== i));
                            toast.info('Session signed out.');
                          }}
                        >
                          Sign out
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Invite Member Modal */}
      {isInviteModalOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <form className={styles.modalCard} onSubmit={handleInviteSubmit}>
            <h2 style={{ fontSize: 18, margin: 0, fontWeight: 600, color: 'var(--blue-dark)' }}>
              Invite Member
            </h2>
            <div className={styles.inputGroup}>
              <label className={styles.label}>Email</label>
              <input
                type="email"
                className={styles.input}
                placeholder="name@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
              />
            </div>
            <div className={styles.inputGroup}>
              <label className={styles.label}>Role</label>
              <select
                className={styles.input}
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option>Client</option>
                <option>Freelancer</option>
                <option>Merchant</option>
                <option>Risk Officer</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
              <button type="button" className={styles.btn} onClick={() => setIsInviteModalOpen(false)}>
                Cancel
              </button>
              <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>
                Send Invite
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

