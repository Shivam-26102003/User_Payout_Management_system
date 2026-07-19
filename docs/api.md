# API Documentation - User Payout Management System

This document outlines the REST API endpoints, request/response formats, security parameters, and HTTP response codes.

---

## 1. Global Specifications

### Base URL
- Local Development: `http://localhost:8000/api/v1`

### Request Headers
- **`Authorization`**: `Bearer <JWT_TOKEN>` (Required for all routes except `/auth/token`)
- **`X-Idempotency-Key`**: Unique string UUID (Required for mutation endpoints like `POST` and `PATCH`)
- **`Content-Type`**: `application/json`

### Pagination & Sorting (Default Parameters)
- `page`: Integer (default: `1`)
- `limit`: Integer (default: `20`, max: `100`)
- `sort_by`: String (field name, e.g. `created_at`)
- `sort_order`: String (`asc` or `desc`, default: `desc`)

---

## 2. Authentication Endpoint

### Authenticate User (Get Token)
- **Path**: `POST /auth/token`
- **Request Body**:
  ```json
  {
    "email": "admin@example.com",
    "password": "securepassword123"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "role": "ADMIN"
  }
  ```
- **Response (401 Unauthorized)**:
  ```json
  {
    "detail": "Invalid email or password"
  }
  ```

---

## 3. Users Endpoint

### Get List of Users (Admin only)
- **Path**: `GET /users`
- **Response (200 OK)**:
  ```json
  {
    "users": [
      {
        "id": "787e91bd-5060-4960-9e6b-0731f24d2629",
        "email": "user1@example.com",
        "name": "Jane Doe",
        "role": "USER",
        "status": "ACTIVE",
        "created_at": "2026-07-19T02:00:00Z"
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 1 }
  }
  ```

---

## 4. Sales Endpoint

### Create Sale (Mock Ingestion / Admin / System)
- **Path**: `POST /sales`
- **Request Body**:
  ```json
  {
    "user_id": "787e91bd-5060-4960-9e6b-0731f24d2629",
    "brand_name": "brand_1",
    "external_id": "tx_sale_9988",
    "amount": "400.0000"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": "b3b246a0-d12c-47d3-9bc7-d779bb6cdfe4",
    "user_id": "787e91bd-5060-4960-9e6b-0731f24d2629",
    "brand_id": "1a2b3c4d-...",
    "external_id": "tx_sale_9988",
    "amount": "400.0000",
    "earnings": "40.0000",
    "status": "PENDING",
    "advance_status": "PENDING",
    "created_at": "2026-07-19T02:05:00Z"
  }
  ```

### List Sales (Filterable by status, user_id)
- **Path**: `GET /sales`
- **Query Parameters**: `status=PENDING&user_id=787e91bd-5060-4960-9e6b-0731f24d2629`
- **Response (200 OK)**:
  ```json
  {
    "sales": [
      {
        "id": "b3b246a0-d12c-47d3-9bc7-d779bb6cdfe4",
        "user_id": "787e91bd-5060-4960-9e6b-0731f24d2629",
        "brand_name": "brand_1",
        "amount": "400.0000",
        "earnings": "40.0000",
        "status": "PENDING",
        "advance_status": "PENDING",
        "created_at": "2026-07-19T02:05:00Z"
      }
    ]
  }
  ```

---

## 5. Advance Payout Endpoints

### Run Advance Payout Job (Admin only)
- **Path**: `POST /advance-payouts/run`
- **Response (202 Accepted)**:
  ```json
  {
    "message": "Advance payout background job triggered successfully",
    "job_id": "dcf11b7d-6523-455b-b9d9-95e28a528cc2"
  }
  ```

### Get Advance Payouts History
- **Path**: `GET /advance-payouts/history`
- **Response (200 OK)**:
  ```json
  {
    "history": [
      {
        "id": "3c847e11-e408-410a-b31a-6df7d17be6c7",
        "sale_id": "b3b246a0-d12c-47d3-9bc7-d779bb6cdfe4",
        "user_id": "787e91bd-5060-4960-9e6b-0731f24d2629",
        "amount": "4.0000",
        "status": "COMPLETED",
        "created_at": "2026-07-19T02:06:00Z"
      }
    ]
  }
  ```

