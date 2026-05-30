# Database Indexing — Audit & Recommendations

Audit of every index declared in `app/database/models/` against the actual query
patterns found in `app/api/**/dao/`. The goal is two-fold:

1. Catch **missing indexes** on hot read paths (full table scans waiting to bite us in production).
2. Catch **redundant indexes** that double the write cost and waste disk for no gain.

> Note on SQLAlchemy/Postgres behavior used throughout this doc:
> - `mapped_column(..., unique=True)` already creates an implicit unique B-tree index. Adding `index=True` on top is harmless. Adding a *second, explicit* `Index(...)` on the same column is **redundant** — you get two physical indexes for one logical lookup.
> - `UniqueConstraint("a", "b")` creates a composite B-tree on `(a, b)`. Postgres can use it for `WHERE a = ?` (left-most prefix) but **not** for `WHERE b = ?` alone. So a separate index on `b` is needed; a separate index on `a` is redundant.

---

## 1. Currently-applied indexes

| Table | Index / Constraint | Columns | Source |
|---|---|---|---|
| `users` | implicit (PK) | `id` | `users.py:13` |
| `users` | unique + ix | `email` | `users.py:14` |
| `users` | unique + ix | `username` | `users.py:17` |
| `teams` | implicit (PK) | `id` | `teams.py:13` |
| `teams` | implicit unique | `name` | `teams.py:14` |
| `team_members` | implicit (PK) | `id` | `teams.py:40` |
| `team_members` | `uq_team_user` | `(team_id, user_id)` unique | `teams.py:52` |
| `team_members` | `ix_teammember_team_id` | `team_id` | `teams.py:53` |
| `team_members` | `ix_teammember_user_id` | `user_id` | `teams.py:54` |
| `team_join_requests` | `ix_team_join_requests_team_id` | `team_id` | `teams.py:85` |
| `team_join_requests` | `ix_team_join_requests_user_id` | `user_id` | `teams.py:86` |
| `team_join_requests` | `ix_team_join_requests_status` | `status` | `teams.py:87` |
| `contests` | implicit (PK) | `id` | `contests.py:23` |
| `team_contests` | `uq_team_contest` | `(team_id, contest_id)` unique | `contests.py:85` |
| `team_contests` | `ix_teamcontest_team_id` | `team_id` | `contests.py:86` |
| `team_contests` | `ix_teamcontest_contest_id` | `contest_id` | `contests.py:87` |
| `contest_tab_switches` | `uq_contest_tab_switch_contest_user` | `(contest_id, user_id)` unique | `contests.py:102` |
| `contest_tab_switches` | `ix_contest_tab_switches_contest_id` | `contest_id` | `contests.py:103` |
| `builtin_problems` | implicit unique | `slug` | `problems.py:29` |
| `builtin_problems` | `ix_builtin_problem_difficulty` | `difficulty` | `problems.py:73` |
| `builtin_problems` | `ix_builtin_problem_slug` (unique) | `slug` | `problems.py:74` |
| `custom_problems` | `uq_custom_problem_owner_slug` (unique) | `(created_by, slug)` | `problems.py:153` |
| `custom_problems` | `ix_custom_problem_created_by` | `created_by` | `problems.py:159` |
| `custom_problems` | `ix_custom_problem_difficulty` | `difficulty` | `problems.py:160` |
| `contest_problems` | `ck_contest_problem_xor` | check constraint | `problems.py:244` |
| `contest_problems` | `uq_contest_builtin_problem` (partial unique) | `(contest_id, builtin_problem_id)` | `problems.py:254` |
| `contest_problems` | `uq_contest_custom_problem` (partial unique) | `(contest_id, custom_problem_id)` | `problems.py:261` |
| `contest_problems` | `ix_contest_problem_contest_id` | `contest_id` | `problems.py:268` |
| `contest_problems` | `ix_contest_problem_builtin_problem_id` | `builtin_problem_id` | `problems.py:269` |
| `contest_problems` | `ix_contest_problem_custom_problem_id` | `custom_problem_id` | `problems.py:270` |
| `problem_auctions` | `uq_auction_contest_problem` | `contest_problem_id` unique | `bidding.py:66` |
| `problem_auctions` | `ix_auction_contest_id` | `contest_id` | `bidding.py:67` |
| `bids` | `ix_bid_auction_id` | `auction_id` | `bidding.py:107` |
| `contest_problem_assignments` | `uq_assignment_contest_problem` | `contest_problem_id` unique | `bidding.py:144` |
| `contest_problem_assignments` | `ix_assignment_contest_id` | `contest_id` | `bidding.py:145` |
| `contest_problem_assignments` | `ix_assignment_team_id` | `team_id` | `bidding.py:146` |
| `submissions` | `ix_submission_contest_id` | `contest_id` | `submissions.py:98` |
| `submissions` | `ix_submission_team_id` | `team_id` | `submissions.py:99` |
| `submissions` | `ix_submission_assignment_id` | `assignment_id` | `submissions.py:100` |
| `submission_test_results` | `ix_str_submission_id` | `submission_id` | `submissions.py:138` |
| `team_problem_solutions` | `uq_tps_team_problem` | `(team_id, contest_problem_id)` unique | `team_problem_solutions ─ submissions.py:188` |
| `team_problem_solutions` | `ix_tps_contest_id` | `contest_id` | `submissions.py:190` |

