"""Seed script: insert Two Sum and Aggressive Cows into builtin_problems,
then upload their test cases to GCS.

Run from backend/DevDuel/ after applying migrations:
    python scripts/seed_two_sum_and_aggressive_cows.py

Idempotent — skips a problem whose slug already exists and already has
test_cases_url set. Re-uploads test cases if the row exists but the URL
is missing.
"""

import asyncio
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database.models.problems import BuiltinProblem  # noqa: E402
from app.database.utils import generate_uuid  # noqa: E402
from app.services.storage import storage_service  # noqa: E402
from app.services.storage.gcs import StorageError  # noqa: E402

engine = create_async_engine(settings.DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _tc(input_: str, expected_output: str, is_sample: bool = False) -> dict[str, Any]:
    return {"input": input_, "expected_output": expected_output, "is_sample": is_sample}


# ── Problem definitions ────────────────────────────────────────────────────────

PROBLEMS: list[dict[str, Any]] = [
    {
        "title": "Two Sum",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given an array of integers `nums` and an integer `target`, return the **indices** "
            "of the two numbers that add up to `target`.\n\n"
            "You may assume that each input has **exactly one solution**, and you may not use "
            "the same element twice. You can return the answer in any order."
        ),
        "input_format": (
            "- First line: two integers `n` and `target` — the length of the array and the target sum.\n"
            "- Second line: `n` space-separated integers representing `nums`."
        ),
        "output_format": (
            "Print two space-separated **0-indexed** integers `i j` such that "
            "`nums[i] + nums[j] == target` and `i < j`."
        ),
        "constraints": (
            "- `2 ≤ n ≤ 10^4`\n"
            "- `-10^9 ≤ nums[i] ≤ 10^9`\n"
            "- `-10^9 ≤ target ≤ 10^9`\n"
            "- Exactly one valid answer exists."
        ),
        # Test case answers verified manually.
        # nums indices are 0-based; output is always "i j" with i < j.
        "test_cases": [
            # samples
            _tc("4 9\n2 7 11 15",            "0 1",  is_sample=True),   # 2+7=9
            _tc("3 6\n3 2 4",                "1 2",  is_sample=True),   # 2+4=6
            _tc("2 6\n3 3",                  "0 1",  is_sample=True),   # 3+3=6
            # hidden
            _tc("2 0\n0 0",                  "0 1"),                    # 0+0=0
            _tc("5 10\n1 2 3 4 6",           "3 4"),                    # 4+6=10
            _tc("5 -3\n-1 -2 0 1 2",         "0 1"),                    # -1+(-2)=-3
            _tc("4 1\n-3 4 1 2",             "0 1"),                    # -3+4=1
            _tc("6 100\n10 20 30 40 50 60",  "3 5"),                    # 40+60=100
            _tc("3 -6\n-3 -3 5",             "0 1"),                    # -3+(-3)=-6; wait: -3+(-3)=-6 ✓ → "0 1"
            _tc("4 200\n100 50 150 75",       "1 2"),                    # 50+150=200
            _tc("5 0\n-4 2 -2 3 1",          "1 2"),                    # 2+(-2)=0
            _tc("2 1000000000\n1 999999999", "0 1"),                    # 1+999999999=10^9
            _tc("5 7\n0 4 3 7 5",            "1 2"),                    # 4+3=7
            _tc("6 15\n5 3 9 2 8 6",         "2 5"),                    # 9+6=15
            _tc("4 -1\n-5 3 4 -6",           "0 2"),                    # -5+4=-1
        ],
    },
    {
        "title": "Aggressive Cows",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Farmer John has built `N` stalls at distinct positions along a straight line. "
            "He wants to place `C` cows in `C` of these stalls.\n\n"
            "The cows are aggressive and don't like being close to each other, so Farmer John "
            "wants to **maximize** the **minimum distance** between any two cows.\n\n"
            "Help Farmer John determine this maximum possible minimum distance."
        ),
        "input_format": (
            "- First line: two integers `N` and `C` — the number of stalls and the number of cows.\n"
            "- Second line: `N` space-separated integers representing stall positions "
            "(not necessarily sorted)."
        ),
        "output_format": (
            "Print a single integer — the largest minimum distance between any two cows "
            "when placed optimally."
        ),
        "constraints": (
            "- `2 ≤ C ≤ N ≤ 10^5`\n"
            "- `0 ≤ stall position ≤ 10^9`\n"
            "- All stall positions are distinct."
        ),
        # Answers verified by binary-search simulation on sorted stall arrays.
        "test_cases": [
            # samples
            _tc("5 3\n1 2 8 4 9",                    "3",   is_sample=True),
            _tc("3 2\n0 10 5",                        "10",  is_sample=True),
            # hidden
            _tc("2 2\n0 1000000000",                  "1000000000"),  # only 2 stalls, 2 cows
            _tc("4 2\n1 3 5 7",                       "6"),           # sorted [1,3,5,7] → 1 and 7
            _tc("4 4\n1 3 5 7",                       "2"),           # all 4 stalls → min gap = 2
            _tc("6 3\n10 1 2 7 5 3",                  "4"),           # sorted [1,2,3,5,7,10] → 1,5,10 → min=4
            _tc("5 2\n100 200 300 400 500",            "400"),         # 100 and 500
            _tc("6 4\n1 2 4 8 9 10",                  "2"),           # 1,4,8,10 → min(3,4,2)=2
            _tc("7 3\n0 3 6 9 12 15 18",              "9"),           # 0,9,18 → min=9
            _tc("5 5\n1 2 3 4 5",                     "1"),           # all stalls, min gap=1
            _tc("4 2\n0 1 999999999 1000000000",      "1000000000"),  # 0 and 1000000000
            _tc("8 4\n1 2 3 4 5 6 7 8",              "2"),           # 1,3,5,7 → min=2
            _tc("6 2\n5 4 3 2 1 6",                   "5"),           # sorted [1..6] → 1 and 6
            _tc("6 3\n1 6 11 16 21 26",               "10"),          # evenly spaced by 5 → 1,11,21 → min=10; or 1,16? wait 1,11,21 gaps=10,10 ✓
            _tc("5 3\n10 30 20 50 40",                "20"),          # sorted [10,20,30,40,50] → 10,30,50 → min=20
        ],
    },
]


