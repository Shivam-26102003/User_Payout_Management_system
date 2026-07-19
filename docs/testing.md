# Quality Assurance & Testing Plan - User Payout Management System

This document outlines the testing strategy, test classifications, coverage requirements, and verification commands.

---

## 1. Quality Assurance Strategy

Our goal is to ensure high reliability, especially for financial transactions and account balances. The testing plan is structured into three layers:

- **Unit Testing**: Tests core domain modules in isolation (e.g. `Money` Value Object rules and state machines) without database connections.
- **Integration Testing**: Validates transactions across API routes, repository operations, and balance modifications.
- **Concurrency & Stress Testing**: Verifies that pessimistic locks (`SELECT FOR UPDATE`) block concurrent requests and prevent double-spend attempts.

---

## 2. Core Test Scenarios

### 1. Money Value Object Safety
- Verify addition, subtraction, and multiplication operations for the `Money` object.
- Ensure trying to add mismatching currencies throws a `CurrencyMismatchException`.
- Verify half-up rounding logic on odd-valued commissions.

### 2. Double-Entry Integrity
- Validate that balance adjustments write exactly two balanced ledger entries (one debit, one credit).
- Assert that the sum of debit adjustments matches the sum of credit adjustments.

### 3. Concurrency Protection
- Simulate multiple users submitting simultaneous withdrawal calls.
- Verify that only the first thread executes successfully, and the remaining requests are blocked and rejected with an HTTP 400 error.

### 4. 24-Hour Cooldown Limit
- Test that a user can withdraw funds, and immediately fails a subsequent attempt.
- Advance the mock database clock to 24 hours later, and verify the user can withdraw successfully again.

### 5. Reconciliation Logic (Case 1 & 2)
- **Approved Sale**: Check that reconciling a ₹100 sale results in a ₹10 advance payout and a ₹90 remaining payout.
- **Rejected Sale**: Check that rejecting a ₹100 sale after a ₹10 advance has been paid results in a ₹10 deduction from the user's balance.

### 6. Webhook and Failed Payout Recovery
- Initiate a withdrawal, lowering the user's balance.
- Submit a mock payment-failure webhook event.
- Verify the withdrawal status transitions to `FAILED`, the funds are restored to the user's balance via a ledger transaction, and the 24-hour limit cooldown is cleared.

### 7. Idempotency Keys
- Call the withdrawal API twice using the same `X-Idempotency-Key` header.
- Verify the second request returns the cached response from the first request, and only one transaction is written to the database.

---

## 3. Running Automated Tests

### Prerequisites
Make sure the testing dependencies are installed:
```bash
pip install -r backend/requirements.txt
```

### Running Tests Locally
To execute the test suite, run the following command from the `backend/` directory:
```bash
pytest -v --cov=app tests/
```

### Running Tests inside Docker Container
To execute the test suite within the Docker environment, run:
```bash
docker-compose exec backend pytest -v
```
