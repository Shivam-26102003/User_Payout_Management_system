# Database Design - User Payout Management System

This document describes the relational database structure, indexing strategies, concurrency lock configurations, and double-entry ledger database schema.

---

## 1. Entity Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o{ SALES : "generates"
    USERS ||--|| BALANCES : "owns"
    USERS ||--o{ LEDGER_TRANSACTIONS : "audited by"
    USERS ||--o{ WITHDRAWAL_REQUESTS : "requests"
    BRANDS ||--o{ SALES : "tracks"
    SALES ||--o{ ADVANCE_PAYOUTS : "triggers"
    RECONCILIATION_JOBS ||--o{ SALES : "reconciles"

    USERS {
        UUID id PK
        VARCHAR email UK
        VARCHAR password_hash
        VARCHAR name
        VARCHAR role "ADMIN | USER | VIEWER"
        VARCHAR status "ACTIVE | INACTIVE | BLOCKED"
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP deleted_at
    }

    BRANDS {
        UUID id PK
        VARCHAR name UK
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP deleted_at
    }

    SALES {
        UUID id PK
        UUID user_id FK
        UUID brand_id FK
        VARCHAR external_id UK
        DECIMAL amount
        DECIMAL earnings
        VARCHAR status "PENDING | APPROVED | REJECTED"
        VARCHAR advance_status "PENDING | ELIGIBLE | PAID | SKIPPED"
        UUID reconciliation_job_id FK
        INTEGER version
        TIMESTAMP reconciled_at
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP deleted_at
    }

    ADVANCE_PAYOUTS {
        UUID id PK
        UUID sale_id FK, UK
        UUID user_id FK
        DECIMAL amount
        VARCHAR status "INITIATED | COMPLETED | FAILED"
        INTEGER version
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    WITHDRAWAL_REQUESTS {
        UUID id PK
        UUID user_id FK
        DECIMAL amount
        VARCHAR currency
        VARCHAR status "PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED"
        VARCHAR idempotency_key UK
        VARCHAR failure_reason
        INTEGER version
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    LEDGER_TRANSACTIONS {
        UUID id PK
        UUID transaction_group_id INDEX "groups double-entry transactions"
        UUID user_id FK, INDEX
        DECIMAL debit "positive deduction if non-zero"
        DECIMAL credit "positive gain if non-zero"
        VARCHAR balance_type "WITHDRAWABLE"
        VARCHAR transaction_type "SALE_APPROVED | SALE_REJECTED | ADVANCE_PAYOUT | WITHDRAWAL_INITIATED | WITHDRAWAL_FAILED | WITHDRAWAL_COMPLETED"
        VARCHAR reference_type "SALE | ADVANCE_PAYOUT | WITHDRAWAL"
        UUID reference_id INDEX
        TIMESTAMP created_at INDEX
    }

    BALANCES {
        UUID id PK
        UUID user_id FK, UK
        DECIMAL withdrawable_balance
        INTEGER version
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    RECONCILIATION_JOBS {
        UUID id PK
        UUID admin_id FK
        VARCHAR status "RUNNING | COMPLETED | FAILED"
        VARCHAR error_details
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    IDEMPOTENCY_KEYS {
        VARCHAR key PK
        INTEGER response_status
        JSONB response_body
        TIMESTAMP expires_at
        TIMESTAMP created_at
    }
```

---

## 2. Complete SQL Schema (DDL)

The schema utilizes high-precision `DECIMAL(18, 4)` columns for financial figures to avoid decimal representation rounding errors.

```sql
-- Core schemas & tables
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'USER', -- ADMIN, USER, VIEWER
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, BLOCKED
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE brands (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE reconciliation_jobs (
    id UUID PRIMARY KEY,
    admin_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL, -- RUNNING, COMPLETED, FAILED
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE sales (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    brand_id UUID NOT NULL REFERENCES brands(id),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    amount DECIMAL(18, 4) NOT NULL CHECK (amount >= 0),
    earnings DECIMAL(18, 4) NOT NULL CHECK (earnings >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
    advance_status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, ELIGIBLE, PAID, SKIPPED
    reconciliation_job_id UUID REFERENCES reconciliation_jobs(id),
    version INTEGER NOT NULL DEFAULT 1,
    reconciled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE advance_payouts (
    id UUID PRIMARY KEY,
    sale_id UUID UNIQUE NOT NULL REFERENCES sales(id),
    user_id UUID NOT NULL REFERENCES users(id),
    amount DECIMAL(18, 4) NOT NULL CHECK (amount >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'INITIATED', -- INITIATED, COMPLETED, FAILED
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE withdrawal_requests (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    amount DECIMAL(18, 4) NOT NULL CHECK (amount > 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED
    idempotency_key VARCHAR(255) UNIQUE,
    failure_reason TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE ledger_transactions (
    id UUID PRIMARY KEY,
    transaction_group_id UUID NOT NULL,
    user_id UUID REFERENCES users(id), -- NULL if corporate ledger account
    debit DECIMAL(18, 4) NOT NULL DEFAULT 0.0 CHECK (debit >= 0),
    credit DECIMAL(18, 4) NOT NULL DEFAULT 0.0 CHECK (credit >= 0),
    balance_type VARCHAR(50) NOT NULL, -- WITHDRAWABLE, RESERVE_ADVANCE, RESERVE_SYSTEM
    transaction_type VARCHAR(50) NOT NULL, -- SALE_APPROVED, SALE_REJECTED, ADVANCE_PAYOUT, etc.
    reference_type VARCHAR(50) NOT NULL, -- SALE, ADVANCE_PAYOUT, WITHDRAWAL
    reference_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE balances (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    withdrawable_balance DECIMAL(18, 4) NOT NULL DEFAULT 0.0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    response_status INTEGER NOT NULL,
    response_body JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    target_table VARCHAR(100),
    target_id UUID,
    changes JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- RECEIVED, PROCESSED, FAILED
    payload JSONB NOT NULL,
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE system_jobs (
    id UUID PRIMARY KEY,
    job_name VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL, -- IDLE, RUNNING, FAILED
    last_run_at TIMESTAMP WITH TIME ZONE,
    error_log TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE notification_logs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL, -- EMAIL, IN_APP
    status VARCHAR(50) NOT NULL, -- SENT, FAILED
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

## 3. Indexing & Composite Indexing Strategy

To guarantee rapid query performance with millions of data rows, the following indexes are declared:

1. **`sales_status_idx`**: `CREATE INDEX idx_sales_status ON sales (status)`
   - *Why*: The advance payout processor scans for `Pending` sales repeatedly.
2. **`sales_user_status_idx`**: `CREATE INDEX idx_sales_user_status ON sales (user_id, status)`
   - *Why*: Powers user dashboards listing their active pending, approved, or rejected sales.
3. **`withdrawals_user_created_idx`**: `CREATE INDEX idx_withdrawals_user_created ON withdrawal_requests (user_id, created_at DESC)`
   - *Why*: Enforces the 24-hour cool-down period by querying the user's latest withdrawals.
4. **`ledger_user_created_idx`**: `CREATE INDEX idx_ledger_user_created ON ledger_transactions (user_id, created_at DESC)`
   - *Why*: Displays audit statements to users in reverse chronological order.
5. **`ledger_group_idx`**: `CREATE INDEX idx_ledger_group_id ON ledger_transactions (transaction_group_id)`
   - *Why*: Simplifies retrieving both legs (debit and credit entries) of a specific transaction.
6. **`audit_logs_created_idx`**: `CREATE INDEX idx_audit_logs_created ON audit_logs (created_at DESC)`
   - *Why*: Supports admin activity dashboards.
7. **`idempotency_expires_idx`**: `CREATE INDEX idx_idempotency_expires ON idempotency_keys (expires_at)`
   - *Why*: Enables clean-up workers to prune expired idempotency keys efficiently.

---

## 4. Concurrency Locking & Isolation Design

To avoid race conditions such as duplicate withdrawals or simultaneous administrator overrides, we deploy two primary mechanisms:

### 1. Pessimistic Locking (`SELECT FOR UPDATE`)
We use database-level locks on the `balances` table to guarantee serializable updates on financial calculations.
- **Workflow**:
  1. Start a transaction context.
  2. Perform `SELECT withdrawable_balance FROM balances WHERE user_id = :user_id FOR UPDATE`.
  3. Compute calculations using the `Money` value object.
  4. Perform SQL insert for `ledger_transactions` (2 balanced rows).
  5. Update the `balances` cache row with the new amount.
  6. Commit transaction, releasing the lock.
- **Benefits**: Blocks concurrent withdrawal threads and reconciliation overrides on the same user account from executing in parallel, completely avoiding double-spend issues.

### 2. Optimistic Locking (`version` column)
We use optimistic versioning on the `sales` and `withdrawal_requests` tables to handle low-frequency contention.
- **Workflow**:
  1. Retrieve the sale entity including its current `version` (e.g. `version = 1`).
  2. Perform updates with a conditional statement: `UPDATE sales SET status = 'APPROVED', version = 2 WHERE id = :id AND version = 1`.
  3. If the row count modified returns `0`, it indicates that another action has updated the sale. Throw a `ConcurrentModificationException` and roll back.
