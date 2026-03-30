from alembic import op

revision = "2"
down_revision = "1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_customer_id
        ON orders (customer_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_item_id
        ON orders (item_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger (
            ledger_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL UNIQUE,
            customer_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_ledger_order_id
                FOREIGN KEY (order_id)
                REFERENCES orders(order_id)
        );
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ledger_customer_id
        ON ledger (customer_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_records (
            idempotency_key TEXT PRIMARY KEY,
            request_hash TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            response_body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS idempotency_records;")
    op.execute("DROP INDEX IF EXISTS ix_ledger_customer_id;")
    op.execute("DROP TABLE IF EXISTS ledger;")
    op.execute("DROP INDEX IF EXISTS ix_orders_item_id;")
    op.execute("DROP INDEX IF EXISTS ix_orders_customer_id;")
    op.execute("DROP TABLE IF EXISTS orders;")