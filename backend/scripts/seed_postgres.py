"""
Seed Postgres database with initial users and static records from data/generated/.
Safe to run repeatedly (upsert / check existence).
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.db.session import sync_engine
from backend.app.db.models.users import User
from backend.app.db.models.projects import Project, Milestone, LedgerEntry
from backend.app.db.models.cases import Case
from backend.app.db.models.entities import (
    Customer,
    Invoice,
    Subscription,
    PayPalTransaction,
    MerchantSale,
)
from backend.app.db.models.support import ReconRecord

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "generated"


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_users(session: Session) -> None:
    # Maps (email, name, role, customer_id) — customer_id links to CUST-XXXXX in entities tables.
    # admin/risk_officer have customer_id=None → they see all data.
    demo_users = [
        # ── Original 4 users ──
        {"email": "client@example.com",      "name": "Acme Global Solutions", "role": "client",       "customer_id": "CUST-00010"},
        {"email": "freelancer@example.com",  "name": "Rahul Sharma",          "role": "freelancer",   "customer_id": "CUST-00081"},
        {"email": "merchant@example.com",    "name": "Sahil",                 "role": "merchant",     "customer_id": "CUST-00002"},
        {"email": "admin@example.com",       "name": "Risk Officer",          "role": "admin",        "customer_id": None},
        # ── Additional clients ──
        {"email": "client2@example.com",     "name": "Nexus Corp",            "role": "client",       "customer_id": "CUST-00068"},
        {"email": "client3@example.com",     "name": "Global Trade Ltd",      "role": "client",       "customer_id": "CUST-00089"},
        # ── Additional freelancers ──
        {"email": "freelancer2@example.com", "name": "Sarah Jenkins",         "role": "freelancer",   "customer_id": "CUST-00041"},
        {"email": "freelancer3@example.com", "name": "David Chen",            "role": "freelancer",   "customer_id": "CUST-00005"},
        # ── Additional merchants ──
        {"email": "merchant2@example.com",   "name": "TechBazaar",            "role": "merchant",     "customer_id": "CUST-00003"},
        {"email": "merchant3@example.com",   "name": "MegaShop",              "role": "merchant",     "customer_id": "CUST-00004"},
        # ── Additional admin/risk ──
        {"email": "risk@example.com",        "name": "Risk Officer 2",        "role": "admin",        "customer_id": None},
    ]

    for u in demo_users:
        existing = session.execute(
            select(User).where(User.email == u["email"])
        ).scalar_one_or_none()
        if not existing:
            user = User(
                email=u["email"],
                name=u["name"],
                role=u["role"],
                password_hash=hash_pw("ProofPay@2026"),
                is_active=True,
                customer_id=u.get("customer_id"),
            )
            session.add(user)
        else:
            # Always keep customer_id in sync (idempotent update)
            existing.customer_id = u.get("customer_id")
    session.commit()
    print(f"Users seeded/updated ({len(demo_users)} records).")


def seed_customers(session: Session) -> None:
    cust_file = DATA_DIR / "customers.json"
    if not cust_file.exists():
        return
    with open(cust_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        cid = item.get("customer_id")
        existing = session.execute(
            select(Customer).where(Customer.customer_id == cid)
        ).scalar_one_or_none()
        if not existing:
            cust = Customer(
                customer_id=cid,
                email=item.get("email", ""),
                language=item.get("language", "en"),
                timezone=item.get("timezone", "UTC"),
                opted_out=item.get("opted_out", False),
                history=item.get("history", []),
            )
            session.add(cust)
    session.commit()
    print(f"Customers seeded ({len(data)} records).")


def seed_invoices(session: Session) -> None:
    inv_file = DATA_DIR / "invoices.json"
    if not inv_file.exists():
        return
    with open(inv_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        iid = item.get("invoice_id")
        existing = session.execute(
            select(Invoice).where(Invoice.invoice_id == iid)
        ).scalar_one_or_none()
        if not existing:
            issued = None
            if item.get("issued_at"):
                try:
                    issued = datetime.fromisoformat(item["issued_at"])
                except Exception:
                    pass
            due = None
            if item.get("due_at"):
                try:
                    due = datetime.fromisoformat(item["due_at"])
                except Exception:
                    pass

            # Random status variation for realistic display
            amt = float(item.get("amount_usd", 0.0))
            status = "paid" if amt < 400 else ("overdue" if amt > 700 else "pending")

            inv = Invoice(
                invoice_id=iid,
                customer_id=item.get("customer_id", ""),
                amount_usd=amt,
                currency=item.get("currency", "USD"),
                issued_at=issued,
                due_at=due,
                status=status,
            )
            session.add(inv)
    session.commit()
    print(f"Invoices seeded ({len(data)} records).")


def seed_subscriptions(session: Session) -> None:
    sub_file = DATA_DIR / "subscriptions.json"
    if not sub_file.exists():
        return
    with open(sub_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        sid = item.get("sub_id")
        existing = session.execute(
            select(Subscription).where(Subscription.sub_id == sid)
        ).scalar_one_or_none()
        if not existing:
            failed_at = None
            if item.get("failed_at"):
                try:
                    failed_at = datetime.fromisoformat(item["failed_at"])
                except Exception:
                    pass
            sub = Subscription(
                sub_id=sid,
                customer_id=item.get("customer_id", ""),
                failure_code=item.get("failure_code", "insufficient_funds"),
                amount_usd=float(item.get("amount_usd", 0.0)),
                currency=item.get("currency", "USD"),
                failed_at=failed_at,
                retry_count=int(item.get("retry_count", 1)),
                status="failed",
            )
            session.add(sub)
    session.commit()
    print(f"Subscriptions seeded ({len(data)} records).")


def seed_paypal_txns(session: Session) -> None:
    txn_file = DATA_DIR / "paypal_txns.json"
    if not txn_file.exists():
        return
    with open(txn_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        tid = item.get("txn_id")
        existing = session.execute(
            select(PayPalTransaction).where(PayPalTransaction.txn_id == tid)
        ).scalar_one_or_none()
        if not existing:
            ts = None
            if item.get("timestamp"):
                try:
                    ts = datetime.fromisoformat(item["timestamp"])
                except Exception:
                    pass
            tx = PayPalTransaction(
                txn_id=tid,
                customer_id=item.get("customer_id", ""),
                amount=float(item.get("amount", 0.0)),
                currency=item.get("currency", "USD"),
                status=item.get("status", "completed"),
                timestamp=ts,
                reference=item.get("reference", ""),
            )
            session.add(tx)
    session.commit()
    print(f"PayPal txns seeded ({len(data)} records).")


def seed_merchant_sales(session: Session) -> None:
    csv_file = DATA_DIR / "merchant_sales.csv"
    if not csv_file.exists():
        return

    count = 0
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("sale_id")
            existing = session.execute(
                select(MerchantSale).where(MerchantSale.sale_id == sid)
            ).scalar_one_or_none()
            if not existing:
                sale = MerchantSale(
                    sale_id=sid,
                    customer_id=row.get("customer_id", ""),
                    amount_usd=float(row.get("amount_usd", 0.0)),
                    category=row.get("category", "eCommerce"),
                    date=row.get("date"),
                    status=row.get("status", "paid"),
                )
                session.add(sale)
                count += 1
    session.commit()
    print(f"Merchant sales seeded ({count} records).")


def seed_bank_statements(session: Session) -> None:
    csv_file = DATA_DIR / "bank_statement.csv"
    if not csv_file.exists():
        return

    count = 0
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eid = row.get("entry_id")
            existing = session.execute(
                select(ReconRecord).where(ReconRecord.external_id == eid)
            ).scalar_one_or_none()
            if not existing:
                vdate = None
                if row.get("value_date"):
                    try:
                        vdate = datetime.strptime(row["value_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except Exception:
                        pass
                rec = ReconRecord(
                    source="bank",
                    external_id=eid,
                    amount=float(row.get("amount", 0.0)),
                    currency=row.get("currency", "USD"),
                    date=vdate,
                    customer_ref=f"{row.get('sender_id', '')} - {row.get('description', '')}",
                )
                session.add(rec)
                count += 1
    session.commit()
    print(f"Bank statement seeded into recon_records ({count} records).")


def seed_escrow_projects(session: Session) -> None:
    escrow_file = DATA_DIR / "escrow.json"
    if not escrow_file.exists():
        return
    with open(escrow_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Explicit assignment: projects 0-2 assigned to named users, rest keep file data.
    # This ensures each demo user has at least one visible project.
    USER_PROJECT_MAP = {
        "ESCROW-000": {"client_id": "CUST-00010", "freelancer_id": "CUST-00081"},  # client@ / freelancer@
        "ESCROW-001": {"client_id": "CUST-00068", "freelancer_id": "CUST-00041"},  # client2@ / freelancer2@
        "ESCROW-002": {"client_id": "CUST-00089", "freelancer_id": "CUST-00005"},  # client3@ / freelancer3@
        "ESCROW-003": {"client_id": "CUST-00010", "freelancer_id": "CUST-00005"},  # client@ / freelancer3@
        "ESCROW-004": {"client_id": "CUST-00068", "freelancer_id": "CUST-00081"},  # client2@ / freelancer@
    }

    for item in data:
        pid = item.get("project_id")
        existing = session.execute(
            select(Project).where(Project.id == pid)
        ).scalar_one_or_none()

        # Apply user mapping override or keep file data
        override = USER_PROJECT_MAP.get(pid, {})
        client_id = override.get("client_id", item.get("buyer_id", "CUST-00010"))
        freelancer_id = override.get("freelancer_id", item.get("seller_id", "CUST-00081"))

        if existing:
            # Idempotent: keep client/freelancer IDs in sync for user-mapped projects
            if pid in USER_PROJECT_MAP:
                existing.client_id = client_id
                existing.freelancer_id = freelancer_id
            continue

        amount = float(item.get("amount_usd", 1000.0))
        is_disputed = item.get("disputed", False)
        state = "DISPUTED" if is_disputed else ("FUNDED" if amount > 2000 else "COMPLETED")

        proj = Project(
            id=pid,
            state=state,
            job_description=f"Freelance Engagement: {item.get('milestone', 'Development').title()} for {client_id}",
            total_amount=amount,
            currency=item.get("currency", "USD"),
            client_id=client_id,
            freelancer_id=freelancer_id,
            client_approved=True,
            freelancer_approved=True,
            plan_hash="mock-plan-hash-" + pid,
            paypal_order_id=f"PAYPAL-ORDER-{pid}",
            paypal_capture_id=f"PAYPAL-CAP-{pid}",
        )
        session.add(proj)
        session.flush()

        # Also create 2 milestones per project
        m_state = "DISPUTED" if is_disputed else (state if state in ("FUNDED", "COMPLETED") else "RELEASED")
        m1 = Milestone(
            id=f"{pid}-M1",
            project_id=pid,
            state=m_state,
            title=f"{item.get('milestone', 'Phase 1').title()} Deliverable",
            amount=round(amount * 0.6, 2),
            currency=item.get("currency", "USD"),
            sequence=1,
            criteria=[
                {"id": "crit-1", "type": "github_pr", "weight": 0.5, "must_pass": True},
                {"id": "crit-2", "type": "pdf_report", "weight": 0.5, "must_pass": False},
            ],
        )
        session.add(m1)

        m2 = Milestone(
            id=f"{pid}-M2",
            project_id=pid,
            state="DRAFT" if state == "FUNDED" else m_state,
            title="Final QA & Handover",
            amount=round(amount * 0.4, 2),
            currency=item.get("currency", "USD"),
            sequence=2,
            criteria=[
                {"id": "crit-3", "type": "client_approval", "weight": 1.0, "must_pass": True},
            ],
        )
        session.add(m2)

        # Create ledger entry
        led = LedgerEntry(
            type="FUNDING",
            subject_id=pid,
            amount=amount,
            currency=item.get("currency", "USD"),
            paypal_id=f"PAYPAL-CAP-{pid}",
            note=f"Escrow project funded by {client_id}",
        )
        session.add(led)
        session.commit()

    session.commit()
    print(f"Escrow projects and milestones seeded ({len(data)} projects).")


def seed_cases(session: Session) -> None:
    sub_file = DATA_DIR / "subscriptions.json"
    if not sub_file.exists():
        return
    with open(sub_file, "r", encoding="utf-8") as f:
        subs = json.load(f)

    # Seed 25 cases from subscriptions
    states = ["OPEN", "RECOVERED", "OPEN", "CONTACTED", "RECOVERED", "PAID_ELSEWHERE", "ESCALATED"]
    channels = ["email", "sms", "whatsapp", "portal"]
    count = 0
    for idx, sub in enumerate(subs[:35]):
        cid = sub.get("customer_id")
        sub_id = sub.get("sub_id")
        existing = session.execute(
            select(Case).where(Case.trigger_event_id == f"TRG-{sub_id}")
        ).scalar_one_or_none()
        if not existing:
            st = states[idx % len(states)]
            amt = float(sub.get("amount_usd", 120.0))
            score = round(0.5 + (amt / 500.0) * 0.4, 2)
            c = Case(
                customer_id=cid,
                type="failed_payment",
                state=st,
                amount_usd=amt,
                currency=sub.get("currency", "USD"),
                payload={
                    "sub_id": sub_id,
                    "failure_code": sub.get("failure_code", "insufficient_funds"),
                    "retry_count": sub.get("retry_count", 1),
                },
                contact_count=1 if st != "OPEN" else 0,
                priority_score=score,
                trigger_event_id=f"TRG-{sub_id}",
                diagnosis={
                    "risk_level": "medium" if amt < 200 else "high",
                    "recommended_channel": channels[idx % len(channels)],
                    "optimal_time": "14:00 UTC",
                },
                history=[
                    {
                        "from_state": "NEW",
                        "to_state": "OPEN",
                        "actor": "system",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )
            session.add(c)
            count += 1
    session.commit()
    print(f"Cases seeded ({count} records).")


def run():
    print("Starting database seeding into Postgres...")
    with Session(sync_engine) as session:
        seed_users(session)
        seed_customers(session)
        seed_invoices(session)
        seed_subscriptions(session)
        seed_paypal_txns(session)
        seed_merchant_sales(session)
        seed_bank_statements(session)
        seed_escrow_projects(session)
        seed_cases(session)
    print("All seeding completed successfully!")


if __name__ == "__main__":
    run()
