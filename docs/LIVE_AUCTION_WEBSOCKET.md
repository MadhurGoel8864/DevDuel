# Live Auction System - WebSocket Documentation

## Overview

DevDuel's live auction system allows teams to bid on coding problems in real-time during a contest. An organizer starts auctions one problem at a time, teams place bids via WebSocket, and the highest bidder wins the problem. The winning team's currency is deducted and the problem is assigned to them.

---

## Roles & Responsibilities

| Role | Who | What They Do |
|------|-----|-------------|
| **Organizer** | Contest creator/admin | Starts auctions, monitors progress, can manually finish auctions |
| **Bidder** | Team member with `BIDDING` role | Places bids on behalf of their team via WebSocket |
| **Coder** | Team member with `CODING` role | Cannot bid; solves problems after auction is won |
| **Spectator** | Any connected WebSocket client | Receives real-time bid updates (read-only) |

---

## End-to-End Auction Flow

### Step 1: Setup (Before Auction)

1. Organizer creates a **Contest** (status goes through `DRAFT` -> `REGISTRATION_OPEN` -> `ACTIVE`)
2. Problems are added to the contest as **ContestProblems** with a `base_price` and `problem_order`
3. Teams register for the contest; each team receives a starting `currency` (default: 1000)
4. Each team assigns members either the `BIDDING` or `CODING` role

### Step 2: Clients Connect via WebSocket

All participants (bidders, spectators) connect to the WebSocket endpoint:

```
ws://<host>/api/bidding/ws/{contest_id}
```

- No authentication is required at connection time
- Clients are added to a per-contest "room" managed by the `ConnectionManager`
- Multiple clients can connect per team

### Step 3: Organizer Starts an Auction

The organizer calls the REST endpoint:

```http
POST /api/bidding/contests/{contest_id}/auctions/start
Authorization: Bearer <jwt_token>

{
  "data": {
    "contest_problem_id": "<optional UUID>",
    "duration_seconds": 60
  }
}
```

- If `contest_problem_id` is omitted, the system auto-selects the next un-auctioned problem (by `problem_order`)
- Only **one auction can be active per contest** at a time
- The contest must be in `ACTIVE` status

**What happens server-side:**
1. A `ProblemAuction` record is created with `status=ACTIVE`
2. Redis is seeded with the base price as the initial highest bid
3. A background task is scheduled to auto-finish the auction after `duration_seconds`
4. A **WebSocket broadcast** is sent to all connected clients:

```json
{
  "type": "AUCTION_STARTED",
  "auction_id": "<UUID>",
  "contest_problem_id": "<UUID>",
  "base_price": 1000,
  "start_time": "2026-03-26T10:00:00+05:30",
  "end_time": "2026-03-26T10:01:00+05:30"
}
```

### Step 4: Teams Place Bids

Bidders send bids through the WebSocket connection:

```json
{
  "type": "PLACE_BID",
  "auction_id": "<UUID>",
  "team_id": "<UUID>",
  "user_id": "<UUID>",
  "amount": 1200
}
```

**Validations (in order):**

| Check | Error If Failed |
|-------|----------------|
| Auction exists and is `ACTIVE` | `Auction not currently active` |
| Current time < auction `end_time` | `Auction has ended` |
| User has `BIDDING` role in team | `Only BIDDING role can bid` |
| Team is registered in the contest | `Team not registered` |
| Team has enough currency | `Not enough currency` |
| Bid > current highest bid | `Bid must exceed current highest` |

**On success**, all clients in the contest room receive:

```json
{
  "type": "NEW_HIGHEST_BID",
  "team_id": "<UUID>",
  "amount": 1200
}
```

**On failure**, only the sender receives:

```json
{
  "type": "ERROR",
  "message": "Bid must exceed current highest bid"
}
```

### Step 5: Auction Ends

An auction can end in two ways:

**Path A - Auto-finish (timer expires):**
A background `asyncio` task fires after `duration_seconds` and finishes the auction automatically.

**Path B - Manual finish:**
A client sends:

```json
{
  "type": "FINISH_AUCTION",
  "auction_id": "<UUID>"
}
```

**What happens when an auction finishes:**

1. Read the winning team and bid amount from Redis
2. In a single atomic database transaction:
   - Mark the `ProblemAuction` as `FINISHED`
   - Set `winning_team_id` and `winning_bid`
   - Deduct the winning bid from the team's currency
   - Create a `ContestProblemAssignment` (status: `ASSIGNED`)
3. Clean up Redis keys
4. Broadcast to all clients:

```json
{
  "type": "AUCTION_FINISHED",
  "auction_id": "<UUID>",
  "winning_team_id": "<UUID or null>",
  "winning_bid": 1200
}
```

If no bids were placed, `winning_team_id` and `winning_bid` are `null`.

### Step 6: Repeat

The organizer starts the next auction for the next problem. This cycle repeats until all contest problems have been auctioned.

---

## WebSocket Message Reference

### Client -> Server

| Type | Fields | Description |
|------|--------|-------------|
| `PLACE_BID` | `auction_id`, `team_id`, `user_id`, `amount` | Place a bid. `amount` must be a positive integer exceeding the current highest bid. |
| `FINISH_AUCTION` | `auction_id` | Manually end an auction early. |

### Server -> Client (Broadcast to all in room)

| Type | Fields | Description |
|------|--------|-------------|
| `AUCTION_STARTED` | `auction_id`, `contest_problem_id`, `base_price`, `start_time`, `end_time` | A new auction has begun. |
| `NEW_HIGHEST_BID` | `team_id`, `amount` | A new highest bid has been placed. |
| `AUCTION_FINISHED` | `auction_id`, `winning_team_id`, `winning_bid` | The auction has ended. Nulls if no winner. |