---

## 2. Recommended additions

These are FKs / filter columns that the codebase queries against, but where **no index covers the query**. Listed in rough priority order (hottest paths first).

### 2.1 `contests.created_by` — HIGH
Used by `ContestDAO.get_created_by`, `count_created_by`, `get_created_by_paginated`
(`contests/dao/contests.py:64-77, 79-87, 158-170`).

The "My Contests" dashboard for organizers hits this on every page load and there is currently **no index on `contests.created_by`** — it's only a foreign key. As the `contests` table grows this becomes a seq scan per request.

```python
# contests.py table_args
Index("ix_contest_created_by", "created_by"),
```

### 2.2 `contests.status` — HIGH
Used by `get_active`, `count_active`, `get_active_paginated`, plus the lifecycle scheduler that promotes `REGISTRATION_OPEN → ACTIVE → ENDED` and `has_member_in_active_contest` (`contests.py:117-156, 415-435`). Enum has only 4 values so cardinality is low, but the queries always look for `ACTIVE` specifically, and partial indexing makes that nearly free:

```python
Index(
    "ix_contest_status_active",
    "status",
    postgresql_where="status = 'ACTIVE'",
),
```

(A plain `Index("ix_contest_status", "status")` also works and is simpler — pick that if you don't want partial-index complexity in migrations.)

### 2.3 `problem_auctions(contest_id, status)` — HIGH
`BiddingDAO.get_active_auction_for_contest` (`bidding.py:69-83`) runs on every websocket reconnect / auction tick:

```sql
SELECT * FROM problem_auctions
WHERE contest_id = :cid AND status = 'ACTIVE';
```

Currently served by `ix_auction_contest_id` only — Postgres has to scan every auction row for the contest and re-filter on `status`. A composite is a strict win here:

```python
Index("ix_auction_contest_status", "contest_id", "status"),
```

(You can then drop `ix_auction_contest_id` — see §3.)

### 2.4 `submissions(team_id, contest_id)` or `(contest_id, team_id)` composite — HIGH
`list_submissions_for_team_in_contest` (`submissions.py:114-125`) and `get_leaderboard_stats` (`contests/dao/contests.py:482-566`) filter on both columns together. Two single-column indexes work but force a bitmap-and; one composite is faster and lets you drop the redundant per-column index:

```python
Index("ix_submission_contest_team", "contest_id", "team_id"),
```

Pick `(contest_id, team_id)` over `(team_id, contest_id)` because the leaderboard query also filters by `contest_id` alone in `get_leaderboard_stats`, so the composite covers both shapes.

### 2.5 `submissions.contest_problem_id` — MEDIUM
`get_leaderboard_stats` selects `(team_id, contest_problem_id)` distinct (`contests.py:542-562`). The `contest_problem_id` FK is currently unindexed. The composite from §2.4 doesn't help here because the WHERE is on `contest_id`, but if you ever query "all submissions for a single contest problem" (e.g. an organizer's per-problem analytics view) you'll seq-scan. Cheap to add:

