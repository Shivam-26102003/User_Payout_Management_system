# Edge Cases & Failure Scenarios - User Payout Management System

This document outlines the detailed breakdown of 33 critical edge cases, assessing their impact and the corresponding engineering solutions designed in the codebase.

---

## 1. Financial & Business Logic Edge Cases

### 1. Duplicate Advance Payout Runs
- **Problem**: The background job to pay the 10% advance runs twice simultaneously or in close succession.
- **Impact**: The user might receive the 10% advance twice, resulting in financial loss.
- **Solution**: We set the sale's `advance_status` to `PAID` using a strict check in the transaction. When the job runs, it selects only sales where `advance_status = 'pending'`. The update uses optimistic locking on the sale's version column.

### 2. Double Reconciliation of a Sale
- **Problem**: Two administrators attempt to reconcile (approve/reject) the same sale at the exact same moment.
- **Impact**: Double crediting of earnings, leading to inaccurate ledger records.
- **Solution**: We enforce optimistic concurrency control on the `sales` table using a `version` column. The second update fails with `ConcurrentModificationException` as the version will have already incremented.

### 3. Advance Payout Triggered After Reconciliation
- **Problem**: A sale is reconciled (e.g., approved/rejected) and later the advance payout job executes.
- **Impact**: The advance payout job might try to pay an advance on a sale that is already reconciled.
- **Solution**: The advance payout job strictly filters for sales where `status = 'PENDING'`. Once reconciled, a sale's status changes to `APPROVED` or `REJECTED`, making it ineligible for advances.

### 4. Sale Approved Without Advance Payout Paid
- **Problem**: A sale is approved before the advance payout background job ever ran for it.
- **Impact**: The user is owed the full 100% of earnings, but the default formula `Earnings - Advance Paid` might calculate incorrectly if it assumes the advance was always paid.
- **Solution**: The reconciliation service queries the actual `advance_payouts` table. If no advance was paid, the advance paid is treated as ₹0, crediting the full 100% of the earnings.

### 5. Sale Rejected Without Advance Payout Paid
- **Problem**: A sale is rejected before the advance payout background job ever ran.
- **Impact**: The adjustment should be ₹0, but if the code blindly adjustments `-10%`, the user's balance is unfairly penalized.
- **Solution**: The reconciliation service checks the `advance_payouts` table. If no advance was paid, the adjustment amount is ₹0.

### 6. Negative Balances After Rejected Sale Adjustment
- **Problem**: A user gets an advance payout, withdraws the funds immediately (withdrawable balance goes to ₹0), and then the administrator rejects the sale.
- **Impact**: The adjustment of `-Advance` will push the user's balance into the negative.
- **Solution**: We permit the user's balance to go negative. The user's withdrawable balance is decremented below zero. Future approved sales will credit the balance, gradually restoring it to positive.

### 7. Zero Earnings Sale
- **Problem**: An affiliate sale is registered with an earning of ₹0.00.
- **Impact**: Calculation of 10% advance payout or division operations might cause zero-value entries or division by zero exceptions.
- **Solution**: The Money Value Object handles zero values cleanly. If earnings are ₹0, the advance payout amount is computed as ₹0, and the status is transitioned directly to `SKIPPED`.

### 8. Very Large Earnings Sale (Precision Overflow)
- **Problem**: A sale is registered with massive earnings (e.g., ₹100,000,000.00).
- **Impact**: Database integer overflow or floating point inaccuracies.
- **Solution**: The database column is defined as `DECIMAL(18, 4)` and Python arithmetic runs strictly on `Decimal`, supporting massive numbers without precision loss.

### 9. Decimal Rounding Discrepancies
- **Problem**: A sale earning is ₹33.33. 10% is ₹3.333, and the remaining 90% is ₹29.997.
- **Impact**: Loss of fractional currency across transactions, preventing ledger entries from matching perfectly.
- **Solution**: The Money Value Object enforces a rounding scale of 4 decimal places using half-up rounding. This ensures that `Advance + Remaining = Total Earning` holds mathematically down to the smallest decimal fraction.