### Server -> Client (Unicast to sender only)

| Type | Fields | Description |
|------|--------|-------------|
| `ERROR` | `message` | Something went wrong with the client's request. |

---

## REST API Endpoints

### Start Auction

```
POST /api/bidding/contests/{contest_id}/auctions/start
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `contest_problem_id` | UUID | No | Specific problem to auction. Auto-selects next if omitted. |
| `duration_seconds` | int | Yes | How long the auction lasts. |

**Response:** `201 Created` with auction details.

### Get Current Auction

```
GET /api/bidding/contests/{contest_id}/auctions/current
```

Returns the currently active auction, or the most recent one if none is active.

### Get Auction Result

```
GET /api/auctions/{auction_id}/result
```

Returns the final result of a completed auction including winner and winning bid.

---

## Race Condition Handling

Concurrent bids are protected using a **Redis mutex lock**:

```
Key: auction:{auction_id}:lock
TTL: 5 seconds (auto-expires to prevent deadlocks)
```

**How it works:**

1. A bid request attempts to acquire the lock using Redis `SET NX EX`
2. If the lock is already held by another bid, the request is **immediately rejected** (no waiting/retry)
3. Under the lock: read current highest bid, validate, update Redis
4. Lock is released after processing (or auto-expires after 5s)

**Redis keys per auction:**

| Key | Purpose |
|-----|---------|
| `auction:{id}:highest_bid` | Current highest bid amount |
| `auction:{id}:highest_team` | Team ID of the current highest bidder |
| `auction:{id}:lock` | Mutex lock (TTL 5s) |

All keys are cleaned up when the auction finishes.

---

## Error Reference

| Error | HTTP/WS | Cause |
|-------|---------|-------|
| `AuctionNotFoundException` | 404 | Invalid auction ID |
| `AuctionAlreadyActiveException` | 409 | Tried to start a second auction in the same contest |
| `AuctionNotActiveException` | 400 | Bid on a non-active auction |
| `AuctionExpiredException` | 400 | Bid placed after `end_time` |
| `InsufficientCurrencyException` | 400 | Team can't afford the bid |
| `BidTooLowException` | 400 | Bid is not higher than the current highest |
| `NotBidderRoleException` | 403 | User doesn't have the `BIDDING` role |
| `NoProblemAvailableException` | 400 | All problems have already been auctioned |
| `TeamNotInContestException` | 403 | Team isn't registered for this contest |

---

## Sequence Diagram

```
Organizer              Server              Redis            WebSocket Clients
   |                     |                   |                     |
   |-- POST /start ----->|                   |                     |
   |                     |-- SET base_price->|                     |
   |                     |-- schedule timer  |                     |
   |                     |-------- AUCTION_STARTED --------------->|
   |                     |                   |                     |
   |                     |<-------- PLACE_BID (team1, 1100) ------|
   |                     |-- SET NX lock --->|                     |
   |                     |<-- OK ------------|                     |
   |                     |-- GET highest --->|                     |
   |                     |<-- 1000 ----------|                     |
   |                     |-- SET 1100 ------>|                     |
   |                     |-- DEL lock ------>|                     |
   |                     |-------- NEW_HIGHEST_BID (1100) -------->|
   |                     |                   |                     |
   |                     |<-------- PLACE_BID (team2, 1050) ------|
   |                     |-- SET NX lock --->|                     |
   |                     |<-- OK ------------|                     |
   |                     |-- GET highest --->|                     |
   |                     |<-- 1100 ----------|  (1050 < 1100)     |
   |                     |-- DEL lock ------>|                     |
   |                     |-------- ERROR "Bid too low" ---------->| (sender only)
   |                     |                   |                     |
   |                     |<-------- PLACE_BID (team2, 1300) ------|
   |                     |-- SET NX lock --->|                     |
   |                     |<-- OK ------------|                     |
   |                     |-- GET highest --->|                     |
   |                     |<-- 1100 ----------|                     |
   |                     |-- SET 1300 ------>|                     |
   |                     |-- DEL lock ------>|                     |
   |                     |-------- NEW_HIGHEST_BID (1300) -------->|
   |                     |                   |                     |
   |              [timer expires]            |                     |
   |                     |-- GET winner ---->|                     |
   |                     |<-- team2, 1300 ---|                     |
   |                     |-- DB: deduct currency, assign problem   |
   |                     |-- DEL keys ------>|                     |
   |                     |-------- AUCTION_FINISHED (team2) ------>|
   |                     |                   |                     |
```

---

## Client Integration Guide

### Connecting

```javascript
const ws = new WebSocket("ws://localhost:8150/api/bidding/ws/<contest_id>");

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case "AUCTION_STARTED":
      // Show auction UI with base_price, start countdown timer to end_time
      break;
    case "NEW_HIGHEST_BID":
      // Update displayed current bid and leading team
      break;
    case "AUCTION_FINISHED":
      // Show winner or "no bids" if winning_team_id is null
      break;
    case "ERROR":
      // Display error to user (e.g. "Bid too low")
      break;
  }
};
```

### Placing a Bid

```javascript
ws.send(JSON.stringify({
  type: "PLACE_BID",
  auction_id: "<auction-uuid>",
  team_id: "<team-uuid>",
  user_id: "<user-uuid>",
  amount: 1500
}));
```

### Finishing an Auction Manually

```javascript
ws.send(JSON.stringify({
  type: "FINISH_AUCTION",
  auction_id: "<auction-uuid>"
}));
```
