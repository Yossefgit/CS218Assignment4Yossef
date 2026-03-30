from alembic import op
import sqlalchemy as sa

revision = "1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_items_id", "items", ["id"], unique=False)
    op.create_index("ix_items_name", "items", ["name"], unique=False)

    op.create_table(
        "orders",
        sa.Column("order_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"], unique=False)
    op.create_index("ix_orders_item_id", "orders", ["item_id"], unique=False)

    op.create_table(
        "ledger",
        sa.Column("ledger_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_ledger_customer_id", "ledger", ["customer_id"], unique=False)

    op.create_table(
        "idempotency_records",
        sa.Column("idempotency_key", sa.String(), primary_key=True, nullable=False),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("idempotency_records")
    op.drop_index("ix_ledger_customer_id", table_name="ledger")
    op.drop_table("ledger")
    op.drop_index("ix_orders_item_id", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_items_name", table_name="items")
    op.drop_index("ix_items_id", table_name="items")
    op.drop_table("items")