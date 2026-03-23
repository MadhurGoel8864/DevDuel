# Frontend Implementation Guide — Contest Organizer Feature

This document describes backend changes that require corresponding frontend updates.
It is intended for an AI agent or developer implementing the frontend side of the `is_organizer` feature.

---

## What Changed

A new boolean field `is_organizer` has been added to users.

- Default value: `false`
- Set by admins via the database (no self-service promotion)
- **Only users with `is_organizer: true` can create and manage contests**
- All other users get a `403 Forbidden` if they attempt those actions

---

## Where `is_organizer` Appears

### 1. JWT Access Token Payload
After login or token refresh, decode the JWT. The payload now includes:

```json
{
  "sub": "uuid",
  "email": "user@example.com",
  "is_organizer": false,
  "type": "access",
  "jti": "uuid",
  "exp": 1234567890
}
```

You can decode the JWT client-side (without verification) to read `is_organizer` without an extra API call. Use any JWT decode library (e.g. `jwt-decode` for JS/TS).

### 2. `GET /api/auth/me` Response
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "role": "user",
    "permissions": [],
    "is_active": true,
    "is_verified": true,
    "is_organizer": false,
    "profile_img_url": null,
    "last_login_at": "2026-03-23T10:00:00+05:30"
  }
}
```

### 3. `GET /api/users/{user_id}` Response
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
    "created_at": "...",
    "updated_at": "..."
  }
}
```

---

## Endpoints That Now Require `is_organizer: true`

These endpoints return `403 Forbidden` for users with `is_organizer: false`.

| Method | Endpoint | Action |
|--------|----------|--------|
| `POST` | `/api/contests` | Create a contest |
| `PATCH` | `/api/contests/{contest_id}` | Edit a contest |
| `POST` | `/api/contests/{contest_id}/open-registration` | Open registration |
| `POST` | `/api/contests/{contest_id}/start` | Start contest |
| `POST` | `/api/contests/{contest_id}/end` | End contest |

**Error response for non-organizers (HTTP 403):**
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Only organizers are allowed to perform this action"
  }
}
```

---

## Reading `is_organizer` — Recommended Approach

**Option A — Decode from JWT (fastest, no extra request):**
```js
import { jwtDecode } from "jwt-decode";

const token = localStorage.getItem("access_token");
const payload = jwtDecode(token);
const isOrganizer = payload.is_organizer ?? false;
```

**Option B — Read from `/auth/me` (most up-to-date):**
```js
const res = await fetch("/api/auth/me", {
  headers: { Authorization: `Bearer ${token}` }
});
const { data } = await res.json();
const isOrganizer = data.is_organizer;
```

> Prefer Option B if you already call `/auth/me` on app load to hydrate the user store, since `is_organizer` is there. Option A is fine for quick gate checks.

---

## Required UI Changes

### 1. Hide "Create Contest" button/page for non-organizers
Show the **Create Contest** button/link only when `is_organizer === true`.

```jsx
{user.is_organizer && <Button onClick={goToCreateContest}>Create Contest</Button>}
```

If a non-organizer navigates to the create contest page directly (e.g. via URL), redirect them away or show a "You don't have permission" message.

### 2. Hide contest management controls for non-organizers
On the contest detail page, these controls should only be visible when `is_organizer === true` **AND** the current user is the contest creator (`contest.created_by === user.user_id`):

- Edit contest button / form
- "Open Registration" button
- "Start Contest" button
- "End Contest" button

```jsx
const canManage = user.is_organizer && contest.created_by === user.user_id;

{canManage && <Button onClick={openRegistration}>Open Registration</Button>}
{canManage && <Button onClick={startContest}>Start Contest</Button>}
{canManage && <Button onClick={endContest}>End Contest</Button>}
```

### 3. Handle 403 errors gracefully
Even with UI guards, always handle the `403` response in your API layer:

```js
if (response.status === 403) {
  showToast("You don't have permission to perform this action.");
  return;
}
```

### 4. Store `is_organizer` in your auth/user state
Add `is_organizer` to wherever you store the current user (Redux, Zustand, Context, etc.).

```ts
interface CurrentUser {
  user_id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  is_organizer: boolean;   // <-- add this
  profile_img_url: string | null;
}
```

Set it when:
- User logs in (decode from JWT or from `/auth/me`)
- App loads and re-hydrates session (read from `/auth/me`)
- Token is refreshed (re-decode the new JWT or re-call `/auth/me`)

---

## Navigation / Route Guards

Protect the **Create Contest** route:

```jsx
// React Router example
<Route
  path="/contests/new"
  element={
    user.is_organizer
      ? <CreateContestPage />
      : <Navigate to="/contests" replace />
  }
/>
```

---

## Summary Checklist

- [ ] Add `is_organizer: boolean` to the current user type/interface
- [ ] Populate `is_organizer` from JWT payload or `/auth/me` on login and app load
- [ ] Re-read `is_organizer` after token refresh
- [ ] Hide "Create Contest" button when `is_organizer === false`
- [ ] Guard the Create Contest route (redirect non-organizers)
- [ ] Show contest lifecycle controls (open registration, start, end, edit) only when `is_organizer === true && contest.created_by === user.user_id`
- [ ] Handle `403 FORBIDDEN` responses from the five contest management endpoints
