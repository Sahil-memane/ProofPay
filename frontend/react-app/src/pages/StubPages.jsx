// Stub pages for P3 — rendered with consistent layout, mock data shown

import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

function StubPage({ title, description, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 26, fontWeight: 600, margin: 0 }}>{title}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{description}</p>
      </div>
      {children}
    </div>
  );
}

export function Agents() {
  const agents = [
    { name: 'Recovery Agent', model: 'GPT-4o', status: 'ACTIVE', cases: 150, accuracy: '28.67%' },
    { name: 'Scoping Agent', model: 'GPT-4o', status: 'ACTIVE', plans: 24, accuracy: '99%' },
    { name: 'Verifier Agent', model: 'GPT-4o', status: 'ACTIVE', verified: 48, accuracy: '94%' },
    { name: 'Root Cause Agent', model: 'GPT-4o-mini', status: 'ACTIVE', diagnosed: 38, accuracy: '89%' },
  ];
  return (
    <StubPage title="AI Agent Control Center" description="Monitor and configure ProofPay's autonomous AI agents.">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
        {agents.map(a => (
          <Card key={a.name}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>{a.name}</span>
              <Badge variant="success">{a.status}</Badge>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span>Model: {a.model}</span>
              <span>Accuracy: <strong style={{ color: 'var(--green)' }}>{a.accuracy}</strong></span>
              {a.cases && <span>Cases processed: {a.cases}</span>}
              {a.plans && <span>Plans scoped: {a.plans}</span>}
              {a.verified && <span>Submissions verified: {a.verified}</span>}
              {a.diagnosed && <span>Root causes diagnosed: {a.diagnosed}</span>}
            </div>
          </Card>
        ))}
      </div>
      <Card>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
          All agents operate within Mandate Guard policy constraints. No agent can exceed $200 payout without HITL approval.
          Agents use LangGraph state machines and are audited on every decision.
        </p>
      </Card>
    </StubPage>
  );
}

export function Assistant() {
  return (
    <StubPage title="AI Assistant (Read-Only)" description="Ask questions about your projects, cases, and audit trail.">
      <Card>
        <div style={{ background: 'var(--bg)', borderRadius: 8, padding: '12px 16px', marginBottom: 12, fontSize: 13, color: 'var(--muted)' }}>
          🤖 This assistant has read-only access. It can explain audit events, summarise case history, and answer questions about ProofPay policies.
        </div>
        <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 16, minHeight: 200, fontSize: 13, color: 'var(--muted)' }}>
          <em>Start a conversation by typing below…</em>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <input style={{ flex: 1, height: 40, padding: '0 12px', border: '1px solid var(--border)', borderRadius: 6, font: '13px var(--font-ui)' }} placeholder="Ask anything about ProofPay…" />
          <button style={{ height: 40, padding: '0 16px', background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Send</button>
        </div>
      </Card>
    </StubPage>
  );
}

export function Disputes() {
  return (
    <StubPage title="Disputes & Escrow Freeze" description="Manage active disputes and freeze escrow funds pending resolution.">
      <Card>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>No active disputes. When a dispute is filed via PayPal webhook, it appears here and the escrow is automatically frozen.</p>
      </Card>
    </StubPage>
  );
}

export function Invoices() {
  return (
    <StubPage title="Invoices & Subscriptions" description="Track overdue invoices and recurring payment recovery.">
      <Card noPadding>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', fontWeight: 600, fontSize: 14 }}>Overdue Invoices</div>
        <div style={{ padding: 24, color: 'var(--muted)', fontSize: 13, textAlign: 'center' }}>
          Connect to fixtures: <a href="/fixtures/invoices">GET /fixtures/invoices</a> to load sample invoices.
        </div>
      </Card>
    </StubPage>
  );
}

