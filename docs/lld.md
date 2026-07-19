# Low-Level Design (LLD) - User Payout Management System

This document outlines the detailed system architecture, system components, sequence flows, state machines, and class structures for the User Payout Management System.

---

## 1. System Overview & Architecture

The system is designed as a production-grade, double-entry financial ledger system using **Domain-Driven Design (DDD)** and **Clean Architecture**. The layout ensures clean separation of concerns:

- **API Controllers (Interface Adapter)**: Handle HTTP requests, manage routing, run authentication middlewares, and process inputs/outputs via DTO schemas.
- **Application Services (Use Case)**: Coordinate the execution of business processes (e.g., triggering advance payouts, reconciling batches, requesting withdrawals).
- **Domain Layer (Entities & Value Objects)**: The core system containing pure business logic (e.g., `Money` arithmetic, state transitions) isolated from frameworks.
- **Repository Layer (Interface/Infrastructure)**: Handles data mapping between DB entities and domain models.
- **Infrastructure (Database / Caching / Queue)**: PostgreSQL for storage, Redis for rate-limiting & idempotency, and background tasks for scheduler processes.

### Component Diagram

```mermaid
graph TD
    UserClient[Web App / Mobile Client] -->|HTTP / JSON| API[FastAPI Web Server]
    API -->|Authenticate & RBAC| Middleware[JWT & RBAC Middleware]
    Middleware -->|Router| Controllers[API Controllers]
    Controllers -->|DTO validation| AppServices[Application Services]
    AppServices -->|Business Rules| Domain[Domain Entities & Value Objects]
    AppServices -->|Data Queries| Repositories[Repositories]
    Repositories -->|SQLAlchemy ORM| DB[(PostgreSQL Database)]
    AppServices -->|Idempotency / Lock / Rate Limit| Redis[(Redis Cache)]
    AppServices -->|Async Tasks| BackgroundTasks[FastAPI BackgroundTasks Scheduler]
    BackgroundTasks -->|Processes Job| AppServices
```

---

## 2. Functional & Non-Functional Requirements

### Functional Requirements
1. **Sale Lifecycle**: Register sales as `Pending`. Calculate earnings and make them eligible for advance payout.
2. **Advance Payout (10%)**: Calculate and distribute exactly 10% of earnings for eligible sales. Prevent double advance payouts.
3. **Admin Reconciliation**: Enable admins to bulk reconcile pending sales into `Approved` or `Rejected` states.
4. **Final Payout Calculation**:
   - **Case 1 (Approved)**: User receives remaining balance: `Earnings - Advance Paid`.
   - **Case 2 (Rejected)**: Adjustment of `-Advance Paid` is debited from user balance.
5. **Withdrawals**: Restrict users to one withdrawal per 24 hours. Ensure ACID locks.
6. **Failed Withdrawal Recovery**: Auto-restore the withdrawn amount to the user's balance and clear the 24h limit cooldown for that withdrawal.
7. **Double-Entry Ledger**: Every balance transition writes exactly one Debit and one Credit entry to `ledger_transactions`.

### Non-Functional Requirements
1. **Financial Precision**: No floating-point math. Enforce Python's `Decimal` type with scale 4 in database.
2. **Idempotency**: All writes must use an `X-Idempotency-Key` header with cached response bodies.
3. **Concurrency Control**: Pessimistic locks (`SELECT FOR UPDATE`) on the `balances` table to prevent race conditions during updates.
4. **Auditability**: Track all mutations, admin reconciliations, and background jobs with version columns and timestamps.

---

## 3. Database Transaction & Data Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant DB as PostgreSQL (Session)
    participant BalanceRepo as Balance Repository
    participant SaleRepo as Sale Repository
    participant LedgerRepo as Ledger Repository
    participant AuditRepo as Audit Repository

    Admin->>ReconciliationService: Reconcile Sales [ID: 1, 2]
    ReconciliationService->>DB: Begin Transaction (ACID)
    ReconciliationService->>BalanceRepo: SELECT FOR UPDATE user_balance WHERE user_id = X
    DB-->>BalanceRepo: Return Locked Balance
    ReconciliationService->>SaleRepo: Update Sale status and version
    ReconciliationService->>LedgerRepo: Insert Balanced Double-Entry Rows (Debit + Credit)
    ReconciliationService->>BalanceRepo: Increment / Decrement withdrawable_balance cache
    ReconciliationService->>AuditRepo: Log Admin Reconciliation action
    ReconciliationService->>DB: Commit Transaction (Releases Locks)
    DB-->>ReconciliationService: Success Confirmation
    ReconciliationService-->>Admin: Reconciliation Job Completed
```

---

## 4. State Machines

### Sale State Transition
```mermaid
stateDiagram-v2
    [*] --> Pending : Sale Created (Advance status: Pending)
    Pending --> Pending : Run Advance Job -> Advance status: Paid (Earnings 10%)
    Pending --> Approved : Admin Reconciles (Approved) -> Add (Earnings - Advance) to Balance
    Pending --> Rejected : Admin Reconciles (Rejected) -> Adjust (-Advance) from Balance
    Approved --> [*]
    Rejected --> [*]
```

### Withdrawal Request State Transition
```mermaid
stateDiagram-v2
    [*] --> Pending : User Initiated (Locked Balance, Checks 24h cooldown)
    Pending --> Processing : Worker Picks Up / Payment Gateway Initiated
    Processing --> Completed : Gateway Success Webhook (Funds Sent)
    Processing --> Failed : Gateway Failure Webhook -> Recover Balance, Bypass 24h cooldown
    Processing --> Cancelled : User / Admin Aborts -> Recover Balance, Bypass 24h cooldown
    Completed --> [*]
    Failed --> [*]
    Cancelled --> [*]