# ── Seed logic ─────────────────────────────────────────────────────────────────

async def seed(session: AsyncSession) -> None:
    inserted = 0
    skipped = 0

    for prob in PROBLEMS:
        slug = _slugify(prob["title"])

        existing = await session.execute(
            select(BuiltinProblem).where(BuiltinProblem.slug == slug)
        )
        row: BuiltinProblem | None = existing.scalar_one_or_none()

        if row is None:
            row = BuiltinProblem(
                id=generate_uuid(),
                title=prob["title"],
                slug=slug,
                description=prob["description"],
                input_format=prob["input_format"],
                output_format=prob["output_format"],
                constraints=prob["constraints"],
                difficulty=prob["difficulty"],
                points=prob["points"],
                base_price=prob["base_price"],
                time_limit_ms=prob["time_limit_ms"],
                memory_limit_mb=prob["memory_limit_mb"],
                is_active=True,
            )
            session.add(row)
            await session.flush()  # assign row.id before GCS upload
            print(f"  [insert] '{prob['title']}' ({prob['difficulty']})")
            inserted += 1
        else:
            if row.test_cases_url:
                print(f"  [skip]   '{prob['title']}' already exists with test cases.")
                skipped += 1
                continue
            print(f"  [found]  '{prob['title']}' exists but has no test cases — uploading.")

        # Upload test cases to GCS (synchronous)
        test_cases = prob["test_cases"]
        sample_count = sum(1 for tc in test_cases if tc["is_sample"])
        try:
            url = storage_service.upload_test_cases(slug, test_cases)
            row.test_cases_url = url
            print(
                f"           GCS ✓  {len(test_cases)} test cases "
                f"({sample_count} sample) → {url}"
            )
        except StorageError as e:
            print(f"  [warn]   GCS upload failed for '{prob['title']}': {e}")
            print(f"           Row saved without test_cases_url.")

    await session.commit()
    print(f"\nDone. {inserted} inserted, {skipped} skipped.")


async def main() -> None:
    print("Seeding Two Sum and Aggressive Cows...\n")
    async with AsyncSessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