export function Pay() {
  return (
    <StubPage title="Pay" description="Initiate direct payments and PayPal Orders.">
      <Card>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
          Payments flow through ProofPay escrow → PayPal Orders API → Payouts API.
          Use Project Details to fund an escrow contract.
        </p>
      </Card>
    </StubPage>
  );
}

export function PaymentAttempts() {
  return (
    <StubPage title="Payment Attempts & Logs" description="All payment events across escrow and recovery workflows.">
      <Card noPadding>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', fontWeight: 600, fontSize: 14 }}>Payment Event Log</div>
        <div style={{ padding: 24, color: 'var(--muted)', fontSize: 13, textAlign: 'center' }}>
          Webhook events from PayPal appear here as they are processed.
        </div>
      </Card>
    </StubPage>
  );
}

export function Integrations() {
  const integrations = [
    { name: 'PayPal Orders v2', status: 'Connected', detail: 'Sandbox credentials active' },
    { name: 'PayPal Payouts', status: 'Connected', detail: 'Mandate Guard: $200 cap' },
    { name: 'PayPal Webhooks', status: 'Connected', detail: 'POST /webhooks/paypal' },
    { name: 'PayPal Invoicing', status: 'Connected', detail: 'Invoice creation ready' },
  ];
  return (
    <StubPage title="Integrations (PayPal / APIs)" description="Manage external service connections.">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
        {integrations.map(i => (
          <Card key={i.name}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>{i.name}</span>
              <Badge variant="success">{i.status}</Badge>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>{i.detail}</div>
          </Card>
        ))}
      </div>
    </StubPage>
  );
}

export function Settings() {
  return (
    <StubPage title="Settings" description="Configure ProofPay environment and preferences.">
      <Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            ['Mandate Guard Cap', '$200.00 USD'],
            ['Quiet Hours', '21:00 – 08:00 local time'],
            ['Max Contact Attempts', '3 (Stage 1 → 2 → 3)'],
            ['Demo Mode', 'Enabled'],
            ['PayPal Exec Mode', 'fake (sandbox)'],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
              <span style={{ color: 'var(--muted)' }}>{k}</span>
              <strong>{v}</strong>
            </div>
          ))}
        </div>
      </Card>
    </StubPage>
  );
}

export function Help() {
  const faqs = [
    ['What is ProofPay?', 'AI-powered escrow for freelancers + autonomous revenue recovery for merchants — built on PayPal APIs.'],
    ['How does dual approval work?', 'Both client and freelancer must cryptographically sign the project plan (SHA-256 hash). Funding is blocked until both approve.'],
    ['What is Mandate Guard?', 'Policy layer that caps autonomous payouts at $200. Amounts above that go to the HITL approval queue.'],
    ['How does recovery work?', 'Failed payments trigger a 3-stage contact ladder (email → SMS → letter). AI decides timing. Quiet hours are respected.'],
    ['What is paid-elsewhere reconciliation?', 'If a customer pays via another method, ProofPay detects it and stops recovery outreach automatically.'],
  ];
  return (
    <StubPage title="Help & Support" description="Documentation, FAQs, and API reference.">
      <Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {faqs.map(([q, a]) => (
            <details key={q} style={{ padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 500, fontSize: 13 }}>{q}</summary>
              <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--muted)' }}>{a}</p>
            </details>
          ))}
        </div>
      </Card>
      <Card>
        <div style={{ fontSize: 13 }}>
          <strong>API Docs:</strong> <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">http://localhost:8000/docs</a>
          {' — '}<strong>Postman:</strong> Import <code>postman/ProofPay.postman_collection.json</code>
        </div>
      </Card>
    </StubPage>
  );
}

export function CreateProjectWizard() {
  return (
    <StubPage title="Create Project Wizard" description="Step-by-step project creation with AI scope generation.">
      <Card>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
          Use the <a href="/projects">Projects page</a> to create a project directly, or use this wizard for guided creation with AI scope suggestions.
        </p>
      </Card>
    </StubPage>
  );
}

