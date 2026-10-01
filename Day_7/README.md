# Day 7 — Food Delivery Platform (Microservices)

A production-oriented food delivery platform built with Django/DRF, implementing two BFFs, two independent microservices, PostgreSQL, Celery, and event-driven workflows.

---

## Architecture

```
                     Customer App
                          |
                          v
                   Customer BFF  (port 8000)
                   Django + DRF
                          |
             +------------+------------+
             |                         |
             v                         v
      Restaurant Service         Order Service
      Django + PostgreSQL        Django + PostgreSQL
      (restaurant_service_db)    (order_service_db)
             ^                         ^
             |                         |
             +-------- Events ---------+
                     Celery Workers
                     Redis (broker)

                   Restaurant App
                          |
                          v
                   Restaurant BFF  (port 8003)
                   Django + DRF
                          |
             +------------+------------+
             |                         |
             v                         v
      Restaurant Service         Order Service
```

---

## Services

| Service | Port | DB |
|---------|------|----|
| Customer BFF | 8000 | SQLite (sessions only) |
| Restaurant Service | 8001 | `restaurant_service_db` (PostgreSQL) |
| Order Service | 8002 | `order_service_db` (PostgreSQL) |
| Restaurant BFF | 8003 | SQLite (sessions only) |

---

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (running on 127.0.0.1:5432)
- Redis (running on 127.0.0.1:6379)
- Shared venv from Day_6

### Create Databases
```bash
PGPASSWORD=12345678 psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE restaurant_service_db;"
PGPASSWORD=12345678 psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE order_service_db;"
```

### Run Migrations
```bash
source ../Day_6/venv/bin/activate

cd restaurant_service && python manage.py migrate && cd ..
cd order_service && python manage.py migrate && cd ..
```

### Start Services (each in a separate terminal)
```bash
# Activate venv first: source ../Day_6/venv/bin/activate

# Restaurant Service
cd restaurant_service && python manage.py runserver 8001

# Order Service
cd order_service && python manage.py runserver 8002

# Customer BFF
cd customer_bff && python manage.py runserver 8000

# Restaurant BFF
cd restaurant_bff && python manage.py runserver 8003

# Celery workers (one per service)
cd restaurant_service && celery -A config worker -B --loglevel=info
cd order_service && celery -A config worker -B --loglevel=info
```

---

## Customer BFF APIs

```
GET  /api/customer/restaurants/
GET  /api/customer/restaurants/<restaurant_id>/menu/
POST /api/customer/restaurants/<restaurant_id>/orders/
GET  /api/customer/orders/<order_id>/
POST /api/customer/orders/<order_id>/cancel/
```

### Place Order Request
```json
POST /api/customer/restaurants/<restaurant_id>/orders/
Headers: X-Customer-ID: 42
{
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
    "items": [
        {"menu_item_id": "<uuid>", "quantity": 2},
        {"menu_item_id": "<uuid>", "quantity": 1}
    ]
}
```

### Order Detail Response (Aggregated)
```json
GET /api/customer/orders/<order_id>/
{
    "order": {"id": "...", "status": "PREPARING", "total_amount": "680.00", ...},
    "restaurant": {"id": "...", "name": "Spice Kitchen", "status": "OPEN"},
    "items": [...],
    "status": "PREPARING"
}
```

---

## Restaurant BFF APIs

```
POST  /api/restaurant/menu-items/
PATCH /api/restaurant/menu-items/<item_id>/
POST  /api/restaurant/menu-items/<item_id>/availability/
GET   /api/restaurant/orders/
POST  /api/restaurant/orders/<order_id>/accept/
POST  /api/restaurant/orders/<order_id>/reject/
POST  /api/restaurant/orders/<order_id>/preparing/
POST  /api/restaurant/orders/<order_id>/ready/
POST  /api/restaurant/close/
```

All Restaurant BFF endpoints require `X-Restaurant-ID` header.

---

## Service Ownership

### Restaurant Service owns:
- `Restaurant` (status, capacity configuration, `active_order_count`)
- `MenuItem` (price, availability)
- Capacity slot reservation/release
- RestaurantCreated, RestaurantClosed, MenuItemCreated/Updated/AvailabilityChanged events

### Order Service owns:
- `Order` (full lifecycle state machine)
- `OrderItem` (price snapshot — denormalized at order time)
- OrderCreated, OrderAccepted, OrderRejected, OrderCancelled, OrderPreparing, OrderReady events

### How Order Service gets restaurant/menu data without DB access:
The Customer BFF performs a **synchronous REST call** to Restaurant Service's validation endpoint before creating an order. Restaurant Service returns a price snapshot `{id, name, price}` for each item. This snapshot is written into `OrderItem` at creation time. After that, Order Service never needs to read Restaurant Service's database.

---

## Events

All events use the **Transactional Outbox** pattern:
- Business state change + outbox row are committed in the **same atomic transaction**
- The broker is **never called inside `transaction.atomic()`**
- The Celery outbox relay publishes using `claim_batch()` (SELECT FOR UPDATE SKIP LOCKED)
- Consumers use `ProcessedMessage` for at-least-once deduplication

