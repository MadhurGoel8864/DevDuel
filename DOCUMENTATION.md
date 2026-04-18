# DevDuel — Project Documentation

> A competitive coding platform where two-person teams compete in real-time bidding + coding contests.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [How It Works](#how-it-works)
5. [Database Schema](#database-schema)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
# Update

---

## Project Overview

**DevDuel** is a real-time competitive programming platform built around a unique team format:

- Teams consist of **two members** with distinct roles — a **Bidder** and a **Coder**.
- Contests have a set of coding problems, each with a `base_price`.
- During a contest, teams **bid currency** to acquire problems using their assigned `currency` budget.
- After bidding, the **Coder** solves the problems the team acquired; earned `points` are tracked on a leaderboard.
- Contests go through a lifecycle: `DRAFT → REGISTRATION_OPEN → ACTIVE → ENDED`.

---

## Tech Stack

| Layer          | Technology                                          |
| -------------- | --------------------------------------------------- |
| Language       | Python 3.12+                                        |
| Web Framework  | FastAPI (async)                                     |
| ORM            | SQLAlchemy 2 (async, with `asyncpg`)                |
| Database       | PostgreSQL                                          |
| Cache / OTP    | Redis                                               |
| Auth           | JWT (access + refresh tokens), Google OAuth 2.0     |
| Migrations     | Alembic                                             |
| Validation     | Pydantic v2                                         |
| Email          | SMTP (Gmail)                                        |
| Package Mgr    | Poetry                                              |

---

## Architecture

```
app/
├── main.py                 # App factory: registers middleware, exception handlers, router
├── api/
│   ├── main.py             # Central APIRouter (/api prefix), mounts all sub-routers
│   ├── auth/               # Authentication & OAuth module
│   ├── users/              # User CRUD module
│   ├── teams/              # Team management module
│   ├── contests/           # Contest lifecycle module
│   ├── problems/           # Problems & contest-problem mapping module
│   └── bidding/            # (In progress) Bidding logic module
├── core/
│   ├── config.py           # Pydantic settings (env vars)
│   ├── enums.py            # Shared enumerations
│   ├── database.py         # Async SQLAlchemy session factory
│   ├── redis.py            # Redis client setup
│   ├── security/           # JWT utilities
│   ├── middleware/         # RequestID & RequestLogging middlewares
│   └── exception_handlers.py
├── database/
│   ├── models/             # SQLAlchemy ORM models (single source of truth for schema)
│   └── utils.py            # UUID generator helper
└── services/               # Shared / cross-cutting services (e.g., email)
```

Each API module follows a strict **4-layer pattern**:

```
routes.py  →  handlers.py  →  services.py  →  dao.py  →  DB
```

| Layer        | Responsibility                                            |
| ------------ | --------------------------------------------------------- |
| **Routes**   | Declare HTTP method + path, wire to handler               |
| **Handlers** | Parse request, call service, return HTTP response         |
| **Services** | Business logic, orchestration, calls DAO                  |
| **DAO**      | Raw database queries (SQLAlchemy async)                   |

---

## How It Works

### 1. User Registration & Verification

1. User registers via `POST /api/users` — account created with `is_verified = False`.
2. An OTP is sent to their email (`POST /api/auth/send-otp`).
3. User verifies the OTP via `POST /api/auth/verify-otp` → `is_verified = True`.
4. User logs in via `POST /api/auth/login` → receives `access_token` + `refresh_token`.

### 2. Google OAuth

1. Client requests login URL via `GET /api/auth/google/login` — receives Google OAuth URL with secure state token.
2. After Google redirects, `GET /api/auth/google/callback` validates state and issues JWT tokens.

### 3. Team Formation

1. A user creates a team via `POST /api/teams` — the creator auto-joins with `BIDDING` role.
2. Another user is added via `POST /api/teams/{team_id}/members` — they join with `CODING` role.
3. The two roles (`BIDDING`, `CODING`) can be swapped via `POST /api/teams/{team_id}/members/swap-roles`.
4. Exactly one team member must be the **Bidder** and one must be the **Coder**.

### 4. Contest Lifecycle

| Status              | Meaning                                               |
| ------------------- | ----------------------------------------------------- |
| `DRAFT`             | Contest created, not visible for registration yet     |
| `REGISTRATION_OPEN` | Teams can join the contest                            |
| `ACTIVE`            | Contest is live; bidding and coding happen            |
| `ENDED`             | Contest over; leaderboard is finalised                |

Transitions (admin-only):
- `DRAFT → REGISTRATION_OPEN`: `POST /api/contests/{id}/open-registration`
- `REGISTRATION_OPEN → ACTIVE`: `POST /api/contests/{id}/start`
- `ACTIVE → ENDED`: `POST /api/contests/{id}/end`

### 5. Problem Bidding & Scoring

- Problems are added to a contest via `POST /api/contests/{contest_id}/problems`.
- Each `ContestProblem` has a `problem_order` (the sequence for bidding) and `is_active` flag.
- Each `TeamContest` entry starts with **1000 currency** units.
- During an `ACTIVE` contest, the **Bidder** spends currency to claim problems.
- Successfully solving a problem awards the problem's `points` to the team's `score`.
- Final standings are exposed via `GET /api/contests/{id}/teams` (leaderboard).

### 6. Token Management

- **Access token**: Short-lived (30 min by default). Sent as `Bearer` in `Authorization` header.
- **Refresh token**: Long-lived. Stored and rotated on each `POST /api/auth/refresh`.
- **Logout**: `POST /api/auth/logout` blacklists the refresh token in Redis.
- **Password reset**: Stateless token sent by email; consumed once via `POST /api/auth/reset-password`.

---

## Database Schema

> All tables use UUIDs (String 36) as primary keys. Timestamps are in IST (Asia/Kolkata). Most tables include `created_at` and `updated_at` via `TimestampMixin`.

---

### `users`

Stores all registered users regardless of auth provider.

| Column               | Type         | Constraints                   | Default   | Description                              |
| -------------------- | ------------ | ----------------------------- | --------- | ---------------------------------------- |
| `id`                 | VARCHAR(36)  | PK                            | UUID      | Primary key                              |
| `email`              | VARCHAR(255) | UNIQUE, NOT NULL, indexed     | —         | User email address                       |
| `username`           | VARCHAR(50)  | UNIQUE, NOT NULL, indexed     | —         | Display username                         |
| `role`               | VARCHAR(20)  | NOT NULL                      | `user`    | `user` \| `organizer` \| `admin`         |
| `full_name`          | VARCHAR(255) | nullable                      | —         | Optional display name                    |
| `password_hash`      | VARCHAR(255) | nullable                      | —         | `NULL` for OAuth users                   |
| `is_active`          | BOOLEAN      | NOT NULL                      | `true`    | Whether account is active                |
| `is_verified`        | BOOLEAN      | NOT NULL                      | `false`   | Email verified via OTP                   |
| `auth_provider`      | VARCHAR(50)  | NOT NULL                      | `local`   | `local` \| `google` \| `apple`           |
| `provider_user_id`   | VARCHAR(255) | nullable                      | —         | External OAuth user ID                   |
| `last_login_at`      | TIMESTAMPTZ  | nullable                      | —         | Last successful login                    |
| `email_verified_at`  | TIMESTAMPTZ  | nullable                      | —         | When email was verified                  |
| `profile_img_url`    | VARCHAR(512) | nullable                      | —         | Avatar URL                               |
| `password_updated_at`| TIMESTAMPTZ  | nullable                      | —         | Last password change                     |
| `created_at`         | TIMESTAMPTZ  | NOT NULL                      | now()     | Row creation time                        |
| `updated_at`         | TIMESTAMPTZ  | NOT NULL                      | now()     | Row last updated                         |

---

### `teams`

A competitive unit of exactly 2 members.

| Column       | Type        | Constraints       | Default | Description                       |
| ------------ | ----------- | ----------------- | ------- | --------------------------------- |
| `id`         | VARCHAR(36) | PK                | UUID    | Primary key                       |
| `name`       | VARCHAR(100)| UNIQUE, NOT NULL  | —       | Unique team name                  |
| `created_by` | VARCHAR(36) | FK → `users.id`   | —       | Team creator (CASCADE delete)     |
| `created_at` | TIMESTAMPTZ | NOT NULL          | now()   |                                   |
| `updated_at` | TIMESTAMPTZ | NOT NULL          | now()   |                                   |

---

### `team_members`

Junction table linking a user to a team with an assigned role.

| Column     | Type        | Constraints                  | Description                                  |
| ---------- | ----------- | ---------------------------- | -------------------------------------------- |
| `id`       | VARCHAR(36) | PK                           | Primary key                                  |
| `team_id`  | VARCHAR(36) | FK → `teams.id`, indexed     | Parent team (CASCADE delete)                 |
| `user_id`  | VARCHAR(36) | FK → `users.id`, indexed     | Member user (CASCADE delete)                 |
| `role`     | ENUM        | NOT NULL                     | `BIDDING` or `CODING`                        |
| `created_at`| TIMESTAMPTZ| NOT NULL                     |                                              |
| `updated_at`| TIMESTAMPTZ| NOT NULL                     |                                              |

**Constraints**: `UNIQUE(team_id, user_id)` — a user can only appear once per team.

---

### `contests`

A timed competitive event.

| Column        | Type        | Constraints             | Default   | Description                              |
| ------------- | ----------- | ----------------------- | --------- | ---------------------------------------- |
| `id`          | VARCHAR(36) | PK                      | UUID      | Primary key                              |
| `name`        | VARCHAR(100)| NOT NULL                | —         | Contest display name                     |
| `description` | VARCHAR(255)| nullable                | —         | Optional description                     |
| `start_time`  | TIMESTAMPTZ | NOT NULL                | —         | Scheduled start time                     |
| `end_time`    | TIMESTAMPTZ | NOT NULL                | —         | Scheduled end time                       |
| `created_by`  | VARCHAR(36) | FK → `users.id`         | —         | Organizer (CASCADE delete)               |
| `status`      | ENUM        | NOT NULL                | `DRAFT`   | `DRAFT` \| `REGISTRATION_OPEN` \| `ACTIVE` \| `ENDED` |
| `created_at`  | TIMESTAMPTZ | NOT NULL                | now()     |                                          |
| `updated_at`  | TIMESTAMPTZ | NOT NULL                | now()     |                                          |

---

### `team_contests`

Records a team's participation in a contest, including their budget and score.

| Column       | Type        | Constraints                    | Default | Description                        |
| ------------ | ----------- | ------------------------------ | ------- | ---------------------------------- |
| `id`         | VARCHAR(36) | PK                             | UUID    | Primary key                        |
| `team_id`    | VARCHAR(36) | FK → `teams.id`, indexed       | —       | Participating team (CASCADE delete)|
| `contest_id` | VARCHAR(36) | FK → `contests.id`, indexed    | —       | Target contest (CASCADE delete)    |
| `currency`   | INTEGER     | NOT NULL                       | `1000`  | Remaining bidding budget           |
| `score`      | INTEGER     | NOT NULL                       | `0`     | Accumulated problem points         |
| `created_at` | TIMESTAMPTZ | NOT NULL                       | now()   |                                    |
| `updated_at` | TIMESTAMPTZ | NOT NULL                       | now()   |                                    |

**Constraints**: `UNIQUE(team_id, contest_id)` — a team can only join a contest once.

---

### `problems`

A reusable coding problem that can be assigned to multiple contests.

| Column            | Type        | Constraints              | Default | Description                                   |
| ----------------- | ----------- | ------------------------ | ------- | --------------------------------------------- |
| `id`              | VARCHAR(36) | PK                       | UUID    | Primary key                                   |
| `title`           | VARCHAR(255)| NOT NULL                 | —       | Problem title                                 |
| `slug`            | VARCHAR(300)| UNIQUE, NOT NULL, indexed| —       | URL-safe unique identifier                    |
| `description`     | TEXT        | NOT NULL                 | —       | Full problem statement (Markdown)             |
| `difficulty`      | ENUM        | NOT NULL                 | —       | `easy` \| `medium` \| `hard`                 |
| `points`          | INTEGER     | NOT NULL                 | —       | Points awarded on solve                       |
| `base_price`      | INTEGER     | NOT NULL                 | —       | Minimum bid currency required                 |
| `time_limit_ms`   | INTEGER     | NOT NULL                 | `2000`  | Execution time limit (milliseconds)           |
| `memory_limit_mb` | INTEGER     | NOT NULL                 | `256`   | Memory limit (megabytes)                      |
| `created_by`      | VARCHAR(36) | FK → `users.id`          | —       | Problem author (CASCADE delete)               |
| `is_active`       | BOOLEAN     | NOT NULL                 | `true`  | Soft toggle for visibility                    |
| `created_at`      | TIMESTAMPTZ | NOT NULL                 | now()   |                                               |
| `updated_at`      | TIMESTAMPTZ | NOT NULL                 | now()   |                                               |

**Indexes**: `ix_problem_difficulty`, `ix_problem_slug` (unique)

---

### `contest_problems`

Maps a problem to a specific contest, with an ordering for the bidding sequence.

| Column          | Type        | Constraints                         | Default | Description                            |
| --------------- | ----------- | ----------------------------------- | ------- | -------------------------------------- |
| `id`            | VARCHAR(36) | PK                                  | UUID    | Primary key                            |
| `contest_id`    | VARCHAR(36) | FK → `contests.id`, indexed         | —       | Parent contest (CASCADE delete)        |
| `problem_id`    | VARCHAR(36) | FK → `problems.id`, indexed         | —       | Linked problem (CASCADE delete)        |
| `problem_order` | INTEGER     | NOT NULL                            | —       | Bidding turn order within the contest  |
| `is_active`     | BOOLEAN     | NOT NULL                            | `true`  | Include/exclude without removing       |
| `created_at`    | TIMESTAMPTZ | NOT NULL                            | now()   |                                        |

**Constraints**:
- `UNIQUE(contest_id, problem_id)` — a problem appears at most once per contest.
- `UNIQUE(contest_id, problem_order)` — no two problems share the same order in a contest.

---

### Entity Relationship Diagram

```
users
 ├──< teams (created_by)
 ├──< team_members (user_id)
 ├──< contests (created_by)
 └──< problems (created_by)

teams
 ├──< team_members
 └──< team_contests

contests
 ├──< team_contests
 └──< contest_problems

problems
 └──< contest_problems
```

---

## API Reference

> Base URL: `/api`  
> Authentication: `Authorization: Bearer <access_token>` (where required)

### Auth — `/api/auth`

| Method | Endpoint              | Description                                          |
| ------ | --------------------- | ---------------------------------------------------- |
| POST   | `/login`              | Email/password login → `access_token + refresh_token`|
| POST   | `/logout`             | Blacklist refresh token (Redis)                      |
| POST   | `/refresh`            | Exchange refresh token → new tokens                  |
| POST   | `/verify-otp`         | Verify email OTP → marks account as verified         |
| GET    | `/me`                 | Get authenticated user's profile                     |
| POST   | `/forgot-password`    | Request password reset email                         |
| POST   | `/reset-password`     | Complete password reset with token                   |
| POST   | `/resend-otp`         | Resend verification OTP                              |

### OAuth — `/api/auth/google`

| Method | Endpoint    | Description                                           |
| ------ | ----------- | ----------------------------------------------------- |
| GET    | `/login`    | Get Google OAuth authorization URL + state token      |
| GET    | `/callback` | Handle Google callback; return JWT tokens             |

### Users — `/api/users`

| Method | Endpoint        | Description               |
| ------ | --------------- | ------------------------- |
| POST   | `/`             | Register a new user        |
| GET    | `/{user_id}`    | Get a user's public profile|
| GET    | `/`             | List all users *(temp)*   |

### Teams — `/api/teams`

| Method | Endpoint                           | Description                                |
| ------ | ---------------------------------- | ------------------------------------------ |
| POST   | `/`                                | Create a new team                          |
| GET    | `/me`                              | Get teams for the authenticated user       |
| GET    | `/{team_id}`                       | Get team details                           |
| DELETE | `/{team_id}`                       | Delete a team                              |
| POST   | `/{team_id}/members`               | Add a member to team                       |
| DELETE | `/{team_id}/members/{user_id}`     | Remove a member from team                  |
| POST   | `/{team_id}/members/swap-roles`    | Swap BIDDING ↔ CODING roles               |
| GET    | `/{team_id}/status`                | Get team status info                       |
| GET    | `/{team_id}/my-role`               | Get the authenticated user's role in team  |
| GET    | `/{team_id}/can-join/{contest_id}` | Check if team can register for a contest   |

### Contests — `/api/contests`

| Method | Endpoint                          | Description                                 |
| ------ | --------------------------------- | ------------------------------------------- |
| POST   | `/`                               | Create a new contest (organizer/admin)       |
| GET    | `/`                               | List all contests                           |
| GET    | `/active`                         | List currently active contests              |
| GET    | `/me`                             | List contests the authenticated user is in  |
| GET    | `/{contest_id}`                   | Get contest details                         |
| POST   | `/{contest_id}/register`          | Register a team to a contest                |
| GET    | `/{contest_id}/teams`             | Leaderboard — teams ranked by score         |
| GET    | `/{contest_id}/teams/{team_id}`   | Get a specific team's contest entry         |
| POST   | `/{contest_id}/open-registration` | Transition: DRAFT → REGISTRATION_OPEN       |
| POST   | `/{contest_id}/start`             | Transition: REGISTRATION_OPEN → ACTIVE      |
| POST   | `/{contest_id}/end`               | Transition: ACTIVE → ENDED                  |

### Problems — `/api/problems`

| Method | Endpoint          | Description                     |
| ------ | ----------------- | ------------------------------- |
| POST   | `/`               | Create a new problem             |
| GET    | `/`               | List all problems                |
| GET    | `/{problem_id}`   | Get problem details              |
| PUT    | `/{problem_id}`   | Update a problem                 |
| DELETE | `/{problem_id}`   | Delete a problem                 |

### Contest Problems — `/api/contests/{contest_id}/problems`

| Method | Endpoint                      | Description                              |
| ------ | ----------------------------- | ---------------------------------------- |
| POST   | `/`                           | Add a problem to a contest               |
| GET    | `/`                           | List all problems in a contest (ordered) |
| DELETE | `/{contest_problem_id}`       | Remove a problem from a contest          |

### System

| Method | Endpoint    | Description              |
| ------ | ----------- | ------------------------ |
| GET    | `/health`   | Health check             |
| GET    | `/db-check` | Database connectivity check |

---

## Configuration

All configuration is loaded from the `.env` file via Pydantic settings.

| Variable                   | Description                                      | Default              |
| -------------------------- | ------------------------------------------------ | -------------------- |
| `APP_NAME`                 | Application name                                 | `DevDual`            |
| `DEBUG`                    | Debug mode                                       | `false`              |
| `ENV`                      | Environment (`development`/`production`)          | `development`        |
| `ALLOWED_ORIGINS`          | Pipe-separated CORS origins                      | `http://localhost:3000` |
| `SECRET_KEY`               | App secret (fallback JWT secret)                 | *(required)*         |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token TTL                         | `30`                 |
| `JWT_SECRET_KEY`           | Dedicated JWT signing secret                     | Falls back to `SECRET_KEY` |
| `JWT_ALGORITHM`            | JWT algorithm                                    | `HS256`              |
| `DB_HOST`                  | PostgreSQL host                                  | *(required)*         |
| `DB_PORT`                  | PostgreSQL port                                  | *(required)*         |
| `DB_NAME`                  | PostgreSQL database name                         | *(required)*         |
| `DB_USER`                  | PostgreSQL user                                  | *(required)*         |
| `DB_PASSWORD`              | PostgreSQL password                              | *(required)*         |
| `REDIS_HOST`               | Redis host                                       | `localhost`          |
| `REDIS_PORT`               | Redis port                                       | `6379`               |
| `REDIS_DB`                 | Redis database number                            | `0`                  |
| `OTP_EXPIRE_SECONDS`       | OTP TTL in Redis                                 | `300` (5 min)        |
| `SMTP_HOST`                | SMTP server                                      | `smtp.gmail.com`     |
| `SMTP_PORT`                | SMTP port                                        | `587`                |
| `SMTP_USERNAME`            | SMTP login                                       | *(empty)*            |
| `SMTP_PASSWORD`            | SMTP password                                    | *(empty)*            |
| `EMAIL_FROM`               | From address for emails                          | *(empty)*            |
| `GOOGLE_CLIENT_ID`         | Google OAuth client ID                           | *(required)*         |
| `GOOGLE_CLIENT_SECRET`     | Google OAuth client secret                       | *(required)*         |
| `GOOGLE_REDIRECT_URI`      | OAuth callback URL                               | *(required)*         |

---

*Generated on 2026-03-11*
