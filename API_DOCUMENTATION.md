# DevDuel API Documentation

> **Base URL:** `https://<your-domain>/api`
> **Content-Type:** `application/json`
> **Timezone:** All timestamps are ISO 8601 in IST (Asia/Kolkata)

---

## Table of Contents

1. [Authentication & Headers](#authentication--headers)
2. [Standard Response Format](#standard-response-format)
3. [Enumerations](#enumerations)
4. [Auth Endpoints](#auth-endpoints)
5. [Users Endpoints](#users-endpoints)
6. [Teams Endpoints](#teams-endpoints)
7. [Team Invites Endpoints](#team-invites-endpoints)
8. [Contests Endpoints](#contests-endpoints)
9. [Problems Endpoints](#problems-endpoints)
10. [Contest Problems Endpoints](#contest-problems-endpoints)
11. [Bidding Endpoints](#bidding-endpoints)
12. [WebSocket — Real-Time Bidding](#websocket--real-time-bidding)
13. [System Endpoints](#system-endpoints)

---

## Authentication & Headers

All protected endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

**Token lifetime:**
- Access Token: 30 minutes
- Refresh Token: 7 days

**JWT payload fields (access token):**

| Field | Type | Description |
|-------|------|-------------|
| `sub` | string | User ID |
| `email` | string | User email |
| `is_organizer` | boolean | Whether user can create/manage contests |
| `type` | string | Always `"access"` |
| `jti` | string | JWT ID (for blacklisting) |
| `exp` | int | Expiry timestamp |

---

## Standard Response Format

Most API endpoints (Users, Teams, Contests, Problems, Bidding) wrap their response in the following envelope:

**Success:**
```json
{
  "success": true,
  "data": { }
}
```

**Paginated Success** (list endpoints that support `page`/`limit`):
```json
{
  "success": true,
  "data": [ ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

> **Note:** Auth endpoints (`/auth/*`) return their payloads directly — **not** wrapped in `success/data`. See each endpoint for its exact response shape.

> **Note:** Most POST/PUT/PATCH endpoints wrap the request body in a `data` key.
> ```json
> { "data": { "field": "value" } }
> ```

---

## Enumerations

> **`is_organizer`** is a boolean field on the user (`true` / `false`), not an enum. Only users with `is_organizer: true` can create and manage contests. This flag is set by an admin and is included in every JWT access token.

| Enum | Values |
|------|--------|
| `UserRole` | `user`, `admin` |
| `TeamRole` | `BIDDING`, `CODING` |
| `ContestStatus` | `DRAFT`, `REGISTRATION_OPEN`, `ACTIVE`, `ENDED` |
| `Difficulty` | `easy`, `medium`, `hard` |
| `AuctionStatus` | `PENDING`, `ACTIVE`, `FINISHED` |
| `AssignmentStatus` | `ASSIGNED`, `SOLVED`, `FAILED` |
| `AuthProvider` | `local`, `google`, `apple` |

---

## Auth Endpoints

> Auth responses are **not** wrapped in the `success/data` envelope — they return their fields directly.

### POST `/auth/register`
Register a new user. Sends a verification OTP to email.

**Auth required:** No
**Status:** `201 Created`

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "string",
  "full_name": "John Doe",
  "invite_token": "optional-team-invite-token"
}
```

> Pass `invite_token` if the user arrived via a team invite link — they will be auto-added to the team after OTP verification.

**Response:**
```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "email": "user@example.com"
}
```

---

### POST `/auth/login`
Login with email and password.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### POST `/auth/logout`
Blacklist both access and refresh tokens.

**Auth required:** Yes (access token in `Authorization` header)

**Request body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "message": "Logged out successfully."
}
```

---

### POST `/auth/refresh`
Exchange a valid refresh token for a new access + refresh token pair.

**Auth required:** No

**Request body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### GET `/auth/me`
Get the current authenticated user's profile.

**Auth required:** Yes

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "role": "user",
  "permissions": [],
  "is_active": true,
  "is_verified": true,
  "is_organizer": false,
  "profile_img_url": null,
  "last_login_at": null
}
```

---

### POST `/auth/send-otp`
Send a new OTP to the provided email.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "OTP sent successfully. Please check your email.",
  "email": "user@example.com"
}
```

---

### POST `/auth/verify-otp`
Verify the OTP to activate the account.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "User verified successfully",
  "is_verified": true,
  "email": "user@example.com"
}
```

> If the user registered via a team invite link, they are auto-joined to the team upon verification.

---

### POST `/auth/resend-otp`
Resend OTP (for unverified accounts).

**Auth required:** No

**Request body / Response:** Same as `POST /auth/send-otp`

---

### POST `/auth/forgot-password`
Request a password reset email.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset instructions have been sent to your email.",
  "email": "user@example.com"
}
```

---

### POST `/auth/reset-password`
Reset the password using a token from the reset email.

**Auth required:** No

**Request body:**
```json
{
  "token": "reset-token-from-email",
  "new_password": "new-secure-password"
}
```

**Response:**
```json
{
  "message": "Password reset successfully"
}
```

---

### GET `/auth/google/login`
Initiate Google OAuth login. **Redirects** the browser to Google's consent page (HTTP 302).

**Auth required:** No

> This endpoint returns an HTTP redirect — it does not return JSON.

---

### GET `/auth/google/callback`
Google OAuth callback. Called by Google after user consent.

**Auth required:** No

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `code` | string | Authorization code from Google |
| `state` | string | CSRF state token |

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Users Endpoints

### POST `/users`
Create a user (alternative registration endpoint).

**Auth required:** No
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "string"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "is_verified": false,
    "is_organizer": false,
    "profile_img_url": null,
    "created_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

### PATCH `/users/me`
Update the authenticated user's profile. Only `full_name` and `username` can be changed. Both fields are optional — only provided fields are updated.

**Auth required:** Yes

**Request body:**
```json
{
  "data": {
    "full_name": "Jane Doe",
    "username": "janedoe"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `full_name` | string | No | New display name |
| `username` | string | No | New unique username |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "janedoe",
    "full_name": "Jane Doe",
    "role": "user",
    "is_active": true,
    "is_verified": true,
    "is_organizer": false,
    "profile_img_url": null,
    "created_at": "2026-03-23T10:00:00+05:30",
    "updated_at": "2026-03-23T10:05:00+05:30"
  }
}
```

**Error cases:**
- `400 USER_VALIDATION_ERROR` — Username is already taken

---

### GET `/users/{user_id}`
Get a user's public profile.

**Auth required:** No

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `user_id` | uuid | User ID |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "is_verified": true,
    "is_organizer": false,
    "profile_img_url": null,
    "created_at": "2026-03-23T10:00:00+05:30",
    "updated_at": "2026-03-23T10:00:00+05:30",
    "last_login_at": "2026-03-23T10:00:00+05:30",
    "email_verified_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

## Teams Endpoints

### POST `/teams`
Create a new team. Creator is auto-added as a `BIDDING` member.

**Auth required:** Yes
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "name": "Team Alpha"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Team Alpha",
    "created_by": "uuid",
    "members": [
      {
        "id": "uuid",
        "team_id": "uuid",
        "user_id": "uuid",
        "role": "BIDDING",
        "created_at": "2026-03-23T10:00:00+05:30"
      }
    ],
    "created_at": "2026-03-23T10:00:00+05:30",
    "updated_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

### GET `/teams/me`
Get a paginated list of teams the authenticated user belongs to.

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Team Alpha",
      "created_by": "uuid",
      "created_at": "2026-03-23T10:00:00+05:30"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 3
  }
}
```

---

### GET `/teams/{team_id}`
Get full team details including members.

**Auth required:** Yes

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `team_id` | uuid | Team ID |

**Response:** Same as `POST /teams`

---

### DELETE `/teams/{team_id}`
Delete a team. Not allowed if the team is in an active contest. Returns the deleted team's data.

**Auth required:** Yes (creator only)

**Response:** Same as `POST /teams`

---

### POST `/teams/{team_id}/members`
Add a member to the team.

**Auth required:** Yes (creator only)
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "user_id": "uuid",
    "role": "CODING"
  }
}
```

**Response:** Same as `GET /teams/{team_id}`

---

### DELETE `/teams/{team_id}/members/{user_id}`
Remove a member from the team.

**Auth required:** Yes (creator only)

**Response:** Same as `GET /teams/{team_id}`

---

### POST `/teams/{team_id}/members/swap-roles`
Swap the roles of the two team members (BIDDING ↔ CODING).

**Auth required:** Yes (creator only)
**Note:** Team must have exactly 2 members.

**Request body:** None

**Response:** Same as `GET /teams/{team_id}`

---

### DELETE `/teams/{team_id}/leave`
Leave a team voluntarily. Team creator must delete the team instead.

**Auth required:** Yes

**Response:**
```json
{
  "message": "You have left the team."
}
```

---

### GET `/teams/{team_id}/status`
Check if a team has all required roles filled.

**Auth required:** Yes

**Response:**
```json
{
  "success": true,
  "data": {
    "is_ready": true,
    "has_bidder": true,
    "has_coder": true,
    "member_count": 2,
    "missing_roles": []
  }
}
```

---

### GET `/teams/{team_id}/my-role`
Get the authenticated user's role in the specified team.

**Auth required:** Yes

**Response:**
```json
{
  "success": true,
  "data": {
    "team_id": "uuid",
    "user_id": "uuid",
    "role": "BIDDING",
    "is_member": true
  }
}
```

> `role` is `null` if the user is not a member.

---

### GET `/teams/{team_id}/can-join/{contest_id}`
Check if a team is eligible to join a specific contest.

**Auth required:** Yes

**Response:**
```json
{
  "success": true,
  "data": {
    "team_id": "uuid",
    "contest_id": "uuid",
    "can_join": false,
    "reasons": ["Team is missing roles: CODING"]
  }
}
```

---

## Team Invites Endpoints

### POST `/teams/{team_id}/invite`
Invite a user to the team by email. Works for both registered and new users. Sends invite email in background.

**Auth required:** Yes (creator only)
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "email": "invitee@example.com",
    "role": "CODING",
    "name": "Jane Doe"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Invite sent.",
    "is_new_user": false
  }
}
```

> `is_new_user: true` means the invitee has no account yet.

---

### GET `/teams/invite/validate`
Validate an invite token from an email link before accepting/declining.

**Auth required:** No

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `token` | string | Invite token from email link |

**Response:**
```json
{
  "success": true,
  "data": {
    "team_id": "uuid",
    "team_name": "Team Alpha",
    "email": "invitee@example.com",
    "role": "CODING",
    "is_new_user": false
  }
}
```

> Use `is_new_user` to decide whether to show an accept/decline page or a register page.

---

### POST `/teams/invite/accept`
Accept a pending team invite.

**Auth required:** Yes

**Request body:**
```json
{
  "data": {
    "token": "invite-token-from-email"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": { "message": "Invite accepted. You have joined the team." }
}
```

---

### POST `/teams/invite/decline`
Decline a pending team invite.

**Auth required:** Yes

**Request body:**
```json
{
  "data": {
    "token": "invite-token-from-email"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": { "message": "Invite declined." }
}
```

---

## Contests Endpoints

### POST `/contests`
Create a new contest.

**Auth required:** Yes (`is_organizer: true`)
**Status:** `201 Created`
**Error:** `403 FORBIDDEN` if user is not an organizer

**Request body:**
```json
{
  "data": {
    "name": "Sprint Challenge #1",
    "description": "Optional description",
    "start_time": "2026-04-01T10:00:00+05:30",
    "end_time": "2026-04-01T14:00:00+05:30"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Sprint Challenge #1",
    "description": "Optional description",
    "start_time": "2026-04-01T10:00:00+05:30",
    "end_time": "2026-04-01T14:00:00+05:30",
    "status": "DRAFT",
    "created_by": "uuid",
    "teams": [],
    "created_at": "2026-03-23T10:00:00+05:30",
    "updated_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

### GET `/contests`
List all contests (paginated).

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Sprint Challenge #1",
      "description": "...",
      "start_time": "2026-04-01T10:00:00+05:30",
      "end_time": "2026-04-01T14:00:00+05:30",
      "status": "REGISTRATION_OPEN",
      "created_by": "uuid",
      "created_at": "2026-03-23T10:00:00+05:30"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 42
  }
}
```

---

### GET `/contests/active`
List only active contests (`status = ACTIVE`), paginated.

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:** Same schema as `GET /contests`

---

### GET `/contests/me`
List contests the authenticated user's team(s) are registered in (paginated).

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:** Same schema as `GET /contests`

---

### GET `/contests/created`
List contests created by the authenticated user (paginated).

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:** Same schema as `GET /contests`

---

### GET `/contests/{contest_id}`
Get full contest details, including registered teams.

**Auth required:** Yes

**Response:** Same schema as `POST /contests`

---

### PATCH `/contests/{contest_id}`
Update contest details. Not allowed when status is `ENDED`. Sends update email to all registered team members.

**Auth required:** Yes (`is_organizer: true`, creator only)

**Request body (all fields optional):**
```json
{
  "data": {
    "name": "Updated Name",
    "description": "Updated description",
    "start_time": "2026-04-01T10:00:00+05:30",
    "end_time": "2026-04-01T14:00:00+05:30"
  }
}
```

**Response:** Same schema as `POST /contests`

---

### POST `/contests/{contest_id}/register`
Register a team for a contest. Contest must be in `REGISTRATION_OPEN` status.

**Auth required:** Yes (team creator only)
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "team_id": "uuid"
  }
}
```

**Response:** Same schema as `POST /contests` (returns the full updated contest with teams list)

---

### GET `/contests/{contest_id}/teams`
Get the leaderboard for a contest, ordered by score (desc), then currency (desc).

**Auth required:** Yes

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "rank": 1,
      "team_id": "uuid",
      "score": 300,
      "currency": 750
    }
  ]
}
```

---

### GET `/contests/{contest_id}/teams/{team_id}`
Get a specific team's standing in a contest.

**Auth required:** Yes

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "team_id": "uuid",
    "contest_id": "uuid",
    "currency": 750,
    "score": 300,
    "created_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

### POST `/contests/{contest_id}/open-registration`
Transition contest from `DRAFT` → `REGISTRATION_OPEN`.

**Auth required:** Yes (`is_organizer: true`, creator only)

**Response:** Same schema as `POST /contests` (returns the updated contest)

---

### POST `/contests/{contest_id}/start`
Transition contest from `REGISTRATION_OPEN` → `ACTIVE`.

**Auth required:** Yes (`is_organizer: true`, creator only)

**Response:** Same schema as `POST /contests` (returns the updated contest)

---

### POST `/contests/{contest_id}/end`
Transition contest from `ACTIVE` → `ENDED`.

**Auth required:** Yes (`is_organizer: true`, creator only)

**Response:** Same schema as `POST /contests` (returns the updated contest)

---

## Problems Endpoints

### POST `/problems`
Create a new reusable coding problem. Slug is auto-generated from the title.

**Auth required:** Yes
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "title": "Two Sum",
    "description": "Given an array of integers...",
    "difficulty": "easy",
    "points": 100,
    "base_price": 200,
    "time_limit_ms": 2000,
    "memory_limit_mb": 256
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Two Sum",
    "slug": "two-sum",
    "description": "Given an array of integers...",
    "difficulty": "easy",
    "points": 100,
    "base_price": 200,
    "time_limit_ms": 2000,
    "memory_limit_mb": 256,
    "created_by": "uuid",
    "is_active": true,
    "created_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

### GET `/problems`
List problems with optional filters.

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `difficulty` | string | — | Filter by `easy`, `medium`, or `hard` |
| `search` | string | — | Search by title keyword |
| `created_by` | uuid | — | Filter by creator user ID |
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:** Array of problem objects wrapped in `APIResponse` (same schema as `POST /problems`)

---

### GET `/problems/{problem_id}`
Get a problem by ID.

**Auth required:** Yes

**Response:** Single problem object (same schema as `POST /problems`)

---

### PUT `/problems/{problem_id}`
Update a problem. Only the creator may update. All fields optional.

**Auth required:** Yes (creator only)

**Request body:**
```json
{
  "data": {
    "title": "Two Sum (Updated)",
    "description": "...",
    "difficulty": "medium",
    "points": 150,
    "base_price": 250,
    "time_limit_ms": 1500,
    "memory_limit_mb": 128
  }
}
```

**Response:** Updated problem object (same schema as `POST /problems`)

---

### DELETE `/problems/{problem_id}`
Soft-delete a problem (`is_active = false`). Only the creator may delete. Returns the updated problem object.

**Auth required:** Yes (creator only)

**Response:** Problem object with `is_active: false` (same schema as `POST /problems`)

---

### GET `/problems/builtin/problems`
List platform-curated built-in problems that organizers can import into contests.

**Auth required:** Yes

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `difficulty` | string | — | Filter by `easy`, `medium`, or `hard` |
| `search` | string | — | Search by title keyword |
| `page` | int | `1` | Page number (min: 1) |
| `limit` | int | `20` | Items per page (min: 1, max: 100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Reverse Linked List",
      "slug": "reverse-linked-list",
      "description": "...",
      "difficulty": "easy",
      "points": 100,
      "base_price": 150,
      "time_limit_ms": 2000,
      "memory_limit_mb": 256,
      "created_at": "2026-03-23T10:00:00+05:30"
    }
  ]
}
```

---

## Contest Problems Endpoints

### POST `/contests/{contest_id}/problems`
Add a problem to a contest with a bidding order.

**Auth required:** Yes
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "problem_id": "uuid",
    "problem_order": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "contest_id": "uuid",
    "problem_id": "uuid",
    "problem_order": 1,
    "is_active": true,
    "created_at": "2026-03-23T10:00:00+05:30",
    "problem": { }
  }
}
```

> `problem` contains the full problem object nested inline.

---

### GET `/contests/{contest_id}/problems`
List all active problems in a contest, ordered by `problem_order`.

**Auth required:** Yes

**Response:** Array of contest problem objects (same schema as above)

---

### DELETE `/contests/{contest_id}/problems/{contest_problem_id}`
Soft-remove a problem from a contest (`is_active = false`). Returns the updated contest problem.

**Auth required:** Yes

**Response:** Contest problem object with `is_active: false` (same schema as `POST /contests/{contest_id}/problems`)

---

### POST `/contests/{contest_id}/problems/import`
Import a built-in platform problem into a contest. Clones the built-in problem into a new user-owned problem and attaches it to the contest.

**Auth required:** Yes
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "builtin_problem_id": "uuid",
    "problem_order": 2
  }
}
```

**Response:** Same as `POST /contests/{contest_id}/problems`

---

## Bidding Endpoints

### POST `/bidding/contests/{contest_id}/auctions/start`
Start an auction for a problem in an ACTIVE contest. Broadcasts `AUCTION_STARTED` to all WebSocket clients. Auto-finishes after `duration_seconds`.

**Auth required:** Yes
**Status:** `201 Created`

**Request body:**
```json
{
  "data": {
    "contest_problem_id": "uuid",
    "duration_seconds": 60
  }
}
```

> `contest_problem_id` is required. `duration_seconds` defaults to `60`.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "contest_id": "uuid",
    "contest_problem_id": "uuid",
    "status": "ACTIVE",
    "base_price": 200,
    "start_time": "2026-03-23T10:00:00+05:30",
    "end_time": "2026-03-23T10:01:00+05:30",
    "winning_team_id": null,
    "winning_bid": null,
    "created_at": "2026-03-23T10:00:00+05:30",
    "updated_at": "2026-03-23T10:00:00+05:30"
  }
}
```

---

### GET `/bidding/contests/{contest_id}/auctions/current`
Get the currently active (or most recent) auction for a contest.

**Auth required:** Yes

**Response:** Same schema as start auction

---

### GET `/bidding/auctions/{auction_id}/result`
Get the result of a finished auction.

**Auth required:** Yes

**Response:**
```json
{
  "success": true,
  "data": {
    "auction_id": "uuid",
    "contest_problem_id": "uuid",
    "winning_team_id": "uuid",
    "winning_bid": 350,
    "status": "FINISHED"
  }
}
```

---

## WebSocket — Real-Time Bidding

### WS `/bidding/ws/{contest_id}`

Connect to the real-time bidding channel for a contest.

**Auth:** No token required to connect. Authorization is validated per-bid via `user_id` in the message.

```
ws://<domain>/api/bidding/ws/{contest_id}
```

---

### Client → Server Messages

**Place a bid:**
```json
{
  "type": "PLACE_BID",
  "auction_id": "uuid",
  "team_id": "uuid",
  "user_id": "uuid",
  "amount": 350
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"PLACE_BID"` |
| `auction_id` | uuid | Yes | The ID of the active auction |
| `team_id` | uuid | Yes | The bidding team's ID |
| `user_id` | uuid | Yes | Must be the team's `BIDDING`-role member |
| `amount` | int | Yes | Bid amount — must exceed current highest bid |

---

**Manually finish an auction** (organizer override):
```json
{
  "type": "FINISH_AUCTION",
  "auction_id": "uuid"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"FINISH_AUCTION"` |
| `auction_id` | uuid | Yes | The auction to finish |

---

### Server → All Clients Messages

**Auction started** (broadcast when organizer starts a new auction):
```json
{
  "type": "AUCTION_STARTED",
  "auction_id": "uuid",
  "contest_problem_id": "uuid",
  "base_price": 200,
  "start_time": "2026-03-23T10:00:00+05:30",
  "end_time": "2026-03-23T10:01:00+05:30"
}
```

---

**New highest bid** (broadcast after each accepted bid):
```json
{
  "type": "NEW_HIGHEST_BID",
  "team_id": "uuid",
  "amount": 350
}
```

---

**Auction finished** (broadcast when timer expires or FINISH_AUCTION is triggered):
```json
{
  "type": "AUCTION_FINISHED",
  "auction_id": "uuid",
  "winning_team_id": "uuid",
  "winning_bid": 350
}
```

> `winning_team_id` and `winning_bid` are `null` if no bids were placed.

---

### Server → Sender Only

**Error** (sent only to the client that caused the error):
```json
{
  "type": "ERROR",
  "message": "Bid amount must exceed the current highest bid."
}
```

---

> Race conditions are handled server-side via Redis atomic locks (SET NX EX 5). If a lock is held when a bid arrives, the bid is rejected immediately with an `ERROR` message. Only the `BIDDING`-role member of a team may place bids.

---

## System Endpoints

### GET `/health`
Health check.

**Auth required:** No

**Response:**
```json
{ "status": "ok" }
```

---

### GET `/db-check`
Verify database connectivity.

**Auth required:** No

**Response:**
```json
{ "db": 1 }
```

---

## Contest Lifecycle

```
DRAFT → REGISTRATION_OPEN → ACTIVE → ENDED
```

| Transition | Endpoint | Who |
|------------|----------|-----|
| DRAFT → REGISTRATION_OPEN | `POST /contests/{id}/open-registration` | Creator/Organizer |
| REGISTRATION_OPEN → ACTIVE | `POST /contests/{id}/start` | Creator/Organizer |
| ACTIVE → ENDED | `POST /contests/{id}/end` | Creator/Organizer |

Teams can only register when status is `REGISTRATION_OPEN`. Auctions can only be started when status is `ACTIVE`.

---

## Bidding Flow Summary

1. Organizer starts contest (`POST /contests/{id}/start`)
2. All clients connect to WebSocket (`WS /bidding/ws/{contest_id}`)
3. Organizer starts auction for a problem (`POST /bidding/contests/{id}/auctions/start`)
4. Server broadcasts `AUCTION_STARTED` to all WebSocket clients
5. Team's `BIDDING` member places bids via WebSocket (`PLACE_BID`)
6. Server broadcasts `NEW_HIGHEST_BID` to all clients after each accepted bid
7. Auction ends (by timer or manual `FINISH_AUCTION`) → Server broadcasts `AUCTION_FINISHED`
8. Winning team's `CODING` member solves the assigned problem
9. Organizer starts next auction
