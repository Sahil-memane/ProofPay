# MASTER UI/UX DESIGN PROMPT — PROOFPAY
## Agentic Escrow & Intelligent Revenue Recovery Platform
### Complete Multi-Page UI Specification & Frontend Architecture Guide (23 Pages)

**Role Context:**
Act as a Senior Product Designer, FinTech UI/UX Architect, and Enterprise Frontend Engineer (Dev 1 Tech Lead + Dev 4 Frontend UI Lead).

Your task is to design, specify, and build a complete, high-fidelity, multi-page financial SaaS web application named **ProofPay**.

This is not a mock landing page. It is a complete operational web application with interconnected pages, you need t design one at a time, persistent navigation, detailed input forms, financial ledgers, analytics dashboards, AI agent observability interfaces, PayPal checkout & payout workflows, deterministic policy controls, human-in-the-loop governance queues, and cryptographic audit functionality.

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

# PART 4 — PAGE DESIGN SPECIFICATION

PAGE 00 — PROOFPAY LANDING PAGE
- HTML Target: landing.html
- Route: /
- Primary Persona: Hackathon Judges, Potential Customers, Freelancers & Businesses
- Purpose: Public Product Homepage. Showcase ProofPay's AI-powered escrow and revenue recovery platform, its PayPal integration, benchmark results and core financial safeguards.
Layout & Visual Design
- Premium, modern fintech landing page inspired by Stripe, PayPal and Linear.
- Deep navy (#003087), royal blue (#0070E0) and white color palette.
- Clean typography, subtle gradients, elegant animations and responsive design.
- Full-width hero section with a sophisticated dashboard preview or financial visualization.
- No dashboard sidebar; use a sleek navigation bar.
Content Elements
1. Navigation Header:
- Left: ProofPay logo and brand name.
- Right: Open Dashboard → button.
2. Hero Section:
- Headline: AI-Powered Escrow & Revenue Recovery
- Description: "ProofPay combines autonomous failed-payment recovery with cryptographic freelance escrow — all powered by LangGraph agents and PayPal APIs."
- CTAs: View Dashboard | See Benchmark Results
3. Performance Metrics Section: Display four prominent KPI cards:
- 28.67% — Agent Recovery Rate (vs 8% baseline).
- 3.58× — More Revenue Recovered ($11,010 vs $2,560).
- 0% — Wrongful Contacts (100% precision).
- $200 — Mandate Guard Cap (Human-in-the-Loop above).
4. Core Engines Section: Two large side-by-side feature cards.

Engine 1 — PREVENT | Freelance Escrow
- Dual cryptographic plan approval (SHA-256).
- Milestone-based payment release.
- AI work verification (LangGraph verifier).
- Mandate Guard policy gating.
- PayPal Orders v2 + Payouts.
Engine 2 — RECOVER | Revenue Recovery
- 3-stage autonomous contact ladder.
- Root-cause diagnosis (LangGraph).
- 3-way reconciliation (ProofPay ↔ PayPal ↔ Bank).
- Quiet-hours & TCPA compliance.
- 28.67% recovery vs 8% baseline.
5. Trust & Technology Banner:
- Prominent statement: "AI recommends. Policy decides. PayPal executes. Every action is auditable."
- Link: API Docs → pointing to http://localhost:8000/docs.
Functional Requirements
- Open Dashboard and View Dashboard → Main ProofPay dashboard.
- See Benchmark Results → Benchmark section or demo page.
- API Docs → Backend API documentation.
- Fully responsive with functional navigation and polished hover interactions.
Design Objective: Reproduce the content hierarchy above in an exceptionally polished, visually striking fintech landing page. Make benchmark metrics immediately visible, give equal importance to PREVENT and RECOVER, and establish ProofPay's credibility within the first screen.
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