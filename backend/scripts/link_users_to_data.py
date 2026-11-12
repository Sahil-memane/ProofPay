"""
Link demo users to entities in PostgreSQL.
Assigns realistic sets of invoices, subscriptions, merchant sales, and cases to
CUST-00002 (merchant@), CUST-00003 (merchant2@), CUST-00004 (merchant3@),
CUST-00010 (client@), and CUST-00068 (client2@).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from backend.app.db.session import sync_engine
from sqlalchemy.orm import Session

def link_data():
    with Session(sync_engine) as session:
        # Invoices
        session.execute(text("""
            UPDATE invoices SET customer_id = 'CUST-00002' WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE customer_id NOT IN ('CUST-00003', 'CUST-00004') LIMIT 4);
            UPDATE invoices SET customer_id = 'CUST-00003' WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE customer_id NOT IN ('CUST-00002', 'CUST-00004') LIMIT 3);
            UPDATE invoices SET customer_id = 'CUST-00004' WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE customer_id NOT IN ('CUST-00002', 'CUST-00003') LIMIT 3);
            UPDATE invoices SET customer_id = 'CUST-00010' WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE customer_id NOT IN ('CUST-00002', 'CUST-00003', 'CUST-00004') LIMIT 2);
            UPDATE invoices SET customer_id = 'CUST-00068' WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE customer_id NOT IN ('CUST-00002', 'CUST-00003', 'CUST-00004', 'CUST-00010') LIMIT 2);
        """))

        # Subscriptions
        session.execute(text("""
            UPDATE subscriptions SET customer_id = 'CUST-00002' WHERE sub_id IN (SELECT sub_id FROM subscriptions WHERE customer_id NOT IN ('CUST-00003', 'CUST-00004') LIMIT 4);
            UPDATE subscriptions SET customer_id = 'CUST-00003' WHERE sub_id IN (SELECT sub_id FROM subscriptions WHERE customer_id NOT IN ('CUST-00002', 'CUST-00004') LIMIT 3);
            UPDATE subscriptions SET customer_id = 'CUST-00004' WHERE sub_id IN (SELECT sub_id FROM subscriptions WHERE customer_id NOT IN ('CUST-00002', 'CUST-00003') LIMIT 3);
        """))

        # Cases
        session.execute(text("""
            UPDATE cases SET customer_id = 'CUST-00002' WHERE id IN (SELECT id FROM cases WHERE customer_id NOT IN ('CUST-00003', 'CUST-00004') LIMIT 3);
            UPDATE cases SET customer_id = 'CUST-00003' WHERE id IN (SELECT id FROM cases WHERE customer_id NOT IN ('CUST-00002', 'CUST-00004') LIMIT 2);
            UPDATE cases SET customer_id = 'CUST-00004' WHERE id IN (SELECT id FROM cases WHERE customer_id NOT IN ('CUST-00002', 'CUST-00003') LIMIT 2);
        """))

        # Merchant Sales
        session.execute(text("""
            UPDATE merchant_sales SET customer_id = 'CUST-00002' WHERE sale_id IN (SELECT sale_id FROM merchant_sales LIMIT 4);
            UPDATE merchant_sales SET customer_id = 'CUST-00003' WHERE sale_id IN (SELECT sale_id FROM merchant_sales WHERE customer_id != 'CUST-00002' LIMIT 3);
            UPDATE merchant_sales SET customer_id = 'CUST-00004' WHERE sale_id IN (SELECT sale_id FROM merchant_sales WHERE customer_id NOT IN ('CUST-00002', 'CUST-00003') LIMIT 3);
        """))

        session.commit()
        print("Data linked to demo users successfully!")

        for cid, label in [
            ('CUST-00002', 'merchant@ (Sahil)'),
            ('CUST-00003', 'merchant2@ (TechBazaar)'),
            ('CUST-00004', 'merchant3@ (MegaShop)'),
            ('CUST-00010', 'client@ (Acme)'),
            ('CUST-00068', 'client2@ (Nexus)'),
        ]:
            invs = session.execute(text('SELECT count(*) FROM invoices WHERE customer_id = :cid'), {'cid': cid}).scalar()
            subs = session.execute(text('SELECT count(*) FROM subscriptions WHERE customer_id = :cid'), {'cid': cid}).scalar()
            sales = session.execute(text('SELECT count(*) FROM merchant_sales WHERE customer_id = :cid'), {'cid': cid}).scalar()
            cases = session.execute(text('SELECT count(*) FROM cases WHERE customer_id = :cid'), {'cid': cid}).scalar()
            print(f"{label} [{cid}]: {invs} invoices, {subs} subscriptions, {sales} sales, {cases} cases")

if __name__ == "__main__":
    link_data()