```

---

## 5. Background Job Workflows

```mermaid
graph TD
    cron([Periodic Scheduler]) -->|Trigger Advance Payout| JobA[AdvancePayoutJob]
    cron -->|Trigger Recovery retry| JobB[RetryFailedWithdrawalJob]
    cron -->|Trigger Cleanups| JobC[CleanupIdempotencyJob]

    JobA -->|Scan Pending Sales| DB_Sales[(DB: sales WHERE status='pending' AND advance_status='pending')]
    DB_Sales -->|For each sale| AP[Process 10% Advance Payout]
    AP -->|Lock User Balance| Lock[Pessimistic Lock user_balance]
    Lock -->|Write 2 Ledger Entries| AP_Ledger[Debit Reserve / Credit User Balance]
    AP_Ledger -->|Update balance cache| DB_Balance[Update withdrawable_balance]
    DB_Balance -->|Update sale advance status| AP_Done[Set advance_status = 'paid']
```

---

## 6. Sequence Diagrams

### 1. Withdrawal Flow (With Cooldown Check & Locks)
```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Router
    participant WS as Withdrawal Service
    participant BR as Balance Repository
    participant LR as Ledger Service
    participant DB as DB Transaction Context

    User->>API: POST /withdrawals {amount, currency}
    API->>API: Validate Idempotency & JWT
    API->>WS: Request Withdrawal(user_id, amount)
    WS->>DB: Start Transaction
    WS->>WS: Check last successful withdrawal in 24 hours
    alt Cooldown Violator
        WS-->>API: Throw CooldownActiveException
        API-->>User: HTTP 400 (Only one withdrawal allowed every 24 hours)
    end
    WS->>BR: SELECT FOR UPDATE user_balance
    BR-->>WS: Locked Balance
    alt Insufficient Balance
        WS-->>API: Throw InsufficientFundsException
        API-->>User: HTTP 400 (Insufficient funds)
    end
    WS->>LR: Write Double Entry (Debit: User Balance, Credit: Pending Withdrawal Reserve)
    WS->>BR: Deduct cash from user_balance row
    WS->>DB: Commit & Release Locks
    DB-->>WS: Success
    WS-->>API: Return WithdrawalRequest Object (Status: Pending)
    API-->>User: HTTP 201 Created
```

### 2. Failed Payout Recovery Flow
```mermaid
sequenceDiagram
    autonumber
    participant Gateway as Payment Gateway Webhook
    participant API as Webhook Controller
    participant WS as Withdrawal Service
    participant BR as Balance Repository
    participant LR as Ledger Service
    participant DB as DB Transaction Context

    Gateway->>API: POST /webhooks/payouts {event: payout.failed, withdrawal_id}
    API->>API: Verify Signature & Idempotency
    API->>WS: ProcessFailedWithdrawal(withdrawal_id)
    WS->>DB: Start Transaction
    WS->>BR: SELECT FOR UPDATE user_balance
    BR-->>WS: Locked Balance
    WS->>LR: Write Double Entry (Debit: Pending Withdrawal Reserve, Credit: User Balance)
    WS->>BR: Add cash back to user_balance row
    WS->>WS: Mark withdrawal_request status = 'failed'
    WS->>DB: Commit & Release Locks
    DB-->>WS: Success
    WS-->>API: Processed
    API-->>Gateway: HTTP 200 OK
```

---

## 7. Class Interaction Diagram & Domain Layer Structure

```mermaid
classDiagram
    class Money {
        +Decimal amount
        +str currency
        +add(Money other) Money
        +subtract(Money other) Money
        +multiply(Decimal multiplier) Money
        +round() Money
    }

    class Balance {
        +UUID id
        +UUID user_id
        +Money withdrawable_balance
        +int version
    }

    class Sale {
        +UUID id
        +UUID user_id
        +Money amount
        +Money earnings
        +SaleStatus status
        +AdvanceStatus advance_status
        +reconcile(SaleStatus new_status)
    }

    class LedgerTransaction {
        +UUID id
        +UUID transaction_group_id
        +UUID user_id
        +Money amount
        +LedgerTransactionType entry_type
        +str reference_type
        +UUID reference_id
    }

    class ReconciliationService {
        +process_reconciliation(ReconciliationJob job)
    }

    class WithdrawalService {
        +request_withdrawal(UUID user_id, Money amount)
        +fail_withdrawal(UUID withdrawal_id)
    }

    Sale --> Money : uses
    Balance --> Money : uses
    LedgerTransaction --> Money : uses
    ReconciliationService --> Sale : reconciles
    ReconciliationService --> LedgerTransaction : writes
    WithdrawalService --> Balance : modifies
    WithdrawalService --> LedgerTransaction : writes
```

---

## 8. Design Patterns Used

1. **Repository Pattern**: Decouples the domain services from SQLAlchemy ORM operations, allowing for isolated unit testing.
2. **Service Layer Pattern**: Concentrates use cases and transaction controls in services (e.g. `ReconciliationService`) rather than mixing logic inside API endpoints.
3. **Value Object Pattern**: `Money` wraps financial arithmetic, avoiding raw floats or unsafe decimal calculations and standardizing operations across currencies.
4. **Strategy Pattern (Notification)**: Swaps out notification dispatch channels (e.g. Email, SMS, In-App Logs) dynamically depending on settings.
5. **State Pattern (implicit)**: Tracks lifecycle transitions of Sales and Payouts to prevent invalid operations (such as approving an already approved sale).
