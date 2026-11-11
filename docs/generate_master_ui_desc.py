# -*- coding: utf-8 -*-
"""
Master UI Specification Generator for ProofPay
Produces the finalized, gap-free, hyper-detailed docs/UI Desc.md
"""
from pathlib import Path

OUTPUT_PATH = Path(r"e:\Projects\ProofPay\docs\UI Desc.md")

content = """# MASTER UI/UX DESIGN PROMPT — PROOFPAY
## Agentic Escrow & Intelligent Revenue Recovery Platform
### Complete Multi-Page UI Specification & Frontend Architecture Guide (23 Pages)

**Role Context:**
Act as a Senior Product Designer, FinTech UI/UX Architect, and Enterprise Frontend Engineer (Dev 1 Tech Lead + Dev 4 Frontend UI Lead).

Your task is to design, specify, and build a complete, high-fidelity, multi-page financial SaaS web application named **ProofPay**.

This is not a mock landing page. It is a complete operational web application with interconnected pages, persistent navigation, detailed input forms, financial ledgers, analytics dashboards, AI agent observability interfaces, PayPal checkout & payout workflows, deterministic policy controls, human-in-the-loop governance queues, and cryptographic audit functionality.

The design must be professional and bank-grade, fully prepared to be demonstrated to PayPal engineers, hackathon judges, enterprise clients, and investors.

---

# PART 1 — PRODUCT UNDERSTANDING & VALUE PROPOSITION

## 1.1 What is ProofPay?
ProofPay is an autonomous financial operations platform designed for the PayPal AI Hackathon. It unifies two critical engines with a shared deterministic trust layer:

### Engine 1: Escrow Engine — PREVENT
Protects freelancers and clients against non-payment, scope creep, and delivery disputes.
1. **Intake & AI Scoping:** Client describes the engagement; AI Scoping Agent structures it into measurable milestones with testable acceptance criteria.
2. **Cryptographic Dual Approval:** Both Client and Freelancer approve the milestone plan. The platform computes an SHA-256 **Plan Hash** of all milestones, amounts, and criteria. Both signatures must match the plan hash before funding is unlocked. Any out-of-band change creates a 409 Conflict.
3. **Escrow Funding:** Client funds the project via PayPal Checkout (Orders v2 create and capture). Funds are held in a secure escrow pool.
4. **Work Submission:** Freelancer delivers work by submitting GitHub PR URL, repository, deployed staging URL, evidence files, and notes.
5. **AI Work Verification:** AI Verification Agent inspects deliverables against criteria, calculating a verification score (0.0 to 1.0) and route (`AUTO_APPROVE` >= 0.80, `HUMAN_REVIEW` 0.60–0.79, `AUTO_REJECT` < 0.60).
6. **Mandate Guard Policy Gating:** Deterministic Python policy firewall checks transaction safety rules (e.g. per-transaction autonomous limit of $200.00, daily volume limit of $5,000.00, verified PayPal email).
7. **Disbursement:** If allowed, executor dispatches funds to freelancer's verified PayPal account via PayPal Payouts API. If amount exceeds $200.00 or score is borderline, it routes to the Human Approvals Queue.
8. **Audit Trail:** Every state change is recorded in an immutable SHA-256 cryptographic hash chain.

### Engine 2: Revenue Recovery Engine — RECOVER
Helps merchants, SaaS platforms, and freelancers recover failed recurring subscription charges and overdue invoices with zero brand damage.
1. **Detection:** Failed subscription charges and overdue invoices are ingested in real time via webhooks or CSV imports.
2. **3-Way Reconciliation Check:** Reconciliation engine matches PayPal gateway logs against merchant ERP invoices and offline bank statements. If a customer already paid via wire or alternate rail, the recovery campaign is **permanently halted** to prevent embarrassing wrongful dunning.
3. **Root-Cause AI Diagnosis:** AI categorizes failure reasons (`EXPIRED_CARD`, `INSUFFICIENT_FUNDS`, `BANK_AUTH_FAILED`, `GATEWAY_ERROR`).
4. **Intervention Selection:** Selects appropriate recovery step along a 3-stage contact ladder (Stage 1: Soft Update Link, Stage 2: Firm Warning, Stage 3: Executive Pause).
5. **Quiet Hours Compliance:** Outbound communications and retries are automatically suspended during customer quiet hours (21:00 to 08:00 local time).
6. **Customer Payment Portal:** Customer receives a link to a clean, mobile-responsive **Customer Payment Recovery Portal** (`pay.html`) where they can settle the balance in 1 click via PayPal Smart Payment Buttons or update card details.
7. **Resolution Tracking:** Once paid, PayPal webhook captures the event, marks the case `PAID`, updates the timeline, and closes the recovery ticket.

### Shared Trust & Governance Layer
Both engines share:
- **Deterministic Mandate Guard / Policy Engine:** Strictly enforces safety limits. LLMs only propose actions; deterministic Python rules decide what executes.
- **Human-in-the-Loop Governance Queue (Approvals):** Dedicated inbox for human sign-off on high-value escrow payouts (>$200) and sensitive recovery escalations.
- **Dispute Circuit Breaker:** Autonomous escrow freeze and recovery halt immediately upon receipt of a PayPal dispute webhook.
- **Cross-Platform Reputation Ledger:** Trust scores for clients, freelancers, and merchants.
- **Tamper-Evident SHA-256 Audit Trail:** Mathematical proof that no financial record or agent log has been modified.
- **Read-Only AI Assistant:** Natural language cited Q&A interface with clickable audit citations.
- **Demo & Simulation Lab:** Hackathon evaluator control panel with clock fast-forward (+24h, +48h, +7d), failure injectors, and 150-case benchmark simulator.

### Core Product Philosophy
> **"AI recommends. Policy decides. PayPal executes. Every action is auditable."**
Never design an architecture where an LLM directly executes financial disbursements without policy authorization and human fallback guardrails.

---

# PART 2 — VISUAL BRANDING AND DESIGN SYSTEM

## 2.1 Branding Identity
- **Application Name:** ProofPay
- **Tagline:** Every Payment. Proven. Protected.
- **Supporting Description:** "Secure milestones. Recover revenue. Trust every transaction."
- **Aesthetic:** Clean, bank-grade, disciplined, modern, transparent. Adopts the familiar visual authority of PayPal Business while integrating cutting-edge agentic autonomy.

## 2.2 Exact Color Palette Tokens
| Token Name | Hex Code | Visual Application |
| :--- | :--- | :--- |
| **PayPal Deep Navy** | `#003087` | Left sidebar background, brand accents, primary headers |
| **PayPal Royal Blue** | `#0070E0` | Primary buttons, active navigation states, links, main CTAs |
| **PayPal Bright Blue** | `#009CDE` | Accent pills, progress highlights, secondary badges |
| **Dark Navy** | `#001C64` | High-contrast table headers, dark borders |
| **App Canvas Background** | `#F5F7FA` | Neutral canvas background behind cards and tables |
| **Card / Surface Background**| `#FFFFFF` | Cards, tables, modals, flyout drawers, inputs |
| **Primary Text** | `#172B4D` | Main titles, table cell text, prominent labels |
| **Secondary Text** | `#64748B` | Subtitles, field labels, timestamps, metadata |
| **Border Color** | `#E5E9F0` | Dividers, card borders, table row borders, input strokes |
| **Muted Surface** | `#F0F3F8` | Table column headers, badge backgrounds, hover states |
| **Success Green** | `#2E9D65` | Paid, verified, matched, active status, high score |
| **Warning Amber** | `#F5A623` | Pending review, borderline score, quiet hours paused |
| **Danger Red** | `#D9363E` | Failed payment, dispute, policy blocked, auto-reject |
| **Info Blue** | `#0070E0` | Stage indicators, informational banners |
| **Neutral Gray** | `#8A94A6` | Drafts, cancelled, unallocated, archived |

## 2.3 Typography & Sizing Rules
- **Font Stack:** `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Monospace Stack:** `JetBrains Mono, "SF Mono", Consolas, monospace` (for Plan Hashes, Transaction IDs, SHA-256 Hashes, Code, JSON)
- **Scale:**
  - Page Titles: `24px` to `28px`, Semibold (`600`), `#172B4D`
  - Section Headings: `18px` to `20px`, Semibold (`600`), `#172B4D`
  - Card Titles: `14px` to `16px`, Medium (`500`), `#172B4D`
  - Body Text: `13px` to `14px`, Regular (`400`), `#172B4D`
  - Captions & Labels: `12px` to `13px`, Medium (`500`), `#64748B`
  - Code / Identifiers: `12px`, Regular, `#003087`

---

# PART 3 — GLOBAL APPLICATION STRUCTURE

## 3.1 Primary Sidebar Navigation (23 Application Destinations)
The primary navigation sidebar is fixed on the left (`width: 260px`), styled with `#003087` (Deep Navy) background, featuring white/semi-transparent text and `#0070E0` active highlights.

```text
PROOFPAY (Logo + Workspace Dropdown)

▼ ESCROW PREVENT
  01. Dashboard                    [index.html]
  02. Projects                     [projects.html]
  02B. Project Details & Funding   [project-details.html]
  03. Milestones                   [milestones.html]
  04. Submissions & Verification   [submissions.html]
  05. Escrow Ledger                [ledger.html]

▼ REVENUE RECOVER
  06. Recovery Overview            [recovery-overview.html]
  07. Recovery Cases               [cases.html]
  08. Invoices & Subscriptions     [invoices.html]
  09. Payment Attempts & Logs      [payment-attempts.html]

▼ TRUST & GOVERNANCE
  10. Reconciliation (3-Way)       [reconciliation.html]
  11. Disputes & Escrow Freeze     [disputes.html]
  12. Mandate Guard                [mandate-guard.html]
  13. Reputation Ledger            [reputation.html]
  14. Approvals Queue (HITL)       [approvals.html]          <-- Critical Hackathon Feature

▼ INTELLIGENCE
  15. AI Agent Control Center      [agents.html]
  16. Analytics & Reports          [analytics.html]
  17. Audit Trail (SHA-256)        [audit.html]
  18. AI Assistant (Read-Only)     [assistant.html]

▼ SYSTEM & DEMO
  19. Integrations (PayPal/APIs)   [integrations.html]
  20. Settings                     [settings.html]
  21. Help & Support               [help.html]
  22. Demo & Simulation Lab        [demo.html]               <-- Critical Evaluator Panel

▼ EXTERNAL CUSTOMER PORTAL
  23. Customer Recovery Portal     [pay.html]                <-- Debtor 1-Click Checkout
```

## 3.2 Top Header & Persona Role Switcher
Fixed header across all internal application pages (`height: 64px`, `#FFFFFF` background, `border-bottom: 1px solid #E5E9F0`).

### Left Side:
- Breadcrumb navigation (`Projects > PRJ-2026-001 > Milestones`).
- Page context heading.

### Center:
- Global Search Bar: "Search projects, invoices, cases, audit hashes (Ctrl+K)..."

### Right Side:
1. **Interactive Persona Role Switcher (Crucial Evaluator Feature):**
   A dropdown selector allowing judges and users to switch personas in 1 click:
   - **`[Role: 👤 Client (Buyer)]`**: Views projects, approves milestone scope/plan hash, funds escrow via PayPal Smart Buttons, reviews submitted deliverables, releases funds or requests refunds.
   - **`[Role: 🛠️ Freelancer (Contractor)]`**: Reviews project scope, approves plan hash, submits deliverables (GitHub PR, deployed URL), tracks verifier score, receives PayPal payouts.
   - **`[Role: 🏢 Merchant (Billing Admin)]`**: Monitors failed subscriptions, runs 3-way reconciliation, tracks contact ladders, generates recovery links.
   - **`[Role: 🛡️ Risk Officer / Admin]`**: Operates Mandate Guard, decides on over-limit releases in the Approvals Queue, inspects SHA-256 audit chain, runs benchmark simulations.
   *Dynamic Effect:* Switching the role immediately toggles visible action buttons, permissions, and contextual cards across the active page!
2. **PayPal Connection Pill:** Green dot + `PayPal Sandbox: Connected`.
3. **Notification Bell:** Badge counter for alerts (disputes, pending approvals).
4. **User Profile:** Avatar, name, role badge.

## 3.3 Sticky Hackathon Evaluator Quick Bar (Floating Judge Toolbar)
A persistent floating pill or top banner accessible on every page to give hackathon judges instant testing controls:
- **`[ ⚡ DEMO BAR ]`**
- **`[ 🕒 Advance +24h ]`** / **`[ 🕒 Advance +48h ]`**: Calls `POST /demo/advance-clock` to trigger contact ladder progression and test quiet hours.
- **`[ ⚠️ Inject Failure ▾ ]`**: Calls `POST /demo/inject-failure` (options: `INSUFFICIENT_FUNDS`, `EXPIRED_CARD`, `DISPUTE_FILED`, `PLAN_HASH_MISMATCH`).
- **`[ 🚀 Run 150 Benchmark ]`**: Calls `POST /demo/run-simulator` to run synthetic dataset and populate Agent vs Baseline comparison charts.
- **`[ 🔄 Reset Demo ]`**: Calls `POST /demo/reset` to restore pristine demo state.
- **`[ Clock Display ]`**: `Simulated Time: 2026-11-12 14:30 UTC [Active Business Hours]`.

---

# PART 4 — PAGE-BY-PAGE COMPLETE DESIGN SPECIFICATION

---

## PAGE 01 — DASHBOARD
- **HTML Target:** `index.html`
- **Route:** `/dashboard`
- **Primary Persona:** Universal (Executive / Business Owner)
- **Backend API Endpoints:**
  - `GET /reconciliation/summary` (Aggregated recovery totals)
  - `GET /projects` (Active escrow project volume)
  - `GET /cases` (Active recovery cases)
  - `GET /audit` (Recent chained audit events)
  - `GET /submission-approvals` (Pending human approval count)

### Header
- Greeting: "Good afternoon, Sahil"
- Subtitle: "Unified command center for protected milestone escrow and autonomous revenue recovery."
- Header Buttons: `+ Create Project`, `+ Create Invoice`, `Demo Lab →`
- Role Badge: Displays current active role (`Client`, `Freelancer`, `Merchant`, `Risk Officer`).

### Section A: Revenue Recovery Hero Banner
- Prominent horizontal card with deep navy accent:
  - Headline: "Revenue Recovered by Autonomous Agents"
  - Large Metric: **$12,450.00 USD**
  - Supporting Text: "Recovered $12,450.00 of $18,600.00 at risk across 150 cases (67% Recovery Rate)"
  - Progress Bar: Multi-segment showing Recovered ($12,450 / 67%), In Recovery ($4,250 / 23%), and Unrecovered ($1,900 / 10%).
  - Quick Link: `View Recovery Cases →`

### Section B: Core KPI Metric Cards (6 Cards)
1. **Total Escrowed:** `$48,500.00` (+12.5% vs last month) | Subtitle: "Across 8 active client contracts"
2. **Released to Freelancers:** `$31,200.00` | Subtitle: "18 milestone payouts executed via PayPal"
3. **Escrow Held in Trust:** `$17,300.00` | Subtitle: "Protected awaiting work verification"
4. **Revenue Recovered:** `$12,450.00` (67% rate) | Subtitle: "101 of 150 failed invoices recovered"
5. **Reconciliation Accuracy:** `98.5%` | Subtitle: "8 cases prevented from wrongful dunning"
6. **Mandate Guard Interceptions:** `5 Actions Blocked` | Subtitle: "Enforced $200 limit & quiet hours"

### Section C: Live Pending Attention Banner (Conditional Alert)
- Displays amber/red banner when items need human review:
  - `⚠️ 2 Milestone Payouts awaiting Human Review (Oversized > $200.00 limit)`
  - `⚠️ 1 Active Dispute filed: Milestone escrow automatically frozen`
  - Action button: `Open Approvals Queue →` (Links to `approvals.html`)

### Section D: Dual Engine Operational Grid (2 Columns)
- **Left Column: Escrow Engine (PREVENT)**
  - Active Projects Summary (List of top 3 projects with funding and progress bars)
  - Recent Deliverables Submitted (AI verification score pill, route pill)
  - Quick Action: `+ Fund Project via PayPal`
- **Right Column: Recovery Engine (RECOVER)**
  - Active Recovery Ladder Cases (Current stage distribution: Stage 1, Stage 2, Stage 3)
  - Failed Payment Root Cause Breakdown (Expired Card 42%, Insufficient Funds 35%, Bank Auth 18%)
  - Quick Action: `Run Reconciliation Match`

### Section E: Recent Chained Audit Stream
- Chronological table showing the last 5 events from `GET /audit`:
  - Columns: Timestamp, Event Type, Entity ID, Actor, Action, Block/Allow Badge, SHA-256 Row Hash (first 8 chars linked to drawer).

---

## PAGE 02 — PROJECTS MASTER LIST & INTAKE
- **HTML Target:** `projects.html`
- **Route:** `/projects`
- **Primary Persona:** Client / Freelancer
- **Backend API Endpoints:**
  - `GET /projects` (Fetch all projects)
  - `POST /projects` (Create new project with milestones)
  - `GET /projects/{project_id}` (Project details & plan hash)

### Header & Filters
- Title: "Projects & Contracts"
- Subtitle: "Manage freelance client agreements, milestone deliverables, and protected PayPal escrow."
- Actions: `+ Create Project` (opens wizard), `Export CSV`.
- Filter Bar: `All (8)`, `Draft (1)`, `Awaiting Approval (2)`, `Funded (3)`, `Completed (2)`, `Disputed (0)`. Search input.

### Master Projects Table
- **Columns:**
  1. Project ID (`PRJ-2026-001` - monospace link to `project-details.html?id=PRJ-2026-001`)
  2. Project Title & Description snippet
  3. Client Email (`client@example.com`)
  4. Freelancer Email (`freelancer@example.com`)
  5. Total Amount (`$2,400.00 USD`)
  6. Funded Amount (`$2,400.00 USD`)
  7. Released Amount (`$1,100.00 USD`)
  8. Plan Hash Status: Badge (`Both Approved` [Green], `Awaiting Freelancer` [Amber], `Awaiting Client` [Amber], `Mismatch` [Red])
  9. PayPal Status: Badge (`FUNDED` [Green], `AWAITING_PAYPAL` [Amber], `DRAFT` [Gray])
  10. Actions: `View Details`, `Fund Now` (if client & approved), `Approve Scope` (if unapproved).

### Create Project Wizard (Modal / 5-Step Flow)
- **Step 1: Basic Information**
  - Project Title (`input[text]`, required, e.g. "E-commerce Website Development")
  - Project Description (`textarea`, required)
  - Currency (`select`: `USD`, `EUR`, `GBP`; default: `USD`)
- **Step 2: Client Details**
  - Client Name (`input[text]`) & Client Email (`input[email]`, required)
- **Step 3: Freelancer Details**
  - Freelancer Name (`input[text]`) & Freelancer PayPal Recipient Email (`input[email]`, required - validated by Mandate Guard)
- **Step 4: AI Scoping Agent Assist (Optional)**
  - Button: `Generate Criteria with AI Scoping Agent`
  - Automatically parses description and suggests milestones, weights, and acceptance criteria.
- **Step 5: Milestone Allocation & Acceptance Criteria**
  - Dynamic Milestone Rows:
    - Milestone Title (`input[text]`)
    - Description (`textarea`)
    - Amount (`input[number]`, e.g. `700.00`)
    - Due Date (`input[date]`)
    - Acceptance Criteria (`textarea` - clear, testable bullet points)
  - Live Calculation: Sum of milestones must exactly equal Project Total Amount.
  - Plan Hash Computation: Displays computed SHA-256 hash preview (`0a8f9c2...4e1`).
  - Action: `Submit & Create Project` -> calls `POST /projects`.

---

## PAGE 02B — PROJECT DETAILS, DUAL APPROVAL & PAYPAL FUNDING
- **HTML Target:** `project-details.html`
- **Route:** `/projects/{project_id}`
- **Primary Persona:** Client / Freelancer
- **Backend API Endpoints:**
  - `GET /projects/{project_id}` (Fetch project, milestones, plan hash, approval state)
  - `POST /projects/{project_id}/approve` (Dual approval: role + plan_hash)
  - `POST /projects/{project_id}/fund` (Create PayPal Order v2)
  - `POST /projects/{project_id}/capture` (Capture authorized PayPal payment)

### Header & Project Summary
- Breadcrumbs: `Projects > PRJ-2026-001`
- Title: "E-commerce Website Development"
- Badges: `Status: APPROVED` | `Escrow: $2,400.00 USD` | `Plan Hash: 0a8f9c...4e1`

### Section A: Cryptographic Dual Approval Banner (Core Security)
- **Plan Hash Display:** `0a8f9c2e5b741098a83d3467e21098c7654a12908fde3209847162534a9b4e1` (64-char hex, copy button).
- **Client Approval Card:**
  - Status: `✅ Approved by client@example.com at 2026-11-10 09:30 UTC` (or `⏳ Awaiting Client Approval`).
  - Button (visible if Client role and unapproved): `Approve Plan Hash` -> calls `POST /projects/{id}/approve` with `{"role": "client", "plan_hash": "..."}`.
- **Freelancer Approval Card:**
  - Status: `✅ Approved by freelancer@example.com at 2026-11-10 10:15 UTC` (or `⏳ Awaiting Freelancer Approval`).
  - Button (visible if Freelancer role and unapproved): `Approve Plan Hash` -> calls `POST /projects/{id}/approve` with `{"role": "freelancer", "plan_hash": "..."}`.
- **Tamper Detection Banner:** If plan hash has been modified, displays Red Warning: `⚠️ PLAN HASH MISMATCH: Milestones have changed since approval. Both parties must re-approve.`

### Section B: PayPal Escrow Funding Card (Client Role)
- If approved by both parties and status != `FUNDED`:
  - Card: "Fund Project Escrow via PayPal"
  - Amount Due: `$2,400.00 USD`
  - **PayPal Smart Button Container:**
    - Step 1: Client clicks PayPal button -> calls `POST /projects/{id}/fund` -> returns PayPal Order ID & Approval URL.
    - Step 2: Client authorizes in PayPal popup.
    - Step 3: Frontend calls `POST /projects/{id}/capture` with order ID.
    - Step 4: Webhook `PAYMENT.CAPTURE.COMPLETED` fires -> Project transitions to `FUNDED`.
- If already funded: Displays `🔒 ESCROW SECURELY FUNDED IN PAYPAL VAULT (Capture ID: CAP-884102)` [Green].

### Section C: Milestones Breakdown (Milestones 1 to 4)
- Individual cards for each milestone:
  - Milestone 1: UI Design & Tokens — `$400.00 USD` (`PAID` [Green])
  - Milestone 2: Frontend Integration — `$700.00 USD` (`SUBMITTED / IN_REVIEW` [Amber])
  - Milestone 3: Backend & PayPal Checkout — `$800.00 USD` (`FUNDED` [Blue])
  - Milestone 4: QA & Deployment — `$500.00 USD` (`FUNDED` [Blue])
- Action Buttons per card:
  - Freelancer: `Submit Deliverable` (links to `submissions.html`).
  - Client: `Review Deliverable`, `Release Funds`, `Request Refund` (calls `POST /milestones/{id}/refund`).

---

## PAGE 03 — MILESTONES CENTRAL TRACKER
- **HTML Target:** `milestones.html`
- **Route:** `/milestones`
- **Primary Persona:** Universal (Client, Freelancer, Risk Admin)
- **Backend API Endpoints:**
  - `GET /projects` (Lists all projects and nested milestones)
  - `PATCH /projects/{project_id}/milestones/{milestone_id}` (Update milestone scope)
  - `POST /milestones/{milestone_id}/submit`
  - `POST /milestones/{milestone_id}/review`
  - `POST /milestones/{milestone_id}/refund`

### Header & Summary Cards
- Title: "Milestones Central Tracker"
- Subtitle: "Track funding status, deliverable submissions, AI verifications, and PayPal payout releases."
- Summary Cards:
  1. `Total Milestones: 32`
  2. `Funded in Escrow: 14 ($17,300)`
  3. `Awaiting Submission: 8`
  4. `Under AI Verification: 3`
  5. `Pending Release: 2 ($1,400)`
  6. `Completed & Paid: 18 ($31,200)`

### Master Milestone Table
- **Columns:**
  1. Milestone ID (`MS-2026-001-02` - monospace)
  2. Project Title (`E-commerce Web App`)
  3. Milestone Name (`Frontend Integration & API Client`)
  4. Amount (`$700.00 USD`)
  5. Due Date (`2026-11-15`)
  6. Status Badge:
     - `DRAFT` (Gray)
     - `FUNDED` (Blue)
     - `SUBMITTED` (Purple)
     - `VERIFYING` (Amber)
     - `IN_REVIEW` (Amber)
     - `PAYOUT_PROPOSED` (Blue)
     - `PAYOUT_POLICY_DENIED` (Red - Exceeds limit or requires human review)
     - `PAID` (Green)
     - `REFUNDED` (Gray/Red)
     - `DISPUTED` (Red)
  7. AI Score Badge (`94% - AUTO_APPROVE` or `72% - HUMAN_REVIEW`)
  8. Actions:
     - Freelancer: `Submit Work` (opens submission modal)
     - Client: `Review Work`, `Release Funds`, `Request Refund`
     - Risk Officer: `Inspect Mandate Guard Decision`

---

## PAGE 04 — SUBMISSIONS & AI VERIFICATION INSPECTION
- **HTML Target:** `submissions.html`
- **Route:** `/verification` (or `/milestones/{milestone_id}/submission`)
- **Primary Persona:** Freelancer (submit) / Client & Risk Officer (inspect)
- **Backend API Endpoints:**
  - `POST /milestones/{milestone_id}/submit` (Freelancer submits deliverables)
  - `GET /milestones/{milestone_id}/submission` (Fetch submission & verification report)
  - `POST /milestones/{milestone_id}/_inject_verification` (Demo mode verifier injection)
  - `POST /milestones/{milestone_id}/review` (Client review: `APPROVE`, `REQUEST_REVISION`, `DISPUTE`)
  - `POST /milestones/{milestone_id}/refund` (Refund request)

### Section A: Freelancer Deliverable Submission Form (Modal or View)
- Fields:
  - Milestone Reference (`readonly`: "Milestone 2: Frontend Integration — $700.00 USD")
  - GitHub Pull Request URL (`input[url]`, e.g. `https://github.com/acme/shop/pull/42`)
  - GitHub Repository (`input[text]`, e.g. `acme/shop`)
  - Deployed Live URL (`input[url]`, e.g. `https://preview-42.acme.app`)
  - Evidence Documentation URL (`input[url]`)
  - Submission Notes / Summary (`textarea`)
  - File Uploads (`input[file]`: test logs, zip, pdf)
- Button: `Submit Deliverable for AI Verification` -> calls `POST /milestones/{milestone_id}/submit`.

### Section B: 2-Column Work Inspection & AI Verification Report
- **Left Column: Submitted Deliverables & Artifacts**
  - GitHub PR Link with direct branch and commit reference (`commit: 9f8a12e`).
  - Deployed Staging Preview status badge (`HTTP 200 OK — Latency 128ms`).
  - Freelancer notes and instructions.
  - Submission timestamp (`2026-11-11 11:30 UTC`).
- **Right Column: AI Verification Agent Report**
  - **Overall Score Radial Gauge:** Large visual gauge displaying `94/100`.
  - **Routing Decision Badge:**
    - `AUTO_APPROVE` (Score >= 0.80)
    - `HUMAN_REVIEW` (0.60 <= Score < 0.80)
    - `AUTO_REJECT` (Score < 0.60)
  - **Criterion Breakdown Checklist:**
    - `[✅ Passed] (Weight: 35%) GitHub PR exists, passes linting & build`
    - `[✅ Passed] (Weight: 35%) Deployed endpoint returns HTTP 200 with valid UI assets`
    - `[✅ Passed] (Weight: 20%) Responsive layout rendered without layout shifts`
    - `[⚠️ Partial] (Weight: 10%) Unit test coverage at 78% (Target 80%)`
  - **AI Verification Rationale:** Clear natural language explanation explaining why the score was assigned.
- **Section C: Mandate Guard Policy Evaluation Preview**
  - Displays deterministic policy result:
    - If Amount <= $200.00: `ALLOWED — Dispatched PayPal Payout batch ID: PAYOUT-BATCH-771`
    - If Amount > $200.00: `DENIED — Exceeds autonomous limit ($200.00). Sent to Human Approvals Queue (Task #APP-104).`
- **Section D: Actions & Demo Injection Bar**
  - Client Actions: `Approve Payout`, `Request Revisions`, `Request Refund`.
  - Evaluator Demo Controls: Buttons to inject simulated scores (`0.95 Auto-Approve`, `0.72 Human Review`, `0.45 Reject`) calling `POST /milestones/{id}/_inject_verification`.

---

## PAGE 05 — ESCROW FINANCIAL LEDGER
- **HTML Target:** `ledger.html`
- **Route:** `/escrow-ledger`
- **Primary Persona:** Risk Officer / Finance Admin
- **Backend API Endpoints:**
  - `GET /projects` (Fetch all financial balances)
  - `GET /audit` (Fetch transaction audit records)
  - `GET /outbox` (Fetch dispatched PayPal Payout batches)

### Header & Financial KPI Cards
- Title: "Escrow Financial Ledger"
- Subtitle: "Double-entry accounting of all PayPal Order captures, holds, and Payout releases."
- KPI Summary Cards:
  1. `Total Funded into Escrow: $48,500.00 USD`
  2. `Total Released to Freelancers: $31,200.00 USD`
  3. `Total Refunded to Clients: $1,400.00 USD`
  4. `Active Escrow Balance on Hold: $15,900.00 USD`
- Actions: `Export CSV`, `Export PDF Audit Statement`.

### Master Ledger Table (AG Grid / Styled Table)
- **Columns:**
  1. Transaction ID (`TXN-2026-9041` - monospace)
  2. Timestamp (UTC, ISO formatted)
  3. Project Reference (`PRJ-2026-001`)
  4. Milestone Reference (`MS-2026-001-02: Frontend Integration`)
  5. Transaction Type (`CAPTURE_FUNDING`, `PAYOUT_RELEASE`, `REFUND`, `DISPUTE_FREEZE`)
  6. Debited Account (`Client PayPal Account`)
  7. Credited Account (`ProofPay Escrow Vault` / `Freelancer PayPal Account`)
  8. Amount (`$700.00 USD`)
  9. PayPal Reference ID (`CAPTURE-ID-8841` / `PAYOUT-ITEM-1029`)
  10. Policy Status (`ALLOWED`, `POLICY_BLOCKED`, `MANUAL_OVERRIDE`)
  11. SHA-256 Audit Link (lock icon opening audit drawer).
- Transaction Detail Flyout Drawer: Displays complete raw payload, PayPal API response, and audit verification proof.

---

## PAGE 06 — REVENUE RECOVERY OVERVIEW
- **HTML Target:** `recovery-overview.html`
- **Route:** `/recovery`
- **Primary Persona:** Merchant (Billing Admin) / Executive
- **Backend API Endpoints:**
  - `GET /reconciliation/summary` (Aggregated recovery totals)
  - `GET /cases` (List active and resolved cases)
  - `GET /reputation/merchant` (Merchant recovery health score)

### Header & Hero Metrics
- Title: "Revenue Recovery Overview"
- Subtitle: "Autonomous payment recovery powered by root-cause diagnosis, quiet-hour compliance, and 3-way reconciliation."
- Actions: `+ New Recovery Case`, `Run Batch Reconciliation`, `Run 150-Case Benchmark`.
- **Headline Recovery Metric Banner:**
  - **$12,450.00 Recovered of $18,600.00 at risk**
  - **67% Recovery Success Rate**
  - Incremental Revenue Generated: **+$8,250.00 USD** over traditional manual dunning (22% baseline).

### Section A: 4-Stage Recovery Funnel
Visual interactive funnel showing real-time drop-offs:
1. **Failed Payment Detected:** `150 Cases ($18,600.00)`
2. **Reconciliation Passed (Not Paid Elsewhere):** `142 Cases ($17,400.00)` *(8 cases stopped to prevent wrongful dunning!)*
3. **AI Diagnosed & Action Dispatched:** `142 Cases ($17,400.00)`
4. **Successfully Recovered via PayPal:** `101 Cases ($12,450.00)`
5. **Halted / Unrecovered:** `41 Cases ($4,950.00)`

### Section B: Root-Cause Diagnosis Distribution (Interactive Chart)
- **Expired Cards (42%):** Action -> Update Payment Method link via email.
- **Insufficient Funds (35%):** Action -> Smart retry scheduled after payday / payroll cycles.
- **Bank Authorization / SCA Failed (18%):** Action -> 1-click PayPal biometric authorization link.
- **Gateway Glitch / Other (5%):** Action -> Immediate retry with exponential backoff.

### Section C: Intervention Performance Table
- Lists conversion rate and average resolution time:
  - PayPal 1-Click Update Link: 74% conversion, avg recovery time 14 hours.
  - Smart Scheduled Retry: 58% conversion, avg recovery time 48 hours.
  - Polite In-App Reminder: 62% conversion, avg recovery time 26 hours.

---

## PAGE 07 — RECOVERY CASES MASTER TABLE & TIMELINE
- **HTML Target:** `cases.html`
- **Route:** `/recovery-cases`
- **Primary Persona:** Merchant (Billing Admin)
- **Backend API Endpoints:**
  - `GET /cases` (Filterable recovery case list)
  - `GET /cases/{case_id}` (Single case timeline, contact history, and diagnosis)
  - `POST /cases/{case_id}/reopen` (Reopen a halted or closed case)
  - `POST /approvals/{case_id}/decide` (Human approval for sensitive escalation)

### Master Cases Table
- **Filter Pills:** `All Cases (150)`, `Active (38)`, `Recovered (101)`, `Halted (8)`, `Unrecovered (3)`.
- **Search & Filter:** Search by Customer Name, Email, Invoice ID, or Diagnosis.
- **Columns:**
  1. Case ID (`REC-2026-0042` - monospace link opening drawer)
  2. Customer Name & Email (`Sarah Johnson <sarah@example.com>`)
  3. Source Invoice / Subscription ID (`INV-2026-1024`)
  4. Amount at Risk (`$350.00 USD`)
  5. Diagnosis (`EXPIRED_CARD`, `INSUFFICIENT_FUNDS`, `BANK_AUTH_FAILED`)
  6. Current Stage: Badge (`Stage 1: Soft Update Link`, `Stage 2: Firm Warning`, `Stage 3: Executive Pause`)
  7. Quiet Hours Status: Badge (`Active Hours - OK` [Green] or `Quiet Hours (9pm-8am) - Paused` [Amber])
  8. Reconciliation Status: Badge (`MATCHED`, `UNMATCHED`, `PAID_ELSEWHERE` [Red/Halted])
  9. Status: Badge (`ACTIVE`, `PAID`, `HALTED`, `UNRECOVERED`)
  10. Next Scheduled Action: Countdown (e.g. "In 18h 30m" or "Paused during quiet hours")
  11. Actions: `View Timeline`, `Open Recovery Portal (pay.html)`, `Halt Recovery`.

### Case Detail Drawer & Timeline (`cases.html` Flyout Drawer)
- Top Header: Customer Name, Case ID, Outstanding Amount, Status.
- Diagnosis Card: AI Explanation: "Customer card expired on 10/26. Soft reminder dispatched with secure PayPal payment method update token."
- Reconciliation Check: "Verified against Bank CSV: No offline match found. Safe to contact."
- **Interactive Chronological Timeline:**
  - `Day 0 08:30 UTC`: Payment failure received (`INSTRUMENT_DECLINED`).
  - `Day 0 08:31 UTC`: Case created; reconciliation passed.
  - `Day 0 09:00 UTC`: Stage 1 PayPal payment link generated and sent.
  - `Day 2 09:00 UTC`: (+48h ladder gap) Stage 2 reminder scheduled.
  - `Day 2 21:00 UTC`: Quiet hours active; outreach paused until 08:00 UTC next morning.
- Action Buttons: `Open Customer Pay Portal (pay.html)`, `Request Human Escalation`, `Mark Paid Elsewhere`, `Halt Recovery`.

---

## PAGE 08 — INVOICES & SUBSCRIPTIONS
- **HTML Target:** `invoices.html`
- **Route:** `/invoices`
- **Primary Persona:** Merchant (Billing Admin)
- **Tabs:**
  1. **Tab 1: Invoices**
     - Table of all issued invoices, due dates, paid status, and recovery links.
     - Button: `+ Create Invoice` (Modal: Customer, Line Items, Tax, Due Date, PayPal Invoicing integration).
  2. **Tab 2: Subscriptions**
     - Table of active recurring plans, billing cycles, next payment dates, and payment method health.
  3. **Tab 3: Failed Payments**
     - Live feed of failed subscription rebills and invoice payment drops.
  4. **Tab 4: Payment Links Generator**
     - Tool to instantly create a single-use PayPal checkout link for any overdue balance with customizable expiration.

---

## PAGE 09 — PAYMENT ATTEMPTS & GATEWAY LOGS
- **HTML Target:** `payment-attempts.html`
- **Route:** `/payment-attempts`
- **Primary Persona:** Merchant / Technical Support
- **Backend API Endpoints:**
  - `GET /cases` (Correlated attempt history)
  - `GET /outbox` (Webhook logs)

### Gateway Logs Table
- Columns:
  1. Attempt ID (`ATT-2026-5510`)
  2. Timestamp (UTC)
  3. Case Reference (`REC-2026-0042`)
  4. Customer Email
  5. Attempt Number (`Attempt 1 of 3`)
  6. Error Code (`INSTRUMENT_DECLINED`, `INSUFFICIENT_FUNDS`, `PAYER_ACTION_REQUIRED`, `TRANSACTION_REFUSED`)
  7. Gateway Message ("The cardholder's bank rejected the transaction.")
  8. Smart Retry Status: Next retry scheduled in `+48 hours` (skipping weekends/quiet hours).
  9. Result: `FAILED`, `SUCCEEDED`, `SKIPPED_QUIET_HOURS`.

---

## PAGE 10 — PAYMENT RECONCILIATION & 3-WAY MATCHING
- **HTML Target:** `reconciliation.html`
- **Route:** `/reconciliation`
- **Primary Persona:** Finance Admin / Risk Officer
- **Backend API Endpoints:**
  - `GET /reconciliation/summary` (Totals, matched, unmatched, paid elsewhere)
  - CSV Upload Endpoint (Import bank/gateway CSVs)

### Header & KPI Cards
- Title: "Payment Reconciliation & 3-Way Matching"
- Subtitle: "Automatically match bank statements and merchant ledgers against PayPal transactions to prevent wrongful dunning."
- KPI Summary Cards:
  1. `Total Ledger Records: 200`
  2. `Perfect 3-Way Matches: 168 (84%)`
  3. `Unmatched Invoices: 24 (12%)`
  4. `Paid Elsewhere (Offline/Wire): 8 (4%)` — **Halted from Dunning!**
  5. `Matching Confidence: 98.5%`

### Section A: 3-Source Reconciliation Dropzone
- Interactive 3-column file upload dropzone:
  - Column 1: `PayPal Gateway Report (.CSV)` [Uploaded: `paypal_nov_2026.csv` (184 txns)]
  - Column 2: `Merchant ERP Invoices (.CSV)` [Uploaded: `erp_billing_nov.csv` (200 records)]
  - Column 3: `Bank Offline Statement (.CSV)` [Uploaded: `bank_statement_nov.csv` (22 wires)]
- Action: `Run 3-Way Reconciliation Engine`

### Section B: Discrepancy & "Paid Elsewhere" Protection Table
- **Highlights the 8 critical "Paid Elsewhere" cases:**
  - Case: `REC-2026-0051 — Michael Anderson ($450.00 USD)`
  - PayPal Status: `FAILED (Card Declined)`
  - Bank Match: `MATCH FOUND (Direct Wire Transfer #WIRE-8891 of $450.00 received yesterday)`
  - System Action: `RECOVERY CAMPAIGN IMMEDIATELY HALTED`
  - Banner: `Safe! Customer was NOT sent an embarrassing overdue notice.`
- Reconciliation Match Detail Drawer: Side-by-side transaction comparison, fuzzy matching score, manual confirm button.

---

## PAGE 11 — DISPUTE MANAGEMENT & ESCROW FREEZE
- **HTML Target:** `disputes.html`
- **Route:** `/disputes`
- **Primary Persona:** Risk Officer / Merchant
- **Backend API Endpoints:**
  - `GET /projects` (Disputed project states)
  - `GET /cases` (Disputed recovery cases)
  - `GET /audit` (Cryptographic evidence records)

### Header & Critical Safety Feature
- Title: "Dispute Management & Evidence Center"
- Subtitle: "Instant escrow freeze and 1-click evidence pack compilation for PayPal dispute defense."
- Active Disputes Alert: `2 Active Disputes ($1,200.00 held)`
- **Autonomous Escrow Freeze Explanation Banner:**
  > **"When a dispute webhook (`CUSTOMER.DISPUTE.CREATED`) is received from PayPal, Mandate Guard immediately locks the affected milestone and freezes all payout execution until human review is complete."**

### Disputes Table
- **Columns:**
  1. Dispute ID (`DISP-2026-012`)
  2. PayPal Dispute Reference (`PP-D-998241`)
  3. Project / Invoice Reference (`PRJ-2026-003 / Milestone 2`)
  4. Disputing Party (`Acme Corp (Client)`)
  5. Amount Disputed (`$600.00 USD`)
  6. Dispute Reason (`Product / Work Not as Described`)
  7. Escrow Status: Badge (`FROZEN BY MANDATE GUARD` [Red])
  8. Recovery Status: Badge (`CAMPAIGN HALTED` [Red])
  9. Evidence Deadline Countdown (`4 Days Remaining`)
  10. Actions: `Generate Evidence Pack`, `Accept Dispute / Refund`, `Submit Defense`.

### Dispute Evidence Pack Generator (Flyout Drawer)
- Generates a PDF/ZIP dossier for PayPal Dispute Center containing:
  1. Original Scope & Dual-approved **Plan Hash** (`0a8f9c2...4e1`)
  2. Timestamped Client Approval Record
  3. Submitted GitHub Pull Request & Deployment Logs
  4. AI Verifier Inspection Report (Score: 92/100)
  5. Immutable SHA-256 Audit Chain Trail showing all agreements.
- Button: `Download PayPal Evidence Pack (PDF)`.

---

## PAGE 12 — MANDATE GUARD / POLICY ENGINE & SIMULATOR
- **HTML Target:** `mandate-guard.html`
- **Route:** `/mandate-guard`
- **Primary Persona:** Risk Officer / Platform Admin
- **Backend API Endpoints:**
  - `GET /audit` (Policy decision audit logs)
  - Policy evaluation simulator endpoints

### Header
- Title: "Mandate Guard / Policy Engine"
- Subtitle: "The deterministic financial firewall. AI agents recommend actions; Mandate Guard decides what executes."
- Status Pill: `Policy Engine: ACTIVE & ENFORCING (100% Deterministic)`.

### Section A: Live Configured Policy Rules
1. **Rule 1: Autonomous Payout Cap**
   - Threshold: `$200.00 USD`
   - Behavior: Any milestone payout <= $200 with verification score >= 0.80 executes autonomously. Payouts > $200 are **BLOCKED** and routed to Human Approvals Queue.
2. **Rule 2: Daily Payout Volume Limit**
   - Threshold: `$5,000.00 USD / Day`
   - Behavior: Caps total autonomous disbursements within a 24-hour window.
3. **Rule 3: Dual Approval Requirement**
   - Condition: `client_approved == true AND freelancer_approved == true`
   - Behavior: Rejects any funding or release where plan hashes do not match.
4. **Rule 4: Recipient Email Format & Verification**
   - Condition: Recipient must be a valid, formatted PayPal email.
5. **Rule 5: Quiet Hours Compliance**
   - Condition: `21:00 to 08:00 (Customer Local Time)`
   - Behavior: Halts all automated recovery outreach and payment retries during quiet hours.
6. **Rule 6: Dispute Circuit Breaker**
   - Condition: Any active PayPal dispute freezes corresponding escrow and halts recovery campaigns.

### Section B: Interactive Policy Simulator Sandbox
- Interactive tester where judges/operators can simulate policy evaluations:
  - Input: Amount (`$700.00`)
  - Input: Action Type (`ESCROW_RELEASE`)
  - Input: Verifier Score (`0.94`)
  - Input: Recipient (`freelancer@example.com`)
  - Button: `Evaluate Policy Now`
  - Output Card:
    - Result: `DENIED — Requires Human Approval`
    - Triggered Rule: `Rule 1: Amount $700.00 exceeds $200.00 autonomous threshold.`
    - Required Next Step: `Routed to Human Approvals Queue (Task #APP-104)`.

### Section C: Policy Decision History Table
- Recent evaluations showing Action, Proposed Amount, Decision (`ALLOWED` vs `DENIED`), Triggered Rule, Actor, and Link to SHA-256 Audit Trail.

---

## PAGE 13 — REPUTATION LEDGER & TRUST SCORES
- **HTML Target:** `reputation.html`
- **Route:** `/reputation`
- **Primary Persona:** Universal (Client, Freelancer, Merchant)
- **Backend API Endpoints:**
  - `GET /reputation/{subject}` (Fetch reputation score and tier)

### Header & Profile Search
- Title: "Reputation Ledger"
- Subtitle: "Cross-platform trust scores measuring milestone delivery, payment speed, and recovery responsiveness."
- Search bar: Search by Email, Username, or Wallet ID.

### Subject Profile Card (e.g. `Rahul Sharma - Freelancer`)
- **Trust Tier Badge:** `PLATINUM TRUST TIER` (Score: 98/100)
- **Key Metrics:**
  - Completed Milestones: `24`
  - On-Time Delivery Rate: `96%`
  - Average Verification Score: `94.2%`
  - Disputes Incurred: `0`
  - Total Volume Released via PayPal: `$42,800.00 USD`
- **Historical Trust Timeline:**
  - Chronological chart showing trust score progression over the past 12 months.

---

## PAGE 14 — HUMAN APPROVALS QUEUE & DECISION INBOX (HITL)
- **HTML Target:** `approvals.html`
- **Route:** `/approvals` and `/submission-approvals`
- **Primary Persona:** Risk Officer / Platform Admin
- **Purpose:** **Core PayPal AI Hackathon Requirement: Safe Autonomous AI with Human-in-the-Loop Guardrails.** Centralized inbox where operators review payouts exceeding policy caps (>$200), borderline AI verification scores (60–80%), and sensitive recovery actions before financial execution.
- **Backend API Endpoints:**
  - `GET /submission-approvals` (Pending milestone payout releases)
  - `POST /submission-approvals/{task_id}/decide` (Approve or Deny milestone payout)
  - `GET /approvals` (Recovery case proposals requiring sign-off)
  - `POST /approvals/{case_id}/decide` (Approve or Deny recovery intervention)

### Header & Pending Counts
- Title: "Human Approvals Queue & Governance Inbox"
- Subtitle: "Human-in-the-Loop decision center for high-value payouts, borderline AI scores, and sensitive recovery interventions."
- **Pending Alert Badges:**
  - `⚠️ 2 Milestone Payouts Awaiting Review (Oversized > $200.00 Limit)`
  - `⚠️ 1 Recovery Escalation Awaiting Sign-off (Stage 3 Account Suspension)`

### Tab 1: Escrow Milestone Payout Approvals (`GET /submission-approvals`)
- Table of payouts flagged by Mandate Guard:
  - **Columns:**
    1. Task ID (`TASK-APP-104` - monospace link)
    2. Milestone ID & Project Name (`MS-2026-001-02` / `E-commerce Web App`)
    3. Freelancer Recipient (`freelancer@example.com`)
    4. Amount (`$700.00 USD` — Badge: `Exceeds $200 Cap`)
    5. AI Verification Score (`94% - Passed all automated criteria`)
    6. Flag Reason (`OVERSIZED_PAYOUT: Amount exceeds $200.00 autonomous threshold`)
    7. Submitted Date (Timestamp)
    8. Actions: `Review & Decide` (opens modal).

### Tab 2: Recovery Intervention Approvals (`GET /approvals`)
- Table of high-risk recovery actions:
  - **Columns:**
    1. Case ID (`REC-2026-0089`)
    2. Customer Name & Company (`Acme Corp`)
    3. Amount at Risk (`$1,850.00 USD`)
    4. Proposed Action (`STAGE_3_SERVICE_SUSPENSION` or `DEBT_SETTLEMENT_DISCOUNT_20%`)
    5. Risk Level (`HIGH RISK` [Red])
    6. Reason for Human Review (`Amount exceeds $1,000 policy threshold; service suspension requested`)
    7. Actions: `Review & Decide`.

### Human Decision Modal (Comprehensive Evidence Inspection)
- Opens when clicking `Review & Decide`:
  - **Top Banner:** Milestone Amount (`$700.00 USD`), Recipient (`freelancer@example.com`), Project (`E-commerce Web App`).
  - **Mandate Guard Flag:** "Policy blocked autonomous payout because amount ($700.00) exceeds $200.00 cap. Human confirmation required."
  - **Evidence Summary:**
    - GitHub PR Link: `https://github.com/acme/shop/pull/42`
    - Staging URL: `https://staging-shop.acme.app` (HTTP 200 OK)
    - Verifier Score: `94/100` (All critical tests passed).
  - **Reviewer Input Fields:**
    - Decision: Radio selection (`Approve Payout` [Green] | `Deny / Request Revisions` [Red]).
    - Reviewer Notes (`textarea`, required, e.g. "Reviewed PR code quality and live preview. Deliverable satisfies all milestone criteria.").
  - **Action Buttons:**
    - `Confirm Decision & Execute PayPal Payout`:
      - Calls `POST /submission-approvals/{task_id}/decide` with `{"decision": "APPROVE", "notes": "..."}`.
      - Executor dispatches PayPal Payout API, records transaction in ledger, and appends to SHA-256 audit chain.
    - `Cancel`: Closes modal without action.

---

## PAGE 15 — AI AGENT CONTROL CENTER & FLEET MONITOR
- **HTML Target:** `agents.html`
- **Route:** `/agents`
- **Primary Persona:** Platform Engineer / Risk Officer
- **Backend API Endpoints:**
  - `GET /healthz` (System & agent health)

### Header & Emergency Kill-Switch
- Title: "AI Agent Control Center"
- Subtitle: "Fleet observability, execution latency, model configurations, and kill-switch controls."
- Global Kill-Switch Button: `PAUSE ALL AUTONOMOUS AGENTS (Emergency Fallback)`.

### The 6 Specialized Agent Cards
1. **AI Scoping Agent**
   - Role: Analyzes project briefs, extracts acceptance criteria, drafts milestone allocations.
   - Status: `ONLINE [Green]`, Latency: `1.4s`, Model: `Gemini / Claude Sonnet`.
2. **Milestone Verification Agent**
   - Role: Inspects GitHub PRs, runs test suites, queries deployed URLs, scores deliverables.
   - Status: `ONLINE [Green]`, Latency: `3.2s`, Accuracy: `96.8%`.
3. **Recovery Diagnosis Agent**
   - Role: Classifies payment failure codes, identifies card expiration vs insufficient funds.
   - Status: `ONLINE [Green]`, Accuracy: `98.2%`.
4. **Contact Ladder Orchestrator**
   - Role: Schedules 3-stage reminders, enforces 48h ladder timeouts and quiet hours.
   - Status: `ONLINE [Green]`.
5. **Reconciliation Matching Agent**
   - Role: Executes 3-way matching between PayPal, bank statements, and ERP.
   - Status: `ONLINE [Green]`, Match Rate: `98.5%`.
6. **Mandate Guard Policy Evaluator**
   - Role: Strictly evaluates proposals against deterministic Python safety rules.
   - Status: `ONLINE [Green]`, Latency: `< 5ms` (Pure deterministic code).

---

## PAGE 16 — ANALYTICS, ROI & BENCHMARK REPORTS
- **HTML Target:** `analytics.html`
- **Route:** `/analytics`
- **Primary Persona:** Executive / Hackathon Judge
- **Backend API Endpoints:**
  - `GET /reconciliation/summary`
  - `GET /projects`
  - `GET /cases`

### Key Analytical Sections
1. **Escrow Velocity & Throughput:** Average days from milestone creation to client funding (1.2 days) and submission to release (4.1 hours).
2. **Recovery Engine ROI:**
   - Total at risk: `$18,600.00 USD`
   - Total recovered: `$12,450.00 USD`
   - Net Recovered Revenue: **+$8,250.00 incremental gain** over traditional dunning.
3. **Agent vs Baseline Comparison Chart (Benchmark Performance):**
   - Traditional Manual Dunning: 22% recovery rate, 12 days average time, 4.2% dispute rate.
   - ProofPay Autonomous Recovery: 67% recovery rate, 2.4 days average time, 0.4% dispute rate.
4. **Export Options:** Download Full Financial Report (`PDF` / `CSV`).

---

## PAGE 17 — AUDIT TRAIL (TAMPER-EVIDENT SHA-256 HASH CHAIN)
- **HTML Target:** `audit.html`
- **Route:** `/audit`
- **Primary Persona:** Risk Officer / Auditor / Hackathon Judge
- **Backend API Endpoints:**
  - `GET /audit` (Chronological event stream with row hashes and previous hashes)

### Header & Cryptographic Integrity Badge
- Title: "Tamper-Evident Audit Trail"
- Subtitle: "Every financial and policy decision linked via SHA-256 cryptographic hash chains."
- **Chain Verification Badge:**
  - Large Green Pill: `🔒 Cryptographic Chain Verified: 100% Valid (All 248 Hashes Match)`
  - Subtext: "Verified 248 chained events. No tampering detected."

### Master Audit Table
- **Columns:**
  1. Event ID (`AUD-00248` - monospace)
  2. Timestamp (UTC, millisecond precision)
  3. Entity Type & ID (`milestone: MS-2026-001-02`)
  4. Actor (`mandate_guard` / `verifier_agent` / `client`)
  5. Action (`POLICY_EVALUATION`, `SUBMISSION_VERIFIED`, `PAYOUT_DISPATCHED`)
  6. Decision / Payload Summary (`ALLOWED - Released $200.00 via PayPal Payouts`)
  7. Previous Hash (`prev_hash`: `3e8b...9f1` - first 8 chars)
  8. Row Hash (`row_hash`: `8a1c...44d` - first 8 chars)
  9. Chain Link Status (`Valid Link` [Green Lock Icon])
  10. Action: `Inspect Details` (opens flyout drawer).

### Audit Event Inspection Drawer
- Full JSON payload of the event.
- Cryptographic proof details:
  - Canonical JSON string representation.
  - Previous Row Hash.
  - Computed Row Hash.
  - Button: `Re-Verify SHA-256 Hash Locally in Browser`.

---

## PAGE 18 — AI ASSISTANT (CITED READ-ONLY CHATBOT)
- **HTML Target:** `assistant.html`
- **Route:** `/assistant`
- **Primary Persona:** Universal
- **Safety Badge:** `READ-ONLY MODE: Cannot execute financial disbursements or mutate policies.`

### Layout & Chat Experience
- Left Sidebar: Suggested Questions & Recent Conversations.
- Center Chat Area:
  - System Greeting: "Hello! I am your ProofPay Assistant. Ask me anything about milestone escrow, payment recovery, reconciliation, or policy decisions."
  - Sample Prompts:
    - "Why was milestone #2 payout held by Mandate Guard?"
    - "Show me all recovery cases halted due to offline bank payments."
    - "What is our current recovery success rate for expired cards?"
    - "Verify the plan hash for Project PRJ-2026-001."
- **Response Format:**
  - Direct answer.
  - Clickable audit citations linking directly to Audit Trail (`audit.html`) or Case Drawer (`cases.html`).
  - Transaction references.

---

## PAGE 19 — INTEGRATIONS & PAYPAL CONNECT
- **HTML Target:** `integrations.html`
- **Route:** `/integrations`
- **Primary Persona:** Platform Engineer
- **Backend API Endpoints:**
  - `POST /webhooks/paypal` (Live webhook processor)
  - Integration health checks

### PayPal Integration Master Card
- Logo: Official PayPal Business badge.
- Status: `Connected to PayPal Sandbox` [Green Pill].
- Merchant ID: `M-882941094` (masked).
- Active APIs Enabled:
  - `PayPal Orders v2` (Escrow creation & capture)
  - `PayPal Payouts API` (Milestone disbursement)
  - `PayPal Invoicing API` (Billing & invoice recovery)
  - `PayPal Webhooks API` (Real-time capture, payout, and dispute events)
- Actions: `Test Connection`, `Rotate API Keys`, `Manage Webhooks`.

### Additional Integrations
- GitHub Evidence Connector (OAuth linked to repositories for PR verification).
- Bank Statement CSV Parser.
- Webhook Event Log Viewer with replay capability.

---

## PAGE 20 — SETTINGS
- **HTML Target:** `settings.html`
- **Route:** `/settings`
- **Primary Persona:** Workspace Owner
- **Tabs:**
  1. **Profile:** Name, email, PayPal recipient email, timezone.
  2. **Workspace:** Business name, tax ID, default currency (USD).
  3. **Team & Permissions:** Manage Client, Freelancer, Merchant, and Risk Officer access.
  4. **Notifications:** Email & webhook alerts for disputes, verification failures, and payouts.
  5. **Security & Sessions:** API key management, 2FA status, session timeout.

---

## PAGE 21 — HELP & SUPPORT
- **HTML Target:** `help.html`
- **Route:** `/help`
- **Primary Persona:** Universal
- **Content Sections:**
  1. Getting Started Guide.
  2. Escrow PREVENT Guide (Dual approval & AI verification).
  3. Revenue RECOVER Guide (3-way reconciliation stops wrongful dunning).
  4. Mandate Guard Explained (Deterministic AI safety firewalls).
  5. PayPal Integration Architecture.
  6. Interactive Support Ticket Form.

---

## PAGE 22 — DEMO & SIMULATION LAB / HACKATHON EVALUATOR PANEL
- **HTML Target:** `demo.html`
- **Route:** `/demo`
- **Primary Persona:** **Hackathon Judge / Evaluator**
- **Purpose:** **Interactive Sandbox & Benchmark Control Center for Hackathon Judges and Evaluators.** Allows evaluators to advance simulated time, inject failure edge cases, run the 150-case synthetic benchmark, and reset state with zero setup friction.
- **Backend API Endpoints:**
  - `POST /demo/advance-clock` (Advance simulated time by +24h, +48h, +7d)
  - `POST /demo/inject-failure` (Inject card, dispute, or plan hash failures)
  - `POST /demo/run-simulator` (Run 150 benchmark cases and calculate statistics)
  - `POST /demo/reset` (Reset DB to pristine seeded demo state)
  - `POST /milestones/{milestone_id}/_inject_verification` (Inject simulated AI verification score)

### Header & Live Evaluator Controls
- Title: "Hackathon Demo & Simulation Lab"
- Subtitle: "Interactive controls for hackathon judges to evaluate time-lapse recovery, edge-case failures, and benchmark accuracy."
- **Live Simulated Clock Card:**
  - Current Simulated Time: `2026-11-12 14:30:00 UTC`
  - Quiet Hours Status: `ACTIVE BUSINESS HOURS (Quiet hours: 21:00 to 08:00)`

### Section A: Simulated Clock Controller (`POST /demo/advance-clock`)
- Presets:
  - `[ +24 Hours ]`: Advances clock 1 day. Triggers scheduled retry checks and skips quiet hours.
  - `[ +48 Hours ]`: Advances clock 2 days. Triggers Stage 2 contact ladder progression.
  - `[ +7 Days ]`: Advances clock 1 week. Tests final case expiration or resolution.
- Custom Hours Input: `input[number]` + `Advance Custom Hours` button.
- Real-time Output Log: Displays which scheduled tasks woke up and executed upon clock tick.

### Section B: Edge-Case Failure Injector (`POST /demo/inject-failure`)
- Dropdown of test scenarios for live judges:
  1. `Scenario 1: Insufficient Funds (Subscription Rebill)` -> Sets customer balance low; triggers smart retry scheduling.
  2. `Scenario 2: Expired Credit Card` -> Injects expired expiration date; triggers payment method update link.
  3. `Scenario 3: PayPal Dispute Filed` -> Simulates `CUSTOMER.DISPUTE.CREATED` webhook; tests immediate escrow freeze and recovery halt!
  4. `Scenario 4: Plan Hash Tamper Mismatch` -> Modifies milestone scope without dual approval; verifies that approval is rejected with 409 Conflict.
- Target ID: Select Project or Case ID.
- Button: `Inject Failure Scenario` -> Immediately tests system resilience!

### Section C: 150-Case Benchmark Simulator (`POST /demo/run-simulator`)
- Card: "Synthetic Dataset Benchmark Runner (150 Cases)"
- Description: Evaluates the RECOVER Engine against a realistic, seeded dataset of 150 failed payments across SaaS and freelance models.
- Button: `🚀 Run 150-Case Simulation Benchmark`
- **Live Results Dashboard (Updates on completion):**
  - **ProofPay Autonomous Recovery:**
    - Recovery Rate: **67.0% (101 / 150 cases recovered)**
    - Total Recovered: **$12,450.00 USD**
    - Wrongful Dunning Prevented: **8 cases (Paid elsewhere detected)**
  - **Traditional Dunning Baseline:**
    - Recovery Rate: **22.0% (33 / 150 cases recovered)**
    - Total Recovered: **$4,200.00 USD**
  - **Net Incremental Benefit:** **+$8,250.00 USD recovered (3.0x improvement!)**

### Section D: Manual Verifier Score Injector
- Select active milestone: `MS-2026-001-02`
- Score Slider: `0.00` to `1.00`
- Presets:
  - `Preset: High Pass (0.95) -> Route: AUTO_APPROVE`
  - `Preset: Borderline (0.72) -> Route: HUMAN_REVIEW`
  - `Preset: Failure (0.45) -> Route: AUTO_REJECT`
- Button: `Inject Verification Result` -> calls `POST /milestones/{id}/_inject_verification`.

### Section E: Environment Reset (`POST /demo/reset`)
- Button: `🔄 Reset Database to Pristine Demo State`
- Restores all initial projects, milestones, cases, and audit logs for a fresh live demo!

---

## PAGE 23 — CUSTOMER PAYMENT RECOVERY PORTAL (DEBTOR CHECKOUT)
- **HTML Target:** `pay.html` (or `payment-portal.html`)
- **Route:** `/pay/{case_id}` or `pay.html?case_id=REC-2026-0042`
- **Primary Persona:** **Customer / Debtor (External Public Page)**
- **Purpose:** **The Customer-Facing Payment Checkout Link.** When the RECOVER Engine sends a recovery link via email/SMS, the customer clicks and opens this standalone, secure, mobile-optimized page to settle their overdue invoice or update their payment method in 1 click using PayPal.
- **Backend API Endpoints:**
  - `GET /cases/{case_id}` (Fetch invoice amount, merchant name, due date)
  - `POST /cases/{case_id}/pay` (or PayPal Checkout Capture webhook)
  - `POST /webhooks/paypal` (Receives `PAYMENT.CAPTURE.COMPLETED` and marks case `PAID`)

### Layout & Visual Design
- Clean, trustworthy, mobile-responsive layout (no internal navigation sidebar; centered card layout).
- Top Header: Merchant Name & Logo (e.g. "Acme Cloud Services") + "Powered by ProofPay & PayPal".
- Security Badges: `🔒 256-Bit SSL Encrypted` | `Verified by PayPal`.

### Content Elements
1. **Invoice Overview Card:**
   - Outstanding Balance: **$350.00 USD**
   - Invoice Reference: `INV-2026-1024`
   - Due Date: `November 10, 2026 (Overdue)`
   - Item Description: "Pro Cloud Subscription — Monthly Renewal (Failed Card Charge)"
2. **Payment Options Container:**
   - **Option A: 1-Click PayPal Checkout (PayPal Smart Payment Button):**
     - Customer clicks yellow PayPal button.
     - Authenticates and authorizes payment in PayPal popup.
     - Instant settlement!
   - **Option B: Update Credit/Debit Card Details:**
     - Enter updated card details to update recurring billing subscription.
3. **Payment Completion State (Live Feedback):**
   - Upon successful payment:
     - Card transitions to green success checkmark: `✅ Payment Successful! Thank You.`
     - Displays PayPal Transaction ID: `PP-TXN-994102`.
     - Confirmation note: "Your invoice has been marked PAID and your service remains uninterrupted."
     - Triggers backend webhook callback -> Case `REC-2026-0042` transitions to `PAID` in `cases.html` and `dashboard.html`!

---

# PART 5 — GLOBAL INTERACTION AND COMPONENT REQUIREMENTS

All 23 pages share a unified, reusable component architecture.

## 5.1 Status Badges
Every badge uses a rounded pill design (`padding: 4px 10px; font-size: 12px; font-weight: 500; border-radius: 9999px;`):
- **Green (`#E8F5E9` bg, `#2E9D65` text):** `PAID`, `FUNDED`, `VERIFIED`, `RECOVERED`, `ALLOWED`, `AUTO_APPROVE`, `ACTIVE`.
- **Amber (`#FFF8E1` bg, `#F5A623` text):** `AWAITING_APPROVAL`, `IN_REVIEW`, `HUMAN_REVIEW`, `QUIET_HOURS_PAUSED`, `BORDERLINE`.
- **Red (`#FFEBEE` bg, `#D9363E` text):** `POLICY_BLOCKED`, `DISPUTED`, `FROZEN`, `AUTO_REJECT`, `FAILED`, `UNRECOVERED`.
- **Blue (`#E3F2FD` bg, `#0070E0` text):** `SUBMITTED`, `VERIFYING`, `PAYOUT_PROPOSED`, `MATCHED`.
- **Gray (`#F0F3F8` bg, `#64748B` text):** `DRAFT`, `CANCELLED`, `CLOSED`.

## 5.2 Buttons
- **Primary CTA (`#0070E0`):** White text, subtle hover brightness, `border-radius: 6px`.
- **Secondary (`#FFFFFF`):** Gray border (`#E5E9F0`), dark text (`#172B4D`), hover `#F8FAFC`.
- **Danger (`#D9363E`):** Red text or background for dispute escalation or rejection.
- **Ghost / Icon:** Transparent background, gray hover.

## 5.3 Modals & Drawers
- Standardized modal backdrop (`rgba(10, 37, 64, 0.4)`).
- Slide-over right drawer (`width: 480px` to `600px`) for transaction inspection, case timelines, and audit event proofs.

## 5.4 Toast Notifications
- Floating notifications top-right:
  - `Success: Milestone deliverable submitted successfully.`
  - `Policy Alert: Payout exceeds $200.00 limit. Routed to Human Approvals Queue.`
  - `Reconciliation: 3-way matching completed: 8 cases marked Paid Elsewhere.`

---

# PART 6 — REALISTIC AND INTERCONNECTED DEMO DATA

To ensure an interconnected and believable live demonstration:

### Sample Project: PRJ-2026-001
- **Project Name:** E-commerce Website Development
- **Client:** Acme Global Solutions (`client@example.com`)
- **Freelancer:** Rahul Sharma (`freelancer@example.com`)
- **Total Value:** `$2,400.00 USD`
- **Milestones:**
  1. UI Design & Figma Tokens — `$400.00` (`PAID`)
  2. Frontend Integration & API Client — `$700.00` (`SUBMITTED` / `UNDER_REVIEW`)
  3. Backend & PayPal Checkout — `$800.00` (`FUNDED`)
  4. QA, Testing & Deployment — `$500.00` (`FUNDED`)

### Sample Recovery Case: REC-2026-0042
- **Customer:** Sarah Johnson (`sarah@example.com`)
- **Invoice ID:** `INV-2026-1024`
- **Amount:** `$350.00 USD`
- **Diagnosis:** `EXPIRED_CARD`
- **Current Action:** Sent PayPal payment method update link (`pay.html?case_id=REC-2026-0042`).
- **Status:** `ACTIVE (Awaiting customer payment)`.

### Sample Blocked Action (Human-in-the-Loop Showcase)
- **Action:** Milestone 2 Payout Release (`$700.00 USD`)
- **Policy Limit:** `$200.00 USD`
- **Result:** `BLOCKED — Over Limit -> Routed to Human Approvals Queue (Task #APP-104)`.

### Sample Paid-Elsewhere Case (Reconciliation Showcase)
- **Customer:** Michael Anderson (`michael@example.com`)
- **Amount:** `$450.00 USD`
- **Gateway Status:** `FAILED`
- **Bank Match:** Found offline wire transfer of `$450.00`.
- **Result:** `PAID_ELSEWHERE -> Outreach permanently halted`.

---

# PART 7 — CRITICAL END-TO-END DEMONSTRATION FLOWS

The UI must support demonstrating these 7 core flows:

- **FLOW A: Project Creation to Escrow Funding**
  Create project -> Add milestones -> View plan hash -> Dual approval (Client & Freelancer) -> Fund via PayPal Orders v2 -> Status becomes `FUNDED`.
- **FLOW B: Work Submission to AI Verification & Autonomous Payout**
  Submit GitHub PR link (< $200 milestone) -> AI Verification Agent scores 94% -> Route `AUTO_APPROVE` -> Mandate Guard checks policy (`ALLOWED`) -> Dispatches PayPal Payout -> Ledger & Audit updated.
- **FLOW C: Human-in-the-Loop Governance on Oversized Payouts**
  Submit deliverable on $700 milestone -> Verifier scores 94% -> Mandate Guard flags `Amount > $200` -> Routes to `Page 14: Approvals Queue` -> Operator inspects PR and clicks Approve -> PayPal Payout executes!
- **FLOW D: Failed Payment Recovery via Customer Portal**
  Payment failure ingested -> Diagnosis `EXPIRED_CARD` -> Stage 1 PayPal update link sent -> Customer opens `pay.html` -> Customer completes payment via PayPal -> Webhook captures payment -> Case marked `PAID`.
- **FLOW E: Reconciliation Stopping Wrongful Dunning**
  Failed card detected -> Reconciliation matches offline bank wire -> Case marked `PAID_ELSEWHERE` -> Outbound reminders permanently blocked.
- **FLOW F: PayPal Dispute Escrow Freeze**
  Dispute webhook simulated -> Mandate Guard freezes escrow -> Recovery halted -> Evidence pack compiled with plan hash and test reports.
- **FLOW G: Evaluator Time-Lapse & Clock Advance**
  Evaluator clicks `[🕒 +24h]` or `[🕒 +48h]` -> Simulated clock fast-forwards -> Quiet hours observed -> Scheduled retries execute automatically.

---

# PART 8 — STANDALONE FRONTEND ARCHITECTURE & HTML GENERATION GUIDE

## 8.1 Standalone HTML File Directory Structure
The frontend is organized as modular standalone HTML files that can be opened directly in any browser or served statically:

```text
e:\Projects\ProofPay\
├── frontend/ (or backend/app/static/)
│   ├── index.html                 (Page 01: Dashboard)
│   ├── projects.html              (Page 02: Projects Master List & Intake)
│   ├── project-details.html       (Page 02B: Project Details, Dual Approval & PayPal Funding)
│   ├── milestones.html            (Page 03: Milestones Central Tracker)
│   ├── submissions.html           (Page 04: Submissions & AI Verification Inspection)
│   ├── ledger.html                (Page 05: Escrow Financial Ledger)
│   ├── recovery-overview.html     (Page 06: Revenue Recovery Overview & Funnel)
│   ├── cases.html                 (Page 07: Recovery Cases Master Table & Timeline)
│   ├── invoices.html              (Page 08: Invoices & Subscriptions)
│   ├── payment-attempts.html      (Page 09: Gateway Logs & Retries)
│   ├── reconciliation.html        (Page 10: 3-Way Reconciliation Matching)
│   ├── disputes.html              (Page 11: Dispute Freeze & Evidence Packs)
│   ├── mandate-guard.html         (Page 12: Policy Engine & Simulator)
│   ├── reputation.html            (Page 13: Reputation Ledger)
│   ├── approvals.html             (Page 14: Human Approvals Queue / HITL)
│   ├── agents.html                (Page 15: AI Agent Control Center)
│   ├── analytics.html             (Page 16: Analytics & ROI Reports)
│   ├── audit.html                 (Page 17: Tamper-Evident SHA-256 Audit Trail)
│   ├── assistant.html             (Page 18: Read-Only Cited AI Assistant)
│   ├── integrations.html          (Page 19: PayPal API & Webhook Config)
│   ├── settings.html              (Page 20: Workspace Settings)
│   ├── help.html                  (Page 21: Knowledge Base & Docs)
│   ├── demo.html                  (Page 22: Demo Lab & Evaluator Sandbox)
│   ├── pay.html                   (Page 23: Customer Recovery Payment Portal)
│   │
│   ├── css/
│   │   ├── design-system.css      (Unified color tokens, typography, cards, badges)
│   │   └── tailwind.min.css       (Tailwind styling baseline)
│   │
│   └── js/
│       ├── api-client.js          (REST API client connecting to http://localhost:8000)
│       ├── role-switcher.js       (Manages active persona: Client, Freelancer, Merchant, Admin)
│       ├── demo-bar.js            (Sticky evaluator bar for clock advance, failure injection, reset)
│       ├── components.js          (Reusable sidebar, top header, modal, drawer, and toast handlers)
│       └── mock-fixtures.js       (Instant fallback demo data when backend is disconnected)
```

## 8.2 API Integration Pattern
Every page includes `api-client.js`:
- Attempts to fetch live data from `http://localhost:8000`.
- If the backend is unreachable or in static file demo mode, it seamlessly falls back to `mock-fixtures.js` so all tables, charts, and drawers populate with zero errors.
- Never hardcode PayPal client secrets or private keys in frontend JavaScript.

---

# PART 9 — DESIGN QUALITY AND PRIORITIES

The final presentation must feel like an authentic, enterprise-grade financial SaaS platform.

### What to Avoid:
- Generic admin dashboard templates with exaggerated round cards or neon gradients.
- Hardcoded static text where data should be dynamic.
- Untested buttons that do nothing when clicked.
- Pages without loading, empty, and error fallback states.

### What to Prioritize:
1. **Financial Clarity:** Currency values clearly formatted (`$2,400.00 USD`).
2. **Deterministic Governance:** Prominently visualize when Mandate Guard blocks or approves an action.
3. **Audit Trail Links:** Every financial change should show its corresponding SHA-256 hash link.
4. **Interactive Persona Switching:** Evaluators can switch between Client, Freelancer, and Admin in 1 click.
5. **Hackathon Evaluator Friendly:** The floating demo bar allows testing time advance, failure injection, and 150 benchmark cases instantly.

---

# PART 10 — DEVELOPER IMPLEMENTATION CHECKLIST (DEV 1 & DEV 4)

When generating the individual HTML files:
- [x] Every page uses the shared Deep Navy (`#003087`) sidebar with all navigation items.
- [x] Every page includes the Top Header with Breadcrumbs, Search, Notification Bell, and the **Role Switcher**.
- [x] Every page includes the sticky **Hackathon Evaluator Quick Bar** (`Clock Advance`, `Inject Failure`, `Run Benchmark`, `Reset`).
- [x] All table columns and modal fields match the exact schemas in `contracts/openapi.json`.
- [x] Dual approval plan hash verification is functional.
- [x] PayPal checkout buttons and webhook confirmations are rendered cleanly.
- [x] Human Approvals Queue (`Page 14`) allows 1-click Approve/Deny with audit trail recording.
- [x] Demo Lab (`Page 22`) provides full clock control and 150-case benchmark simulation telemetry.
- [x] Customer Recovery Portal (`Page 23: pay.html`) enables live end-to-end payment settlement.

**"Every payment is protected. Every recovery is intelligent. Every action is accountable."**
"""

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Generated master UI specification to {OUTPUT_PATH}")
print(f"File size: {len(content)} characters, {len(content.splitlines())} lines.")