### Event List
| Event | Producer | Consumers |
|-------|----------|-----------|
| RestaurantCreated | Restaurant Service | Order Service (reconciliation) |
| RestaurantClosed | Restaurant Service | Order Service (cancel pending orders) |
| MenuItemAvailabilityChanged | Restaurant Service | — |
| OrderCreated | Order Service | Restaurant Service (reserve slot) |
| OrderAccepted | Order Service | Notification service |
| OrderRejected | Order Service | Notification service |
| OrderCancelled | Order Service | Restaurant Service (release slot) |
| OrderPreparing | Order Service | Customer notification |
| OrderReady | Order Service | Customer notification |

---

## Order State Machine

```
PENDING ──────────────────────► CONFIRMED ──► PREPARING ──► READY ──► COMPLETED
   │                              │
   ├──► REJECTED (restaurant)     └──► CANCELLED (customer, if not PREPARING)
   └──► CANCELLED (customer)
```

**Invalid transitions explicitly prevented:**
- `CANCELLED → *` (any)
- `COMPLETED → *` (any)
- `PREPARING → CANCELLED`
- `REJECTED → CONFIRMED`

---

## Concurrency Strategy

### Capacity slot reservation
- `SELECT FOR UPDATE` on the `Restaurant` row serializes concurrent reservations
- Two workers racing for the final slot: the second sees `active_order_count >= max_active_orders` and raises `CapacityExceeded`
- No Python locks or process-local state — works across multiple Django instances

### Order idempotency (concurrent submission)
- `idempotency_key` has a DB `UNIQUE` constraint
- Concurrent inserts: one wins, others get `IntegrityError` → read the winner's row
- Same key + different body → `IdempotencyConflict` (422)

### Cancel vs Accept race
- Both paths use `SELECT FOR UPDATE` on the same `Order` row
- Whichever gets the lock first wins
- Cancel-first: CANCELLED → accept gets `InvalidStateTransition` (CANCELLED → CONFIRMED forbidden)
- Accept-first: CONFIRMED → cancel succeeds (CONFIRMED → CANCELLED allowed)

### Out-of-order events
- Every event handler checks the current status before applying the transition
- Stale events (e.g., `OrderAccepted` after `CANCELLED`) are silently skipped

---

## Failure Recovery

| Scenario | Strategy |
|----------|----------|
| Same order submitted 10 times concurrently | DB unique constraint + idempotency key |
| Two workers accept when 1 slot remains | SELECT FOR UPDATE serializes, second gets CapacityExceeded |
| Menu item unavailable during order | Synchronous validation rejects before order creation |
| Cancel races with accept | Both paths lock same row; state machine prevents invalid final state |
| Restaurant rejects committed order | PENDING → REJECTED transition + outbox event |
| Restaurant Service down 30 min | BFF returns 503 with Retry-After; stuck orders detected by reconciliation task |
| Order Service down after RS committed | Capacity slot held; reconciliation task detects and releases |
| Worker crashes after publish before mark_published | Event re-published on next relay run; consumer deduplicates |
| Duplicate event delivered 5 times | ProcessedMessage table ensures handler runs exactly once |
| Out-of-order event (accepted after cancelled) | State machine check in handler ignores stale event |
| Celery task executes twice | All tasks idempotent by design |
| DB transaction rolls back | Outbox event never written (atomic transaction) |

---

## Reconciliation (Periodic Celery Tasks)

| Task | Schedule | Action |
|------|----------|--------|
| `publish_outbox_events` | Every 5s | Relay unpublished outbox events |
| `reconcile_capacity` | Every 60s | Detect/correct Restaurant Service capacity drift |
| `retry_stale_outbox` | Every 30s | Reset stale locked_until on crashed-relay events |
| `detect_stuck_orders` | Every 60s | Log orders stuck in PENDING/CONFIRMED beyond threshold |
| `reconcile_closed_restaurant_orders` | Every 60s | Cancel PENDING orders for closed restaurants |

**Auto-repaired cases:** capacity drift, stale outbox events, closed-restaurant pending orders
**Manual review cases:** orders stuck >30min (logged for human decision), cross-service workflow incomplete after prolonged outage

---

## Authentication & Authorization

- `X-Customer-ID` header is set by the Customer BFF after JWT validation; **never trusted from body**
- `X-Restaurant-ID` header is set by the Restaurant BFF after JWT validation; **never trusted from body**
- Services check these headers; they do not implement JWT validation directly
- Role propagation: BFF → header → microservice (stateless, per-request)

---

## Test Results

| Service | Tests | Result |
|---------|-------|--------|
| Restaurant Service | 15 | ✅ All pass |
| Order Service | 21 | ✅ All pass |
| Customer BFF | 9 | ✅ All pass |
| Restaurant BFF | 12 | ✅ All pass |
| **Total** | **57** | ✅ All pass |

---

## Trade-offs & Assumptions

1. **Synchronous capacity check**: Capacity reservation is synchronous (REST call from BFF to Restaurant Service). This is the only distributed action in the order placement workflow. If Restaurant Service is down, order creation fails cleanly (no partial state).

2. **No distributed transaction**: There is no 2PC or saga coordinator. The order creation workflow uses synchronous REST for immediate validation and async events for eventual consistency. If Order Service is down after capacity is reserved, the reconciliation task detects and releases the slot.

3. **Broker stub**: The broker is a logging stub. In production, replace `broker.publish()` with Redis Streams, RabbitMQ, or Kafka.

4. **Authentication stub**: JWT verification is stubbed via request headers. In production, add a middleware that validates the JWT and sets the header.

5. **BFF as aggregation layer**: BFFs hold no business state. They combine responses from microservices and handle partial failures gracefully (degraded restaurant info when Restaurant Service is down).