```python
Index("ix_submission_contest_problem_id", "contest_problem_id"),
```

Defer until you actually have such a query — for now this is "FK hygiene", not a hot path.

### 2.6 `team_problem_solutions(team_id, contest_problem_id)` lookup
Already covered by `uq_tps_team_problem` — **no action needed**. Noted here so it's not flagged as missing.

### 2.7 FK hygiene (low priority, add only if a query appears)
These columns are foreign keys with no index. Postgres does **not** auto-index FKs. Today nothing hot queries them, but `ON DELETE CASCADE` will table-scan on each parent delete, and ad-hoc analytics will be slow:

- `teams.created_by`
- `problem_auctions.winning_team_id`
- `bids.team_id`, `bids.user_id`
- `submissions.user_id`
- `team_problem_solutions.last_submission_id`

Recommendation: leave them alone for now and revisit if a query path emerges or if cascade-delete latency becomes visible.

---

## 3. Recommended removals (redundant indexes)

Every index costs write throughput and disk; duplicates cost both with zero benefit.

### 3.1 `ix_builtin_problem_slug` — DROP
`builtin_problems.slug` already has `unique=True` on the column declaration (`problems.py:29`), which creates an implicit unique index. The explicit `Index("ix_builtin_problem_slug", "slug", unique=True)` at `problems.py:74` creates a **second** unique index on the same column.

**Action:** remove line `problems.py:74`.

### 3.2 `ix_teammember_team_id` — DROP
`team_members` has `UniqueConstraint("team_id", "user_id")` (`teams.py:52`). Postgres can serve `WHERE team_id = ?` via the left-most prefix of that composite index. The standalone `ix_teammember_team_id` is redundant.

`ix_teammember_user_id` must be **kept** — `user_id` is the second column of the composite and is not covered by left-most prefix.

### 3.3 `ix_teamcontest_team_id` — DROP
Same story as 3.2: `uq_team_contest` is `(team_id, contest_id)` (`contests.py:85`), so `WHERE team_id = ?` is already covered. `ix_teamcontest_contest_id` is **kept** for the symmetric case.

### 3.4 `ix_contest_tab_switches_contest_id` — DROP
`uq_contest_tab_switch_contest_user` is `(contest_id, user_id)` (`contests.py:102`). Left-most prefix already covers `WHERE contest_id = ?` (used by `get_tab_switches_for_contest`).

### 3.5 `ix_auction_contest_id` — DROP **only if §2.3 is applied**
If you add the composite `(contest_id, status)`, the contest-only queries (`get_all_auctions_for_contest`, `get_latest_auction_for_contest`) still hit the left-most prefix. Drop the standalone after the composite ships, not before.

### 3.6 Do **not** drop these even though they look redundant
- `ix_contest_problem_contest_id` — the two `uq_contest_*_problem` indexes are **partial** (`postgresql_where = "... IS NOT NULL"`), so Postgres can't use them for an unqualified `WHERE contest_id = ?`. Standalone is required.
- `ix_contest_problem_builtin_problem_id` / `ix_contest_problem_custom_problem_id` — the partial unique indexes have `contest_id` as the left-most column, so they can't serve `WHERE builtin_problem_id = ?` queries.
- `ix_assignment_team_id` — `uq_assignment_contest_problem` is on `contest_problem_id` only and doesn't cover `team_id` lookups.

---

## 4. Quick scorecard

