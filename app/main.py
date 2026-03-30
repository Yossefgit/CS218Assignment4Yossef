from collections import deque
import hashlib
import json
from threading import Lock
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Item, Order
from app.schemas import ItemCreate, ItemResponse, OrderCreate, OrderCreateResponse, OrderResponse

app = FastAPI()

RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW_SECONDS = 10
RATE_LIMIT_EXCLUDED_PATHS = {"/", "/health", "/docs", "/openapi.json", "/favicon.ico"}

rate_limit_buckets: dict[str, deque[float]] = {}
rate_limit_lock = Lock()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def _check_rate_limit(request: Request) -> tuple[bool, dict[str, str]]:
    if request.url.path in RATE_LIMIT_EXCLUDED_PATHS:
        return True, {}

    now = time.time()
    client_ip = _get_client_ip(request)

    with rate_limit_lock:
        bucket = rate_limit_buckets.setdefault(client_ip, deque())

        while bucket and now - bucket[0] >= RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT_REQUESTS:
            retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])) + 1)
            return False, {
                "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(retry_after),
            }

        bucket.append(now)
        remaining = RATE_LIMIT_REQUESTS - len(bucket)

        return True, {
            "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
            "X-RateLimit-Remaining": str(remaining),
        }


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid4().hex
    request.state.request_id = request_id
    start = time.time()

    allowed, rate_limit_headers = _check_rate_limit(request)

    if not allowed:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )
    else:
        response = await call_next(request)

    response.headers["X-Request-Id"] = request_id
    response.headers["X-Response-Time-Ms"] = str(int((time.time() - start) * 1000))

    for header_name, header_value in rate_limit_headers.items():
        response.headers[header_name] = header_value

    print(
        json.dumps(
            {
                "event": "request_complete",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": int((time.time() - start) * 1000),
            }
        ),
        flush=True,
    )
    return response


@app.get("/")
def root():
    return {"message": "running"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="database not ready")


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(name=item.name, value=item.value)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/orders", response_model=OrderCreateResponse, status_code=201)
def create_order(
    body: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    fail_after_commit: str | None = Header(default=None, alias="X-Debug-Fail-After-Commit"),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key")

    payload = body.model_dump()
    req_hash = _fingerprint(payload)

    with engine.connect() as conn:
        tx = conn.begin()
        try:
            row = conn.execute(
                text(
                    """
                    SELECT request_hash, status_code, response_body
                    FROM idempotency_records
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {"idempotency_key": idempotency_key},
            ).mappings().first()

            if row:
                if row["request_hash"] != req_hash:
                    tx.rollback()
                    raise HTTPException(status_code=409, detail="Idempotency-Key reuse with different payload")

                stored_status = int(row["status_code"])
                stored_body = json.loads(row["response_body"])
                tx.rollback()
                return Response(
                    content=json.dumps(stored_body),
                    media_type="application/json",
                    status_code=stored_status,
                )

            order_id = uuid4().hex
            ledger_id = uuid4().hex
            now = _utc_now()
            amount_cents = int(payload["quantity"]) * 100
            response_body = {"order_id": order_id, "status": "created"}

            conn.execute(
                text(
                    """
                    INSERT INTO orders(order_id, customer_id, item_id, quantity, created_at)
                    VALUES(:order_id, :customer_id, :item_id, :quantity, :created_at)
                    """
                ),
                {
                    "order_id": order_id,
                    "customer_id": payload["customer_id"],
                    "item_id": payload["item_id"],
                    "quantity": payload["quantity"],
                    "created_at": now,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO ledger(ledger_id, order_id, customer_id, amount_cents, created_at)
                    VALUES(:ledger_id, :order_id, :customer_id, :amount_cents, :created_at)
                    """
                ),
                {
                    "ledger_id": ledger_id,
                    "order_id": order_id,
                    "customer_id": payload["customer_id"],
                    "amount_cents": amount_cents,
                    "created_at": now,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO idempotency_records(idempotency_key, request_hash, status_code, response_body, created_at)
                    VALUES(:idempotency_key, :request_hash, :status_code, :response_body, :created_at)
                    """
                ),
                {
                    "idempotency_key": idempotency_key,
                    "request_hash": req_hash,
                    "status_code": 201,
                    "response_body": json.dumps(response_body),
                    "created_at": now,
                },
            )

            tx.commit()

            if _is_truthy(fail_after_commit):
                raise HTTPException(status_code=500, detail="Simulated post-commit failure")

            return response_body
        except HTTPException:
            raise
        except Exception as e:
            try:
                tx.rollback()
            except Exception:
                pass
            print(
                json.dumps(
                    {
                        "event": "create_order_error",
                        "error": repr(e),
                        "idempotency_key": idempotency_key,
                    }
                ),
                flush=True,
            )
            raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order