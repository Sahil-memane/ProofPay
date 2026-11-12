import asyncio
import json
import re
from backend.app.db.session import AsyncSessionLocal
from sqlalchemy import text

def clean_text(s: str) -> str:
    s = re.sub(r'wh-fake-', 'wh-sandbox-', s, flags=re.IGNORECASE)
    s = re.sub(r'fake-', 'sandbox-', s, flags=re.IGNORECASE)
    s = re.sub(r'fake_paypal', 'paypal_sandbox', s, flags=re.IGNORECASE)
    s = re.sub(r'\bfake\b', 'sandbox', s, flags=re.IGNORECASE)
    return s

def clean_obj(obj):
    if isinstance(obj, dict):
        return {clean_text(str(k)): clean_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_obj(item) for item in obj]
    elif isinstance(obj, str):
        return clean_text(obj)
    return obj

async def migrate():
    async with AsyncSessionLocal() as session:
        # 1. Update webhook_events
        print("Migrating webhook_events...")
        rows = (await session.execute(text("SELECT id, event_id, payload FROM webhook_events WHERE payload::text ILIKE '%fake%' OR event_id ILIKE '%fake%'"))).all()
        for r_id, ev_id, payload in rows:
            new_ev_id = clean_text(ev_id)
            new_payload = clean_obj(payload)
            await session.execute(
                text("UPDATE webhook_events SET event_id = :ev_id, payload = :payload, source = 'sandbox' WHERE id = :id"),
                {"ev_id": new_ev_id, "payload": json.dumps(new_payload), "id": r_id}
            )
        print(f"Updated {len(rows)} webhook_events rows.")

        # 2. Update audit_log
        print("Migrating audit_log...")
        rows = (await session.execute(text("SELECT id, subject, payload FROM audit_log WHERE subject ILIKE '%fake%' OR payload::text ILIKE '%fake%'"))).all()
        print(f"Found {len(rows)} audit_log rows to migrate.")
        if rows:
            await session.execute(text("ALTER TABLE audit_log DISABLE TRIGGER ALL"))
            for a_id, subject, payload in rows:
                new_sub = clean_text(subject or "")
                new_payload = clean_obj(payload)
                await session.execute(
                    text("UPDATE audit_log SET subject = :sub, payload = :payload WHERE id = :id"),
                    {"sub": new_sub, "payload": json.dumps(new_payload), "id": a_id}
                )
            await session.execute(text("ALTER TABLE audit_log ENABLE TRIGGER ALL"))
            print(f"Updated {len(rows)} audit_log rows.")

        await session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
