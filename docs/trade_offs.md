# Design Decisions & Trade-offs (RFC) - User Payout Management System

This document provides a comprehensive engineering design review detailing the architectural choices, alternative designs considered, and operational tradeoffs for the User Payout Management System.

---

## 1. Database Architecture: PostgreSQL vs. MongoDB
- **Chosen**: PostgreSQL (Relational)
- **Alternatives Considered**: MongoDB (Document Store)
- **Why Alternatives Were Rejected**: 
  Financial ledgers require strict ACID guarantees and complex transactional relations. MongoDB document structures can handle high-throughput logging but lack support for standard relational constraints (such as foreign key validation and check constraints). Relational databases prevent orphan records (e.g., ledger entries pointing to non-existent users) at the database engine level.
- **Trade-offs**:
  * *Pros*: Strong ACID guarantees, strict schemas, foreign keys, transaction isolation levels.
  * *Cons*: Schema changes require migration scripts (Alembic), and scaling horizontally is more complex than with document databases.
  * *Scalability & Performance*: PostgreSQL handles millions of transactions efficiently when using index strategies. Read replication can offset query loads.

---

## 2. Double-Entry Ledger and Separate Balance Cache
- **Chosen**: Double-Entry Ledger (`ledger_transactions`) as the **Single Source of Truth** with a cached `balances` table projection.
- **Why Alternatives Were Rejected**:
  Relying solely on a `balances` column makes auditing difficult, as it is impossible to reconstruct balance changes in the event of database corruption. Conversely, relying only on ledger queries (`SUM(credit) - SUM(debit)`) is too resource-intensive, requiring full table scans on every balance check and API call.
- **Trade-offs**:
  * *Pros*: Clear audit trails, easy balance verification, fast API reads.
  * *Cons*: Requires maintaining synchronization. Every balance modification must write two entries to the ledger and update the balance cache within the same transaction.
  * *System Integrity*: The ledger is the source of truth. If the cache drifts, it can be recalculated by summing the double-entry transaction rows.

### Double-Entry Flow Example:
- **Advance Payout**:
  - Debit: `RESERVE_ADVANCE` account (reducing corporate advance reserve).
  - Credit: `WITHDRAWABLE` user account (increasing user balance).
- **Approved Sale**:
  - Debit: `RESERVE_SYSTEM` account (representing brand earnings liability).
  - Credit: `WITHDRAWABLE` user account (increasing user balance).

---

## 3. Concurrency Lock: Pessimistic locking vs. Optimistic locking
- **Chosen**: Pessimistic Locking (`SELECT FOR UPDATE`) on the `balances` table; Optimistic Locking (`version` column) on the `sales` and `withdrawal_requests` tables.
- **Why Alternatives Were Rejected**:
  Using optimistic locking on the `balances` table during high concurrent withdrawal attempts would cause frequent transaction failures, forcing clients to retry repeatedly. Pessimistic locking blocks concurrent threads, queuing them sequentially.
- **Trade-offs**:
  * *Pros*: Avoids race conditions and double-spending under high concurrency.
  * *Cons*: Pessimistic locks hold database connection threads longer, which can increase latency if transactions are slow.
  * *Mitigation*: We keep transaction blocks as brief as possible, containing only DB writes and zero external network calls.

---

## 4. Architecture Pattern: Clean DDD vs. Event Sourcing vs. CQRS
- **Chosen**: Domain-Driven Design (DDD) with clean architecture layers.
- **Why Alternatives Were Rejected**:
  * *Event Sourcing*: Adds significant architectural complexity. Replaying events to reconstruct states makes simple CRUD operations more difficult to implement and debug.
  * *CQRS*: Separating read and write databases is unnecessary for a system of this scale and introduces data sync lag.
  * *Microservices*: Introducing microservices early on leads to operational overhead (network latency, distributed transaction tracing). A modular monolith with clear domain boundaries is easier to manage.
- **Trade-offs**:
  * *Pros*: Highly maintainable, decoupled components, testable logic.
  * *Cons*: Requires boilerplate classes (DTOs, Mappers, Repositories).

---

## 5. Technology Stack Choices

### FastAPI vs. Django or Flask
- **Chosen**: FastAPI.
- **Why**: FastAPI provides native async support, automated OpenAPI documentation generation, and fast performance. Django is feature-rich but heavy, and Flask lacks modern async structures out-of-the-box.

### SQLAlchemy vs. Raw SQL or TortoiseORM
- **Chosen**: SQLAlchemy (v2.0).
- **Why**: SQLAlchemy is a stable, feature-rich ORM in Python. It supports advanced transaction isolation, clean relation mapping, and pessimistic locking.

### Decimal vs. Float
- **Chosen**: `Decimal` type.
- **Why**: Binary floating-point math (`float`) cannot represent base-10 fractions accurately (e.g., `0.1 + 0.2` equals `0.30000000000000004`). For financial systems, this rounding error is unacceptable. The `Decimal` value object guarantees mathematical accuracy.

### Redis vs. DB-only Idempotency & Rate Limiting
- **Chosen**: Redis for caching/rate-limiting, falling back to database tables for idempotency storage.
- **Why**: Redis provides fast read/write speeds, making it ideal for checking request signatures and rate-limits without increasing database load.

### FastAPI BackgroundTasks vs. Celery
- **Chosen**: FastAPI `BackgroundTasks` for this implementation, with a recommendation to use Celery in production.
- **Why**: `BackgroundTasks` runs inside the same process space, making it easy to deploy and test. For production, Celery is preferred because it decouples worker processes from the API, supporting durable retries and horizontal scaling.

---

## 6. API Design: REST vs. GraphQL
- **Chosen**: REST APIs.
- **Why**: REST provides a straightforward structure for transaction operations, and supports native HTTP status codes, caching, and simple client integrations. GraphQL adds parsing complexity and makes implementing standard rate-limiting more difficult.

---

## 7. Operational Design Decisions

### Soft Delete vs. Hard Delete
- **Chosen**: Soft Delete (`deleted_at` column) on core entities.
- **Why**: Deleting records directly in financial databases ruins audit trails. Soft-deletes keep records in the database while filtering them out of standard queries.

### Synchronous Reconciliation vs. Asynchronous Job Queue
- **Chosen**: Asynchronous bulk reconciliation with a status tracker.
- **Why**: Processing thousands of sale updates synchronously in a single request can lead to timeout errors. Using background jobs ensures the admin API returns quickly while updates process reliably in the background.
