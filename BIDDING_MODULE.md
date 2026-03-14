# Bidding Module — Documentation

> Real-time, Redis-coordinated problem bidding for DevDuel contests.

---

## Table of Contents

1. [Overview](#overview)
2. [How Bidding Works](#how-bidding-works)
3. [Database Schema](#database-schema)
4. [Redis State](#redis-state)
5. [Module Architecture](#module-architecture)
6. [API Reference](#api-reference)
7. [WebSocket Protocol](#websocket-protocol)
8. [Security & Edge Cases](#security--edge-cases)

---

## Overview

During a **DevDuel contest** (status = `ACTIVE`), problems are sold to teams through a live auction system.

- An **organizer** starts one auction at a time.
- Each team's **Bidder** member places bids using the team's currency budget.
- The **highest bidder wins** the problem and has their currency deducted.
- The winning team receives a `ContestProblemAssignment`, and their **Coder** solves it.
- The next problem's auction then begins.

---

## How Bidding Works

```
Organizer
   │
   ├── POST /bidding/contests/{contest_id}/auctions/start
   │       Creates ProblemAuction (status=ACTIVE)
   │       Seeds Redis: highest_bid = base_price, highest_team = ""
   │
   │   [Clients connect via WebSocket]
   │       ws://.../api/bidding/ws/{contest_id}
   │
   ├── Team Bidder sends: {"type":"PLACE_BID", "auction_id":"...", "team_id":"...", "user_id":"...", "amount": 300}
   │       Service validates:
   │         • Auction is ACTIVE
   │         • User has BIDDING role in team
   │         • team_contests.currency >= amount
   │         • amount > current Redis highest bid (under Redis lock)
   │       Writes bid to DB
   │       Updates Redis: highest_bid=300, highest_team=<team_id>
   │       Broadcasts to room: {"type":"NEW_HIGHEST_BID","team_id":"...","amount":300}
   │
   ├── (Timer expires or organizer sends FINISH_AUCTION via WebSocket)
   │       finish_auction() is called:
   │         • Reads winner from Redis
   │         • Marks ProblemAuction → FINISHED
   │         • Deducts winning_bid from team_contests.currency
   │         • Creates ContestProblemAssignment
   │         • Cleans up Redis keys
   │       Broadcasts: {"type":"AUCTION_FINISHED","winning_team_id":"...","winning_bid":300}
   │
   └── Repeat for next problem
```

### Auction Lifecycle States

| State      | Meaning                                              |
| ---------- | ---------------------------------------------------- |
| `PENDING`  | Reserved, not yet used in current flow               |
| `ACTIVE`   | Bids are open; this is the only state that accepts bids |
| `FINISHED` | Auction closed; winner recorded                      |

---

## Database Schema

### `problem_auctions`

Tracks the auction for each individual contest problem.

| Column               | Type        | Notes                                              |
| -------------------- | ----------- | -------------------------------------------------- |
| `id`                 | VARCHAR(36) | PK, UUID                                           |
| `contest_id`         | VARCHAR(36) | FK → `contests.id` (CASCADE)                       |
| `contest_problem_id` | VARCHAR(36) | FK → `contest_problems.id` (CASCADE), **UNIQUE**   |
| `status`             | ENUM        | `PENDING` \| `ACTIVE` \| `FINISHED`               |
| `base_price`         | INTEGER     | Minimum bid (copied from `problems.base_price`)    |
| `start_time`         | TIMESTAMPTZ | When the auction opened                            |
| `end_time`           | TIMESTAMPTZ | When the auction is scheduled to close             |
| `winning_team_id`    | VARCHAR(36) | FK → `teams.id` (SET NULL), nullable until FINISHED|
| `winning_bid`        | INTEGER     | Final winning amount, nullable until FINISHED      |
| `created_at`         | TIMESTAMPTZ |                                                    |
| `updated_at`         | TIMESTAMPTZ |                                                    |

**Constraints & Indexes**
- `UNIQUE(contest_problem_id)` — one auction per problem per contest
- `INDEX(contest_id)` — fast lookup of all auctions in a contest

---

### `bids`

An append-only log of every bid placed.

| Column       | Type        | Notes                                       |
| ------------ | ----------- | ------------------------------------------- |
| `id`         | VARCHAR(36) | PK, UUID                                    |
| `auction_id` | VARCHAR(36) | FK → `problem_auctions.id` (CASCADE), indexed|
| `team_id`    | VARCHAR(36) | FK → `teams.id` (CASCADE)                   |
| `bid_amount` | INTEGER     | The amount bid                              |
| `created_at` | TIMESTAMPTZ | Bid timestamp                               |

> **Note**: The DB stores all bids for auditing. The active highest bid is tracked exclusively in Redis during the live auction for performance.

---

### `contest_problem_assignments`

Records which team won each problem.

| Column               | Type        | Notes                                             |
| -------------------- | ----------- | ------------------------------------------------- |
| `id`                 | VARCHAR(36) | PK, UUID                                          |
| `contest_id`         | VARCHAR(36) | FK → `contests.id` (CASCADE), indexed             |
| `contest_problem_id` | VARCHAR(36) | FK → `contest_problems.id` (CASCADE), **UNIQUE**  |
| `team_id`            | VARCHAR(36) | FK → `teams.id` (CASCADE), indexed               |
| `winning_bid`        | INTEGER     | Final amount paid                                 |
| `status`             | ENUM        | `ASSIGNED` \| `SOLVED` \| `FAILED`               |
| `created_at`         | TIMESTAMPTZ |                                                   |
| `updated_at`         | TIMESTAMPTZ |                                                   |

---

### Entity Relationships (Bidding)

```
contests ──< problem_auctions ──< bids
                    │
                    └──> contest_problem_assignments ──> teams
```

---

## Redis State

Redis holds the **hot path** bidding state during an active auction to avoid hammering the database on every bid.

| Key                               | Value              | Purpose                                    |
| --------------------------------- | ------------------ | ------------------------------------------ |
| `auction:{auction_id}:highest_bid`| Integer (string)   | Current highest bid amount                 |
| `auction:{auction_id}:highest_team`| Team UUID (string) | Team that placed the current highest bid  |
| `auction:{auction_id}:lock`       | Identifier string  | Mutex lock — prevents race conditions       |

### Initialization
When an auction starts, Redis is seeded with:
```
highest_bid  = problem.base_price
highest_team = ""
```

### Lock Mechanism
Each bid attempt acquires a Redis lock using `SET NX EX 5` (SET if Not eXists, expires in 5 seconds). If the lock is already held:
- The bid is **rejected immediately** with a `400 Bad Request`.
- No spin-wait — avoids cascading latency.
- The 5-second TTL ensures the lock self-heals if the server crashes mid-bid.

### Cleanup
After `finish_auction()` all three Redis keys are deleted.

---

## Module Architecture

```
app/api/bidding/
├── __init__.py
├── schemas.py      ← Pydantic request/response models
├── dao.py          ← Raw database queries (BiddingDAO)
├── services.py     ← Business logic (BiddingService)
├── handlers.py     ← HTTP handler functions (thin layer)
├── websocket.py    ← WebSocket connection manager + bid loop
└── routes.py       ← Route declarations (HTTP + WebSocket)
```

Follows the project-wide **4-layer pattern**:
```
routes.py → handlers.py → services.py → dao.py → DB
```

---

## API Reference

> Base path: `/api/bidding`  
> All HTTP routes require `Authorization: Bearer <access_token>`

### POST `/contests/{contest_id}/auctions/start`

Start the next auction for a contest.

**Request body**
```json
{
  "data": {
    "contest_problem_id": "uuid-of-specific-problem",
    "duration_seconds": 60
  }
}
```

> `contest_problem_id` can be used to target a specific problem. If omitted or pointing to the `fetch_next_problem` result, the service selects the next unresolved problem by `problem_order`.

**Response** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": "auction-uuid",
    "contest_id": "contest-uuid",
    "contest_problem_id": "cp-uuid",
    "status": "ACTIVE",
    "base_price": 100,
    "start_time": "2026-03-12T00:00:00Z",
    "end_time": "2026-03-12T00:01:00Z",
    "winning_team_id": null,
    "winning_bid": null,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

**Validations / Errors**

| Condition                             | HTTP | Error Code                    |
| ------------------------------------- | ---- | ----------------------------- |
| Contest does not exist                | 404  | `CONTEST_NOT_FOUND`           |
| Contest status ≠ `ACTIVE`             | 400  | `REGISTRATION_CLOSED`         |
| Another auction already running       | 409  | `AUCTION_ALREADY_ACTIVE`      |
| No remaining problems to auction      | 400  | `NO_PROBLEM_AVAILABLE`        |

---

### GET `/contests/{contest_id}/auctions/current`

Return the current active (or most recent) auction for a contest.

**Response** `200 OK` — same shape as start auction response.

**Errors**

| Condition           | HTTP | Error Code          |
| ------------------- | ---- | ------------------- |
| No auction exists   | 404  | `AUCTION_NOT_FOUND` |

---

### GET `/auctions/{auction_id}/result`

Return the final result of a finished auction.

**Response** `200 OK`
```json
{
  "success": true,
  "data": {
    "auction_id": "uuid",
    "contest_problem_id": "uuid",
    "winning_team_id": "uuid or null",
    "winning_bid": 250,
    "status": "FINISHED"
  }
}
```

---

## WebSocket Protocol

**Endpoint**: `ws://<host>/api/bidding/ws/{contest_id}`

Each connected client is added to a **contest room**. Messages are only broadcast within the same contest.

---

### Client → Server Messages

#### PLACE_BID
```json
{
  "type": "PLACE_BID",
  "auction_id": "uuid",
  "team_id": "uuid",
  "user_id": "uuid",
  "amount": 250
}
```

#### FINISH_AUCTION _(organizer only)_
```json
{
  "type": "FINISH_AUCTION",
  "auction_id": "uuid"
}
```

---

### Server → Client Messages

#### NEW_HIGHEST_BID _(broadcast to all)_
```json
{
  "type": "NEW_HIGHEST_BID",
  "team_id": "uuid",
  "amount": 250
}
```

#### AUCTION_FINISHED _(broadcast to all)_
```json
{
  "type": "AUCTION_FINISHED",
  "auction_id": "uuid",
  "winning_team_id": "uuid or null",
  "winning_bid": 250
}
```

#### ERROR _(sent only to the sender)_
```json
{
  "type": "ERROR",
  "message": "Bid amount must be strictly greater than the current highest bid"
}
```

---

### WebSocket Connection Flow

```
Client                              Server
  |------ connect ws/{contest_id} ------->|  accepted, joins room
  |                                       |
  |-- PLACE_BID (auction_id, amount) ---->|  validate → Redis lock → update → DB
  |                                       |
  |<-- NEW_HIGHEST_BID (broadcast) -------|  sent to ALL clients in room
  |                                       |
  |-- FINISH_AUCTION (auction_id) ------->|  finish_auction() → deduct → assign
  |                                       |
  |<-- AUCTION_FINISHED (broadcast) ------|  sent to ALL clients in room
  |                                       |
  |------ disconnect ----------------------|  removed from room
```

---

## Security & Edge Cases

### Role Enforcement
- Only users with `TeamRole.BIDDING` in their team may call `place_bid`.
- `TeamRole.CODING` members are rejected with `403 NOT_BIDDER_ROLE`.
- This is validated against the `team_members` table on every bid.

### Race Conditions
- Redis `SET NX EX 5` lock ensures only one bid can update the highest bid at a time.
- If the lock is held, the incoming bid returns a `400` immediately.
- A 5-second TTL prevents permanent lock-up if the process crashes.
- The re-check of `amount > current_highest` happens **inside the lock** to prevent TOCTOU races.

### Edge Cases Handled

| Scenario                              | Behaviour                                      |
| ------------------------------------- | ---------------------------------------------- |
| Bid on non-active auction             | `400 AUCTION_NOT_ACTIVE`                       |
| Bid ≤ current highest                 | `400 BID_TOO_LOW`                              |
| Team currency < bid amount            | `400 INSUFFICIENT_CURRENCY`                    |
| Auction already active for contest    | `409 AUCTION_ALREADY_ACTIVE`                   |
| No problems left to auction           | `400 NO_PROBLEM_AVAILABLE`                     |
| Auction ends with no winner           | Auction marked FINISHED, no assignment created, currency unchanged |
| UNIQUE constraint on `contest_problem_id` | Prevents double-auctioning same problem at DB level |
| WebSocket client disconnects mid-auction | Removed from room, auction continues unaffected |
| Redis lock TTL expiry (server crash)  | Lock auto-expires after 5 s, next bid succeeds  |

---

*Generated on 2026-03-12*