### 10. Currency Mismatch
- **Problem**: A user requests a withdrawal in USD, but their account balance is tracked in INR.
- **Impact**: Mixing currencies in ledger transactions leading to unbalanced corporate books.
- **Solution**: The `Money` Value Object raises a `CurrencyMismatchException` if arithmetic is attempted between different currencies. All payouts and balances are constrained to the system currency (INR).

---

## 2. Concurrency & Race Conditions

### 11. Simultaneous Admin Reconciliation on Same Sale
- **Problem**: Two admins submit approval actions on the same sale at the exact same millisecond.
- **Impact**: Double credits could occur.
- **Solution**: Handled by checking the `version` column of the `sales` table. The transaction that commits first increments the version, causing the second commit to fail.

### 12. Simultaneous Withdrawals by the Same User
- **Problem**: A user invokes the withdrawal endpoint twice concurrently to empty their balance twice.
- **Impact**: Balance goes negative below allowed parameters, escaping the 24-hour limit.
- **Solution**: The withdrawal service starts a transaction and acquires a pessimistic lock (`SELECT FOR UPDATE`) on the user's row in the `balances` table. The second thread waits until the first commits, then reads the updated balance (which is now ₹0) and fails.

### 13. Concurrently Running Advance Payout Job & Reconciliation Job
- **Problem**: The advance payout job picks up a pending sale at the same moment an admin approves it.
- **Impact**: Both jobs calculate balance updates concurrently, leading to race conditions.
- **Solution**: Both services lock the user's balance row (`SELECT FOR UPDATE`) and check the sale's `status` and `version` columns. The reconciliation job commits first, modifying the status. When the advance job resumes, it sees the sale status is no longer `PENDING` and cancels execution.

### 14. Withdrawal Recovery Concurrently with Sale Approval
- **Problem**: A webhook marks a withdrawal as failed (returning money to balance) while a sale approval credits the balance.
- **Impact**: Dirty reads or overwrites.
- **Solution**: Both write-operations lock the `balances` table using pessimistic locks. Balance modifications are sequentially isolated.

### 15. Scheduler Triggers Multiple Background Instances
- **Problem**: The scheduler triggers duplicate job instances on a multi-node cluster.
- **Impact**: Excessive DB connections and high lock contention.
- **Solution**: System jobs are tracked in the `system_jobs` table. A worker must successfully set the job's status to `RUNNING` via atomic update before executing the task.

### 16. User Requests Withdrawal During Advance Payout Credit
- **Problem**: A user attempts to withdraw their balance while an advance payout is actively crediting it.
- **Impact**: Temporary transaction lock contention.
- **Solution**: Pessimistic locks serialize the operations. The withdrawal waits for the advance payout transaction to commit, ensuring the user can safely withdraw the newly added advance.

### 17. Slow Network Leading to Double Submission
- **Problem**: A user clicks the "Withdraw" button twice due to network latency.
- **Impact**: Multiple withdrawal requests created.
- **Solution**: The system requires an `X-Idempotency-Key` header. Duplicate submissions are checked against the `idempotency_keys` table. The server returns the cached response of the first request.

### 18. Webhook Retries for Already Processed Events
- **Problem**: The payment gateway retries a webhook notification because of a network hiccup.
- **Impact**: Reprocessing the event could double-credit the user's account.
- **Solution**: Webhook events are logged in `webhook_events`. The gateway's `event_id` is stored with a unique constraint. Subsequent retries trigger a unique constraint exception, returning a `200 OK` safely.

---

## 3. Infrastructure & Failures

### 19. Redis Cache Goes Down
- **Problem**: The Redis container is unavailable.
- **Impact**: Rate limiting and idempotency caching fail.
- **Solution**: The backend implements a fallback mechanism. Idempotency checks fall back to the PostgreSQL `idempotency_keys` table. Rate limiting logs warnings but allows requests to process under restricted conditions.

### 20. PostgreSQL Connection Fails Mid-Transaction
- **Problem**: The database crashes during a reconciliation job.
- **Impact**: Partial updates could occur.
- **Solution**: All operations are wrapped in SQLAlchemy transactional contexts. A connection failure triggers a database-level rollback, discarding any uncommitted changes.

