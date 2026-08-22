# Slot Machine API Specification

## Overview
The Slot Machine API provides a simple, stateless interface for clients to spin a virtual slot machine, retrieve spin results, and manage user credits.  All endpoints are versioned under `/v1` and expect **Bearer** token authentication (OAuth2 / JWT).  The service is rate‑limited to **30 requests per minute per authenticated user** to mitigate abuse.

## Base URL
```
https://api.example.com/v1
```

## Authentication
All requests must include an `Authorization` header:
```
Authorization: Bearer <access_token>
```
Tokens are short‑lived (e.g. 15 min) and can be refreshed via a standard OAuth2 flow.

## Rate Limiting
* **Limit:** 30 requests/min per user.
* **Response on exceed:** `429 Too Many Requests` with JSON body `{ "error": "Rate limit exceeded. Try again in X seconds." }`.

---

## 1. Spin the Slot Machine
### Endpoint
```
POST /slot-machine/spin
```
### Purpose
Initiates a slot machine spin for the authenticated user.

### Request
| Header | Value | Description |
|--------|-------|-------------|
| `Content-Type` | `application/json` | Required |
| `Authorization` | `Bearer <token>` | Required |

#### Body (JSON)
```json
{
  "bet_amount": 10
}
```
* `bet_amount` – The amount of credits the user wants to wager. Must be an integer > 0.

### Validations
1. `bet_amount` is present and > 0.
2. User has at least `bet_amount` credits.

### Response (200 OK)
```json
{
  "spin_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reels": [
    { "symbol": "CHERRY",   "multiplier": 2 },
    { "symbol": "BAR",      "multiplier": 3 },
    { "symbol": "SEVEN",    "multiplier": 5 }
  ],
  "win_amount": 50,
  "total_credits": 150
}
```
* `spin_id` – UUID of the spin, used to retrieve the result later.
* `reels` – Array of objects, each containing the symbol shown and its multiplier.
* `win_amount` – Credits won (0 if no win).
* `total_credits` – User's credits after the spin.

### Error Responses
| Code | Body | Reason |
|------|------|--------|
| 400 | `{ "error": "Invalid bet amount." }` | Bad request: missing or non‑positive bet.
| 400 | `{ "error": "Insufficient credits." }` | User lacks enough credits.
| 401 | `{ "error": "Unauthorized." }` | Invalid or missing token.
| 429 | `{ "error": "Rate limit exceeded. Try again in X seconds." }` | Too many requests.

---

## 2. Retrieve Spin Result
### Endpoint
```
GET /slot-machine/spin/{spin_id}
```
### Purpose
Returns the full details of a previously executed spin.

### Parameters
| Path | Type | Description |
|------|------|-------------|
| `spin_id` | `UUID` | Identifier returned from the spin endpoint.

### Response (200 OK)
```json
{
  "spin_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "timestamp": "2026-08-22T12:34:56Z",
  "reels": [
    { "symbol": "CHERRY",   "multiplier": 2 },
    { "symbol": "BAR",      "multiplier": 3 },
    { "symbol": "SEVEN",    "multiplier": 5 }
  ],
  "bet_amount": 10,
  "win_amount": 50,
  "total_credits": 150
}
```
### Error Responses
| Code | Body | Reason |
|------|------|--------|
| 404 | `{ "error": "Spin not found." }` | No spin with that ID.
| 401 | `{ "error": "Unauthorized." }` | Invalid or missing token.

---

## 3. Query User Credits
### Endpoint
```
GET /user/credits
```
### Purpose
Returns the current credit balance for the authenticated user.

### Response (200 OK)
```json
{ "credits": 150 }
```
### Error Responses
| Code | Body | Reason |
|------|------|--------|
| 401 | `{ "error": "Unauthorized." }` | Invalid or missing token.

---

## 4. Admin: Add Credits to a User
### Endpoint
```
POST /admin/user/{user_id}/credits
```
### Purpose
Adds credits to a specific user account.  Only users with `admin` scope are authorized.

### Parameters
| Path | Type | Description |
|------|------|-------------|
| `user_id` | `UUID` | The target user's ID.

### Request
| Header | Value | Description |
|--------|-------|-------------|
| `Content-Type` | `application/json` | Required |
| `Authorization` | `Bearer <token>` | Must include `admin` scope.

#### Body (JSON)
```json
{ "amount": 100 }
```
* `amount` – Positive integer to add.

### Response (200 OK)
```json
{ "user_id": "123e4567-e89b-12d3-a456-426614174000", "new_balance": 250 }
```
### Error Responses
| Code | Body | Reason |
|------|------|--------|
| 400 | `{ "error": "Invalid amount." }` | Non‑positive or missing amount.
| 401 | `{ "error": "Unauthorized." }` | Missing or insufficient scope.
| 404 | `{ "error": "User not found." }` | No user with that ID.

---

## Data Model Glossary
| Entity | Fields | Notes |
|--------|--------|-------|
| **User** | `id: UUID`, `username: string`, `credits: int` | Stored in `users` table. |
| **Spin** | `id: UUID`, `user_id: UUID`, `timestamp: datetime`, `bet_amount: int`, `win_amount: int`, `reels: JSON` | `reels` is an array of `{ symbol, multiplier }`. |
| **Reel** | `symbol: string`, `multiplier: int` | Symbols are drawn from a predefined set. |

## Error Handling Conventions
All error responses are JSON and include an `error` key with a human‑readable message.  The HTTP status code reflects the error type.

## Security Notes
* All endpoints require TLS.
* Tokens should be short‑lived and refreshed via a secure flow.
* Admin endpoints are protected by scope checks.
* Rate limiting prevents automated abuse.

---

## Versioning
The API follows semantic versioning via the path.  Future changes should be introduced under `/v2` to avoid breaking existing clients.

---

## Contact
For support or questions, contact the API team at **api-support@example.com**.

---

*Generated by the Backend Team – Full‑Stack Dev Squad-test*