| Severity | Action | Index |
|---|---|---|
| HIGH | ADD | `ix_contest_created_by` on `contests.created_by` |
| HIGH | ADD | `ix_contest_status` on `contests.status` (or partial on `ACTIVE`) |
| HIGH | ADD | `ix_auction_contest_status` on `problem_auctions(contest_id, status)` |
| HIGH | ADD | `ix_submission_contest_team` on `submissions(contest_id, team_id)` |
| MED  | ADD | `ix_submission_contest_problem_id` on `submissions.contest_problem_id` (defer until queried) |
| LOW  | ADD | FK indexes on `teams.created_by`, `bids.team_id/user_id`, `submissions.user_id`, etc. (only if cascade-delete or analytics need them) |
| MED  | DROP | `ix_builtin_problem_slug` (duplicate of implicit unique) |
| MED  | DROP | `ix_teammember_team_id` (covered by `uq_team_user`) |
| MED  | DROP | `ix_teamcontest_team_id` (covered by `uq_team_contest`) |
| MED  | DROP | `ix_contest_tab_switches_contest_id` (covered by `uq_contest_tab_switch_contest_user`) |
| LOW  | DROP | `ix_auction_contest_id` — only after `ix_auction_contest_status` ships |

---

## 5. Migration sketch

Order the migration carefully: add the replacements first, then drop the originals, so reads stay fast across the upgrade window.

```python
"""add hot-path indexes, drop redundant ones"""

from alembic import op

def upgrade():
    # --- Additions ---
    op.create_index("ix_contest_created_by", "contests", ["created_by"])
    op.create_index("ix_contest_status", "contests", ["status"])
    op.create_index(
        "ix_auction_contest_status",
        "problem_auctions",
        ["contest_id", "status"],
    )
    op.create_index(
        "ix_submission_contest_team",
        "submissions",
        ["contest_id", "team_id"],
    )

    # --- Removals (run AFTER additions so no read path regresses) ---
    op.drop_index("ix_builtin_problem_slug", table_name="builtin_problems")
    op.drop_index("ix_teammember_team_id", table_name="team_members")
    op.drop_index("ix_teamcontest_team_id", table_name="team_contests")
    op.drop_index(
        "ix_contest_tab_switches_contest_id",
        table_name="contest_tab_switches",
    )
    op.drop_index("ix_auction_contest_id", table_name="problem_auctions")


def downgrade():
    op.create_index("ix_auction_contest_id", "problem_auctions", ["contest_id"])
    op.create_index(
        "ix_contest_tab_switches_contest_id",
        "contest_tab_switches",
        ["contest_id"],
    )
    op.create_index("ix_teamcontest_team_id", "team_contests", ["team_id"])
    op.create_index("ix_teammember_team_id", "team_members", ["team_id"])
    op.create_index(
        "ix_builtin_problem_slug",
        "builtin_problems",
        ["slug"],
        unique=True,
    )

    op.drop_index("ix_submission_contest_team", table_name="submissions")
    op.drop_index("ix_auction_contest_status", table_name="problem_auctions")
    op.drop_index("ix_contest_status", table_name="contests")
    op.drop_index("ix_contest_created_by", table_name="contests")
```

Remember to mirror the changes in the model `__table_args__` blocks; otherwise the next autogenerated migration will try to re-create what you dropped.

For Postgres in production, prefer `CREATE INDEX CONCURRENTLY` (use `op.create_index(..., postgresql_concurrently=True)` and set `transaction_per_migration = False`) so the migration doesn't take an `ACCESS EXCLUSIVE` lock on hot tables.

---

## 6. Validation checklist

After applying:

1. `make migrate` then `\d+ <table>` in psql to confirm the index set.
2. `EXPLAIN (ANALYZE, BUFFERS)` against the four HIGH queries in §2 and confirm the planner picks the new index.
3. Re-run autogen (`make migration m="check"`) and confirm it produces an **empty** migration — proves the model and DB are in sync.