### 21. Payment Gateway Timeout
- **Problem**: The external API calls times out when initiating a withdrawal.
- **Impact**: Unknown payout state.
- **Solution**: The withdrawal request is set to `PROCESSING`. A background job queries the gateway status periodically, or awaits webhook callbacks to resolve the status to `COMPLETED` or `FAILED`.

### 22. Duplicate Webhook Payload Received
- **Problem**: The gateway sends identical payloads for a transaction.
- **Impact**: Duplicate accounting entries.
- **Solution**: We run a unique index check on the `webhook_events` table using the payload's event ID.

### 23. Network Retry on API Calls
- **Problem**: A client retries a failed HTTP request that actually completed on the server.
- **Impact**: Duplicate actions.
- **Solution**: Clean idempotency lookup filters return the exact response body saved from the first run.

### 24. Server Restarts Mid-Reconciliation
- **Problem**: The FastAPI container is restarted during a bulk reconciliation job.
- **Impact**: The reconciliation job table shows `RUNNING` forever.
- **Solution**: On startup, a system job checks for any reconciliation job marked `RUNNING` and resets its state to `FAILED`. Admin can trigger a retry safely since processed sales were committed inside isolated sub-transactions.

### 25. Task Worker Thread Crashes
- **Problem**: The worker processing advance payouts crashes.
- **Impact**: Unprocessed sales remain pending.
- **Solution**: On the next job run, the system identifies sales that are still pending and processes them.

---

## 4. Security & Integrity

### 26. Unauthorized Reconciliation
- **Problem**: A standard affiliate user calls the reconciliation API.
- **Impact**: Security breach.
- **Solution**: The API route is protected by JWT authentication and RBAC checks, rejecting requests that lack the `ADMIN` role.

### 27. Tampered Request Data
- **Problem**: An attacker attempts to submit modified values (e.g., changing withdrawal user IDs).
- **Impact**: Theft of funds.
- **Solution**: Pydantic schemas enforce type safety and reject unrecognized fields. The user ID is retrieved directly from the validated JWT token rather than trusting payload parameters.

### 28. Replay Attacks
- **Problem**: An attacker intercepts a withdrawal request and replays it.
- **Impact**: Unauthorized funds drain.
- **Solution**: JWT tokens have short lifetimes (e.g., 15 minutes) and are locked to SSL/TLS. Idempotency keys prevent reusing request signatures.

### 29. Reusing Idempotency Key with Altered Parameters
- **Problem**: A client attempts to reuse a key with a different body payload.
- **Impact**: Data corruption or unauthorized operations.
- **Solution**: We hash the request parameters and compare them with the stored idempotency record. If a mismatch is detected, the server returns an HTTP 400 Bad Request error.

### 30. Soft-Deleted Users
- **Problem**: A user is marked as deleted in the database.
- **Impact**: Automated jobs might still process advance payouts or withdrawals for them.
- **Solution**: Database queries filter out soft-deleted users (`deleted_at IS NULL`), preventing them from authenticating or receiving funds.

---

## 5. User & Operations Edge Cases

### 31. Blocked User Actions
- **Problem**: An administrator marks a user as `BLOCKED` due to fraud.
- **Impact**: The user might still try to execute active withdrawals.
- **Solution**: The user's status is validated during authentication and within balance locks. If the status is `BLOCKED`, the transaction aborts.

### 32. Missing User Balance Row
- **Problem**: A user is created, but no row is generated in the `balances` table.
- **Impact**: Queries fail when requesting withdrawals or reconciling sales.
- **Solution**: The user service wraps user creation in a transaction that automatically inserts a corresponding `balances` row with ₹0.00.

### 33. Timezone Clashes and Clock Skew
- **Problem**: Servers and databases run on different timezones, or local times drift.
- **Impact**: The 24-hour withdrawal constraint calculates incorrectly.
- **Solution**: The database and application standardize strictly on UTC timezone-aware timestamps. The database calculates the 24-hour window using `NOW() AT TIME ZONE 'UTC'`.
