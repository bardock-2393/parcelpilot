"""Load ParcelPilot_Assessment_Data.xlsx into SQLite. Idempotent (upsert by primary key)."""
import openpyxl

from app.config import DATA_DIR
from app.db import init_db, session_scope

XLSX_PATH = DATA_DIR / "ParcelPilot_Assessment_Data.xlsx"


def _rows(ws):
    it = ws.iter_rows(values_only=True)
    header = next(it)
    for row in it:
        if row[0] is None:
            continue
        yield dict(zip(header, row))


def seed() -> dict:
    init_db()
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    counts = {}
    with session_scope() as conn:
        for row in _rows(wb["accounts"]):
            conn.execute(
                """INSERT INTO accounts (account_id, account_name, plan, status, csm,
                       contract_file, premium_support, notes)
                   VALUES (:account_id, :account_name, :plan, :status, :csm,
                       :contract_file, :premium_support, :notes)
                   ON CONFLICT(account_id) DO UPDATE SET
                       account_name=excluded.account_name, plan=excluded.plan,
                       status=excluded.status, csm=excluded.csm,
                       contract_file=excluded.contract_file,
                       premium_support=excluded.premium_support, notes=excluded.notes""",
                {**row, "premium_support": int(bool(row.get("premium_support")))},
            )
        counts["accounts"] = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

        for row in _rows(wb["orders"]):
            conn.execute(
                """INSERT INTO orders (order_id, account_id, carrier, status, booked_at,
                       pickup_window_start, pickup_window_end, pickup_actual_at,
                       shipment_fee_inr, carrier_fault, customer_fault,
                       cancellation_requested_at, notes)
                   VALUES (:order_id, :account_id, :carrier, :status, :booked_at,
                       :pickup_window_start, :pickup_window_end, :pickup_actual_at,
                       :shipment_fee_inr, :carrier_fault, :customer_fault,
                       :cancellation_requested_at, :notes)
                   ON CONFLICT(order_id) DO UPDATE SET
                       account_id=excluded.account_id, carrier=excluded.carrier,
                       status=excluded.status, booked_at=excluded.booked_at,
                       pickup_window_start=excluded.pickup_window_start,
                       pickup_window_end=excluded.pickup_window_end,
                       pickup_actual_at=excluded.pickup_actual_at,
                       shipment_fee_inr=excluded.shipment_fee_inr,
                       carrier_fault=excluded.carrier_fault,
                       customer_fault=excluded.customer_fault,
                       cancellation_requested_at=excluded.cancellation_requested_at,
                       notes=excluded.notes""",
                {
                    **row,
                    "carrier_fault": int(bool(row.get("carrier_fault"))),
                    "customer_fault": int(bool(row.get("customer_fault"))),
                },
            )
        counts["orders"] = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        for row in _rows(wb["tickets"]):
            conn.execute(
                """INSERT INTO tickets (ticket_id, account_id, created_at, status, subject,
                       description, channel, assigned_to, last_customer_message_at,
                       historical_resolution)
                   VALUES (:ticket_id, :account_id, :created_at, :status, :subject,
                       :description, :channel, :assigned_to, :last_customer_message_at,
                       :historical_resolution)
                   ON CONFLICT(ticket_id) DO UPDATE SET
                       account_id=excluded.account_id, created_at=excluded.created_at,
                       status=excluded.status, subject=excluded.subject,
                       description=excluded.description, channel=excluded.channel,
                       assigned_to=excluded.assigned_to,
                       last_customer_message_at=excluded.last_customer_message_at,
                       historical_resolution=excluded.historical_resolution""",
                row,
            )
        counts["tickets"] = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    return counts


if __name__ == "__main__":
    print(seed())
