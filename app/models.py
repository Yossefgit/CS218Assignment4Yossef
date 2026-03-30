from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, nullable=False)
    customer_id = Column(String, nullable=False, index=True)
    item_id = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ledger_entry = relationship("Ledger", back_populates="order", uselist=False)


class Ledger(Base):
    __tablename__ = "ledger"

    ledger_id = Column(String, primary_key=True, nullable=False)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, unique=True)
    customer_id = Column(String, nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    order = relationship("Order", back_populates="ledger_entry")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String, primary_key=True, nullable=False)
    request_hash = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())