# User Payout Management System

A production-grade, double-entry financial ledger backend and Stripe-inspired dashboard built using Domain-Driven Design (DDD), Clean Architecture, and SOLID principles.

This repository implements the low-level design and business logic requirements to manage user payout commissions, bulk administrative reconciliations, 24-hour withdrawal constraints, and failed transaction balance recoveries.

> [!IMPORTANT]
> * **Earning is 10% of sales generated**
> * **Advance payout is 10% of the earnings**

---

## 🎥 Demo Video of the Assignment

Here is a video demonstration of the working system showing the user interface and functionality:

<video src="https://github.com/Shivam-26102003/User_Payout_Management_system/raw/main/docs/Demo_Video.mp4" autoplay loop muted playsinline width="100%"></video>

---

## 🚀 System Architecture

The application is structured as a **Modular Monolith** applying **Clean Architecture** patterns:
`API Controller (FastAPI)` ➔ `Application Service` ➔ `Domain (Entities & Value Objects)` ➔ `Repository` ➔ `Infrastructure (PostgreSQL / Redis)`.

```
[API Controllers]
       │
       ▼
[Application Services]
       │
       ▼
[Domain Model] (Entities, Value Objects (Money, Balance), Domain Services, Enums, Exceptions)
       │
       ▼
[Repository Interfaces]
       │
       ▼
[Infrastructure / DB (SQLAlchemy / Alembic)]
```

### Core Architecture Highlights
- **Single Source of Truth (SSOT)**: The general ledger (`ledger_transactions`) is the absolute source of truth. User balances are calculated projections cached in the `balances` table.
- **Double-Entry Bookkeeping**: Every transaction writes exactly two matching journal entries (Debit and Credit) ensuring mathematical balance across corporate reserve wallets.
- **Pessimistic Concurrency**: Uses database-level locks (`SELECT FOR UPDATE`) on the balances table to completely prevent double-spend or race conditions under high concurrent loads.
- **Idempotency Engine**: Dedicated global `idempotency_keys` table wrapping all write mutations (`POST`/`PATCH`), returning cached response bodies for identical requests.

---

## 📂 Project Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── api/             # API Router, endpoints, and dependency injection
│   │   ├── core/            # Database engine, JWT security, and middlewares
│   │   ├── domain/          # DDD value objects (Money), enums, and exceptions
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── repositories/    # Database Repository Pattern implementations
│   │   ├── services/        # Application services managing transaction boundaries
│   │   ├── tasks/           # Periodic background jobs scheduler
│   │   └── main.py          # FastAPI application entry point
│   ├── tests/               # Pytest suite (Domain, Reconciliation, Withdrawals)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed.py              # Schema creator and initial data generator
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router (Dashboard, Sales, Withdrawals)
│   │   ├── components/      # UI components, layout structures
│   │   └── lib/             # API fetch client and Typescript definitions
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── Dockerfile
├── docs/
│   ├── lld.md               # Complete System low-level design & UML diagrams
│   ├── db_design.md         # ER schemas, indexes, and concurrency locking
│   ├── edge_cases.md        # Deep-dive on 30+ financial & infrastructure edge cases
│   ├── trade_offs.md        # Comprehensive RFC explaining design choices
│   └── api.md               # API contracts and schemas
├── docker-compose.yml       # Local container orchestration
└── README.md
```

---

## 📊 Database Schema

Our database layout uses PostgreSQL with strict relationships, primary/foreign keys, version numbers for optimistic locks, and indexes for dashboard queries.

- **`users`**: Platform user registry with RBAC role markers (`ADMIN`, `USER`, `VIEWER`).
- **`brands`**: Directory of affiliate brand partners.
- **`sales`**: Ingested sale transactions containing `amount`, `earnings` (commission), and state status flags (`PENDING`, `APPROVED`, `REJECTED`).
- **`balances`**: High-performance cached project balance.
- **`ledger_transactions`**: General ledger containing double-entry entries (balanced `debit`/`credit` columns).
- **`withdrawal_requests`**: Log of user cash-outs.
- **`idempotency_keys`**: Shared storage caching API request states.
- **`reconciliation_jobs`**: Logs of admin bulk overrides.

For full schema definitions, index designs, and SQL script examples, review [db_design.md](docs/db_design.md).

---

## 🛠 Running the System Locally

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Using Docker Compose (Recommended)
Launch the entire stack (PostgreSQL, Redis, Backend, Frontend) with a single command:

**First run** (builds images from source):
```bash
docker compose up --build
```

**Subsequent runs** (uses cached images, faster):
```bash
docker compose up
```

**Run in detached/background mode:**
```bash
docker compose up -d --build
```

**Stop all containers:**
```bash
docker compose down
```

**Stop and remove all data volumes (full reset):**
```bash
docker compose down -v
```

On startup, the backend automatically runs the `seed.py` script to create all schema tables and populate them with default credentials:
- **Frontend Dashboard**: `http://localhost:3000`
- **FastAPI API**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

### 2. Default Seed Accounts
Sign in instantly using the pre-loaded quick-login buttons on the login screen or enter manually:
- **Platform Administrator**: `admin@example.com` / `adminpassword`
- **Affiliate Marketer**: `affiliate@example.com` / `userpassword`
- **Auditor**: `viewer@example.com` / `viewerpassword`

### 3. Running Automated Tests
To run the Pytest verification checks (Money rounding, double-entry reconciliations, 24-hour limit cooldowns, failed payout recovery) locally, execute:
```bash
cd backend
python -m pytest -v
```

---

## 🏛 Design Decisions & Trade-Offs (RFC Summary)

A summary of the core design justifications:

1. **Why PostgreSQL over MongoDB?**
   Financial transaction ledgers require strict relational constraints, transactional ACID compliance, and foreign key verification at the database engine level. NoSQL databases lack these relational safeguards, which could lead to orphaned entries.
2. **Why a cached Balance table beside the Ledger?**
   Summing all historical ledger records (`SUM(credit) - SUM(debit)`) for every wallet check or validation is too slow. The `balances` table acts as a fast cached projection of the ledger, which is locked pessimistically during payouts and updated inside transactions.
3. **Why Pessimistic Locking over Optimistic Locking on Balances?**
   Under high concurrent withdrawal spikes, optimistic locking (version comparisons) would frequently fail, causing client requests to fail and require retries. Pessimistic locks (`SELECT FOR UPDATE`) serialize requests cleanly.
4. **Why Money as a Value Object?**
   Using floats for currency math introduces binary precision errors (e.g. `0.1 + 0.2 != 0.3`). The `Money` class wraps Python's `Decimal` type to ensure precision and enforce half-up rounding.

For a full list of all 20+ architectural justifications, see [trade_offs.md](docs/trade_offs.md).

---

## 🚨 Edge Cases Handled

The system handles 30+ complex edge cases, including:
- **Negative Balances**: Supported when adjustments on rejected sales exceed the user's current balance, recovering funds automatically from future earnings.
- **24h Cooldown Reset**: If a withdrawal fails or is rejected, the funds are restored to the user's balance, and the 24-hour limit cooldown is bypassed for that amount.
- **Double Ingestion and Double Payout Prevention**: Restricts actions using unique keys, version constraints, and database savepoint boundaries.

Review the complete checklist and solution write-ups in [edge_cases.md](docs/edge_cases.md).