---

## 6. Admin Reconciliation Endpoints

### Bulk Reconcile Sales (Admin only)
- **Path**: `POST /admin/reconcile`
- **Request Body**:
  ```json
  {
    "sales": [
      {
        "sale_id": "b3b246a0-d12c-47d3-9bc7-d779bb6cdfe4",
        "action": "APPROVED"
      },
      {
        "sale_id": "422e032d-2fe4-473d-82d2-88ad88ff910f",
        "action": "REJECTED"
      }
    ]
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "message": "Reconciliation job submitted",
    "job_id": "f8216c5f-8d96-419b-ab0d-40fe52136e05",
    "reconciled_sales_count": 2
  }
  ```

---

## 7. Withdrawals & Webhooks

### Request Withdrawal
- **Path**: `POST /withdrawals`
- **Request Body**:
  ```json
  {
    "amount": "100.0000",
    "currency": "INR"
  }
  ```
- **Response (210 Created)**:
  ```json
  {
    "id": "522197cd-8efd-4e92-91c6-cf8813fa2503",
    "user_id": "787e91bd-5060-4960-9e6b-0731f24d2629",
    "amount": "100.0000",
    "currency": "INR",
    "status": "PENDING",
    "created_at": "2026-07-19T02:10:00Z"
  }
  ```

### Get Withdrawal Logs
- **Path**: `GET /withdrawals`
- **Response (200 OK)**:
  ```json
  {
    "withdrawals": [
      {
        "id": "522197cd-8efd-4e92-91c6-cf8813fa2503",
        "amount": "100.0000",
        "currency": "INR",
        "status": "PENDING",
        "created_at": "2026-07-19T02:10:00Z"
      }
    ]
  }
  ```

### Mock Payout Status Update (Simulates Webhook Callback)
- **Path**: `PATCH /withdrawals/{id}`
- **Request Body**:
  ```json
  {
    "status": "FAILED",
    "failure_reason": "Gateway error code: INSUFFICIENT_DESTINATION_LIQUIDITY"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "id": "522197cd-8efd-4e92-91c6-cf8813fa2503",
    "status": "FAILED",
    "refund_ledger_transaction_id": "8935c102-ef1d-4573-b3c9-...",
    "withdrawable_balance_refunded": "100.0000"
  }
  ```

---

## 8. Balances & Ledger Endpoints

### Get User Balance Cache
- **Path**: `GET /balances`
- **Response (200 OK)**:
  ```json
  {
    "user_id": "787e91bd-5060-4960-9e6b-0731f24d2629",
    "withdrawable_balance": "68.0000",
    "currency": "INR"
  }
  ```

### Get Ledger History
- **Path**: `GET /ledger`
- **Response (200 OK)**:
  ```json
  {
    "transactions": [
      {
        "id": "8935c102-ef1d-...",
        "transaction_group_id": "bfdcf41c-...",
        "debit": "0.0000",
        "credit": "100.0000",
        "balance_type": "WITHDRAWABLE",
        "transaction_type": "WITHDRAWAL_FAILED",
        "reference_type": "WITHDRAWAL",
        "reference_id": "522197cd-8efd-4e92-91c6-cf8813fa2503",
        "created_at": "2026-07-19T02:11:00Z"
      }
    ]
  }
  ```

---

## 9. System Diagnostics

### Health Status Endpoint
- **Path**: `GET /health`
- **Response (200 OK)**:
  ```json
  {
    "status": "HEALTHY",
    "services": {
      "database": "CONNECTED",
      "redis": "CONNECTED"
    },
    "version": "1.0.0"
  }
  ```

### Prometheus Metrics Endpoint
- **Path**: `GET /metrics`
- **Response (200 OK)**:
  ```text
  # HELP http_requests_total Total number of HTTP requests.
  # TYPE http_requests_total counter
  http_requests_total{method="GET",handler="/health",status="200"} 12
  # HELP wallet_balance_inr Sum of withdrawable balances across users.
  # TYPE wallet_balance_inr gauge
  wallet_balance_inr 15200.50
  ```
