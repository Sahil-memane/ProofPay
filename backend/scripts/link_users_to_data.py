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

        # Cases — assign realistic mix of RECOVERED, PAID_ELSEWHERE, and OPEN cases to each user
        session.execute(text("""
            -- client@ (Acme: CUST-00010)
            UPDATE cases SET customer_id = 'CUST-00010' WHERE id IN (
                'ba6a5747-88ff-47dd-a93e-48dacd388034', -- RECOVERED $299.10
                'c047787a-54a4-44af-be1f-bd60b5e8e104', -- PAID_ELSEWHERE $262.98
                '143bf1de-016d-4b2e-ad6a-1ad4979b4571'  -- OPEN $262.20
            );

            -- merchant@ (Sahil: CUST-00002)
            UPDATE cases SET customer_id = 'CUST-00002' WHERE id IN (
                '78bafa3a-4b48-43b6-8e93-6b51ff2647a4', -- RECOVERED $271.34
                '4b3502d5-be05-4b99-bc10-3f859009e02d', -- RECOVERED $198.44
                'ce6d9220-8711-42d6-948b-f073dedf6616'  -- OPEN $150.00
            );

            -- client2@ (Nexus: CUST-00068)
            UPDATE cases SET customer_id = 'CUST-00068' WHERE id IN (
                'aad8b794-e84b-4424-9fe2-810a8e13431e', -- PAID_ELSEWHERE $260.92
                '116e4b31-4564-4e4f-9bcc-19fc711a76d8'  -- OPEN $258.23
            );

            -- freelancer@ (Rahul: CUST-00081)
            UPDATE cases SET customer_id = 'CUST-00081' WHERE id IN (
                'c41e231b-018a-4c85-94b3-eafeb958a5b2', -- RECOVERED $143.81
                'c6bd80c8-cf63-45ac-90a3-309b6137e102'  -- OPEN $238.46
            );

            -- merchant2@ (TechBazaar: CUST-00003)
            UPDATE cases SET customer_id = 'CUST-00003' WHERE id IN (
                '743d5509-c867-44db-bd37-29a946a6dc40', -- RECOVERED $118.69
                '328d1aa4-5238-4369-91f2-f5d03b710c39'  -- OPEN $215.83
            );

            -- merchant3@ (MegaShop: CUST-00004)
            UPDATE cases SET customer_id = 'CUST-00004' WHERE id IN (
                'd77c788b-8dee-4b06-a4af-b04b75ff4f75', -- RECOVERED $77.12
                'c2db9c7c-6e68-43a8-a3b3-9938e6b263db'  -- OPEN $59.29
            );
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

