# Bidding System — Frontend Changes Required

This document lists every change the frontend must make to stay compatible
with the bidding-bug remediation pass applied on 2026-04-11. These changes
are **breaking**; the old client code will fail silently or get closed with
an auth error after deployment.

---

## 1. WebSocket URL now requires an access token

### Before

```ts
const ws = new WebSocket(`wss://host/api/bidding/ws/${contestId}`);
```

### After

```ts
const token = getAccessToken(); // same JWT used for REST Authorization header
const ws = new WebSocket(
  `wss://host/api/bidding/ws/${contestId}?token=${encodeURIComponent(token)}`
);
```

### Why

The WebSocket had no authentication at all — anyone who knew a `contestId`
could open a socket and bid as any user by putting another user's ID in
the payload. The backend now verifies the JWT on connect and uses the
token's `sub` claim as the only trusted identity.

### Error codes

If the token is missing / invalid / expired / belongs to an inactive or
unverified user, the server closes the socket immediately with:

| `code` | Reason                     | What the client should do                  |
| ------ | -------------------------- | ------------------------------------------ |
| 4401   | Missing or invalid token   | Refresh access token and reopen the socket |

The existing access-token refresh logic (from the REST layer) should be
reused: on close code 4401, call the `/auth/refresh` endpoint, then reopen
the socket with the new token.

### Token expiry while the socket is open

The backend does **not** re-validate the token on every inbound message —
it's only checked at `connect` time. If a session is going to be very long
the frontend should proactively close and reopen the socket on or before
access-token expiry to pick up a fresh token. A simple timer matching the
access-token TTL is sufficient.

---

## 2. `PLACE_BID` payload — `user_id` removed, `amount` must be an integer

### Before

```json
{
  "type": "PLACE_BID",
  "auction_id": "au_abc",
  "team_id": "tm_xyz",
  "user_id": "us_def",
  "amount": "300"
}
```

### After

```json
{
  "type": "PLACE_BID",
  "auction_id": "au_abc",
  "team_id": "tm_xyz",
  "amount": 300
}
```

### What changed

1. **Drop `user_id`.** The server ignores any `user_id` in the payload and
   uses the authenticated identity from the connection token. Sending it
   is harmless but the field is dead weight.
2. **`amount` must be a JSON number**, not a string. `"300"` now returns
   `ERROR "PLACE_BID amount must be a positive integer"`.
3. **`amount` must be a positive integer.** `0`, negative values, floats,
   and booleans are all rejected at the WS boundary.
4. `team_id` / `auction_id` must be non-empty strings.

### Frontend action

- Remove the `user_id` field from the `PLACE_BID` message builder.
- Coerce form/input values with `parseInt(raw, 10)` before sending.
- Validate client-side for a positive integer to avoid the round-trip.

---

## 3. `FINISH_AUCTION` payload — `user_id` removed

### Before

```json
{ "type": "FINISH_AUCTION", "auction_id": "au_abc", "user_id": "us_def" }
```

### After

```json
{ "type": "FINISH_AUCTION", "auction_id": "au_abc" }
```

The organizer identity is taken from the WS token; the server uses it to
enforce that only the contest creator can force-end. Sending `user_id`
from the client is now ignored.

---

## 4. `NEW_HIGHEST_BID` broadcast now includes `auction_id`

### Before

```json
{
  "type": "NEW_HIGHEST_BID",
  "server_time": "...",
  "team_id": "tm_xyz",
  "team_name": "Team X",
  "amount": 300
}
```

### After

```json
{
  "type": "NEW_HIGHEST_BID",
  "server_time": "...",
  "auction_id": "au_abc",
  "team_id": "tm_xyz",
  "team_name": "Team X",
  "amount": 300
}
```

### Why

Without `auction_id` the client had no way to tell whether an incoming
highest-bid update belonged to the auction it was currently displaying —
a stale update from a just-finished auction could clobber the UI of a
freshly-started one.

### Frontend action

- When handling `NEW_HIGHEST_BID`, compare `msg.auction_id` against the
  currently displayed auction and **discard non-matching updates**.
- TypeScript type for the message should gain `auction_id: string`.

---

## 5. Auction `winning_bid` / `winning_team_id` no longer mirror live state

### Before

While an auction was `ACTIVE`, the backend populated **both**
`current_highest_bid` / `current_highest_team` **and**
`winning_bid` / `winning_team_id` with the live leader from Redis.

### After

While an auction is `ACTIVE`:

| Field                 | Value                                 |
| --------------------- | ------------------------------------- |
| `current_highest_bid` | Live top bid from Redis (or `null`)   |
| `current_highest_team`| Live leading team id (or `null`)      |
| `winning_bid`         | **`null`** (not decided yet)          |
| `winning_team_id`     | **`null`** (not decided yet)          |

`winning_*` only becomes populated when `status === "FINISHED"`.

### Why

Frontend code that branched on `winning_bid != null` to decide "auction
is over" was rendering in-progress auctions as already-won.

### Frontend action

Audit every use of `winning_bid` / `winning_team_id`:

- If you are displaying the **running leader** during an active auction,
  switch to `current_highest_bid` / `current_highest_team`.
- If you are displaying the **final winner**, keep using `winning_bid` /
  `winning_team_id` but also guard on `auction.status === "FINISHED"`.
- Do not treat `winning_bid != null` alone as a finished-auction signal.

### Places this affects (confirm on the frontend side)

- `AuctionCard` / `AuctionResultPanel` components
- Any reducer/store selector that derives "is auction resolved?"
- The `SYNC` payload handler (see section 7) — the `current_auction`
  object now carries the same new semantics.

---

## 6. `POST /bidding/contests/{id}/auctions/start` — new 400 error

### What changed

If Redis is unavailable when starting an auction, the server now:

1. Marks the just-created auction row as FINISHED-no-winner (rollback).
2. Returns HTTP **400 Bad Request** with:
   ```json
   { "message": "Failed to initialize auction state. Please try again." }
   ```

Previously the server returned 201 with a broken auction that could never
finish. Retrying the request on 400 is safe — the previous attempt has
already been cleaned up.

### Frontend action

- Treat 400 from this endpoint as "transient infra issue, please retry"
  rather than a validation error. A simple "Retry" toast is appropriate.

---

## 7. `SYNC` payload — unchanged shape, but semantics aligned with §5

`SYNC` is still:

```json
{
  "type": "SYNC",
  "server_time": "...",
  "contest_status": "ACTIVE" | "FINISHED" | ...,
  "current_auction": { ...AuctionResponseData } | null
}
```

The only difference: for an `ACTIVE` `current_auction`, `winning_bid` and
`winning_team_id` are now `null`. Use `current_highest_*` for the live
leader. No code changes are required beyond what §5 already covers — this
is a reminder that the SYNC path hits the same enriched payload.

---

## 8. `AUCTION_FINISHED` broadcast — no duplicate on force-end (behavioral)

Previously, when the organizer force-ended an auction early, clients saw
**two** `AUCTION_FINISHED` broadcasts:

1. The authoritative one from `force_end_auction` (with the real winner).
2. A phantom one from the original timer waking up (with
   `winning_team_id: null`, `winning_bid: null`), which overwrote the
   first one in the UI.

The backend now cancels the timer before finalizing, so there will be
exactly one broadcast per auction.

### Frontend action

No code change required, but if the frontend had workaround logic like
"ignore AUCTION_FINISHED events with null winner if we already have a
winner", it can now be removed. Verify and delete that defensive code
after this backend change ships.

---

## 9. `AUCTION_STARTED` broadcast — unchanged

Included here only to confirm nothing changed. The `auction` object now
has `winning_bid: null` / `winning_team_id: null` on start (as it always
should have), so if the frontend was working around the bug it can stop.

---

## Quick checklist for the frontend PR

- [ ] Pass `?token=<access_jwt>` when opening the bidding WebSocket
- [ ] Handle close code 4401 → refresh token → reopen
- [ ] Reopen the socket before access-token expiry (or on expiry alarm)
- [ ] Remove `user_id` from `PLACE_BID` message builder
- [ ] Remove `user_id` from `FINISH_AUCTION` message builder
- [ ] Ensure `amount` is sent as a JSON number (positive integer)
- [ ] Add `auction_id` to the `NEW_HIGHEST_BID` TypeScript type
- [ ] Filter `NEW_HIGHEST_BID` messages by `auction_id` before applying
- [ ] Replace uses of `winning_bid` / `winning_team_id` on ACTIVE auctions
      with `current_highest_bid` / `current_highest_team`
- [ ] Guard "is auction finished?" checks on `status === "FINISHED"`
- [ ] Retry UI on 400 from `/bidding/contests/{id}/auctions/start`
- [ ] Delete any dedupe workaround for double `AUCTION_FINISHED` events

---

## Testing the integration end-to-end

Suggested manual flow for QA after both backend + frontend ship:

1. Log in, join a contest as a bidder.
2. Open the bidding page. DevTools → Network → WS → confirm the URL has
   `?token=...`. Confirm SYNC arrives.
3. Have the organizer start an auction. Confirm `AUCTION_STARTED`
   broadcast lands; UI shows the problem and `current_highest_bid = null`
   (or the base price), `winning_team_id` stays `null`.
4. Place a bid from two different teams in parallel. Confirm both
   `NEW_HIGHEST_BID` broadcasts carry matching `auction_id` and the UI
   ignores any stale ones.
5. Let the timer expire naturally. Confirm exactly **one**
   `AUCTION_FINISHED` broadcast. `winning_*` fields populated.
6. Start a second auction, have the organizer force-end it at t=3 s.
   Confirm exactly **one** `AUCTION_FINISHED` (no phantom at t=duration).
7. Expire the access token (shorten TTL in staging or wait it out). The
   socket should close with code 4401; the client should refresh and
   reconnect transparently, then receive a fresh SYNC.
