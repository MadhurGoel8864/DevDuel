"""Seed script: populate the builtin_problems table with curated problems.

Run once after applying the 0015 migration:
    python scripts/seed_builtin_problems.py

The script is idempotent - it skips rows whose slugs already exist.
"""

import asyncio
import re
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings  # noqa: E402
from app.database.models.problems import BuiltinProblem  # noqa: E402
from app.database.utils import generate_uuid  # noqa: E402

# Allow running from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

engine = create_async_engine(settings.DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


BUILTIN_PROBLEMS = [
    # ── Easy ──────────────────────────────────────────────────────────────────
    {
        "title": "Two Sum",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given an array of integers `nums` and an integer `target`, return **indices** "
            "of the two numbers such that they add up to `target`.\n\n"
            "You may assume that each input would have **exactly one solution**, and you "
            "may not use the same element twice.\n\n"
            "### Examples\n\n"
            "**Input:** `nums = [2,7,11,15]`, `target = 9`  \n"
            "**Output:** `[0, 1]`\n\n"
            "### Constraints\n"
            "- `2 <= nums.length <= 10^4`\n"
            "- `-10^9 <= nums[i] <= 10^9`\n"
            "- Only one valid answer exists."
        ),
    },
    {
        "title": "Reverse Linked List",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given the `head` of a singly linked list, reverse the list and return the "
            "reversed list.\n\n"
            "### Example\n\n"
            "**Input:** `head = [1,2,3,4,5]`  \n"
            "**Output:** `[5,4,3,2,1]`\n\n"
            "### Constraints\n"
            "- The number of nodes is in the range `[0, 5000]`.\n"
            "- `-5000 <= Node.val <= 5000`"
        ),
    },
    {
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, "
            "`'['` and `']'`, determine if the input string is **valid**.\n\n"
            "An input string is valid if:\n"
            "1. Open brackets must be closed by the same type of brackets.\n"
            "2. Open brackets must be closed in the correct order.\n"
            "3. Every close bracket has a corresponding open bracket of the same type.\n\n"
            "### Example\n\n"
            '**Input:** `s = "()[]{}"` → **Output:** `true`  \n'
            '**Input:** `s = "(]"` → **Output:** `false`'
        ),
    },
    {
        "title": "Fibonacci Number",
        "difficulty": "easy",
        "points": 80,
        "base_price": 80,
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "description": (
            "The **Fibonacci numbers**, commonly denoted `F(n)`, form a sequence such that "
            "each number is the sum of the two preceding ones, starting from `0` and `1`.\n\n"
            "`F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2)` for `n > 1`.\n\n"
            "Given `n`, calculate `F(n)`.\n\n"
            "### Constraints\n"
            "- `0 <= n <= 30`"
        ),
    },
    # ── Medium ─────────────────────────────────────────────────────────────────
    {
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given a string `s`, find the length of the **longest substring** without "
            "repeating characters.\n\n"
            "### Example\n\n"
            '**Input:** `s = "abcabcbb"` → **Output:** `3` (the answer is `"abc"`)\n\n'
            "### Constraints\n"
            "- `0 <= s.length <= 5 * 10^4`\n"
            "- `s` consists of English letters, digits, symbols and spaces."
        ),
    },
    {
        "title": "Binary Tree Level Order Traversal",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given the `root` of a binary tree, return the **level order traversal** of "
            "its nodes' values (i.e., from left to right, level by level).\n\n"
            "### Example\n\n"
            "**Input:** `root = [3,9,20,null,null,15,7]`  \n"
            "**Output:** `[[3],[9,20],[15,7]]`\n\n"
            "### Constraints\n"
            "- The number of nodes is in the range `[0, 2000]`.\n"
            "- `-1000 <= Node.val <= 1000`"
        ),
    },
    {
        "title": "Coin Change",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 3000,
        "memory_limit_mb": 256,
        "description": (
            "You are given an integer array `coins` representing coins of different "
            "denominations and an integer `amount` representing a total amount of money.\n\n"
            "Return the **fewest number of coins** needed to make up that amount. "
            "If it is impossible, return `-1`.\n\n"
            "### Example\n\n"
            "**Input:** `coins = [1,5,11]`, `amount = 11` → **Output:** `1`\n\n"
            "### Constraints\n"
            "- `1 <= coins.length <= 12`\n"
            "- `1 <= coins[i] <= 2^31 - 1`\n"
            "- `0 <= amount <= 10^4`"
        ),
    },
    {
        "title": "Number of Islands",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given an `m x n` 2D binary grid which represents a map of `'1'`s (land) and "
            "`'0'`s (water), return the **number of islands**.\n\n"
            "An island is surrounded by water and is formed by connecting adjacent lands "
            "horizontally or vertically.\n\n"
            "### Example\n\n"
            "```\n"
            "Input:\n"
            "  11110\n"
            "  11010\n"
            "  11000\n"
            "  00000\n"
            "Output: 1\n"
            "```\n\n"
            "### Constraints\n"
            "- `1 <= m, n <= 300`\n"
            "- `grid[i][j]` is `'0'` or `'1'`."
        ),
    },
    # ── Hard ───────────────────────────────────────────────────────────────────
    {
        "title": "Median of Two Sorted Arrays",
        "difficulty": "hard",
        "points": 400,
        "base_price": 400,
        "time_limit_ms": 3000,
        "memory_limit_mb": 256,
        "description": (
            "Given two sorted arrays `nums1` and `nums2` of size `m` and `n` respectively, "
            "return the **median** of the two sorted arrays.\n\n"
            "The overall runtime complexity should be `O(log(m+n))`.\n\n"
            "### Example\n\n"
            "**Input:** `nums1 = [1,3]`, `nums2 = [2]` → **Output:** `2.00000`\n\n"
            "### Constraints\n"
            "- `nums1.length == m`, `nums2.length == n`\n"
            "- `0 <= m, n <= 1000`\n"
            "- `0 <= m + n`\n"
            "- `-10^6 <= nums1[i], nums2[i] <= 10^6`"
        ),
    },
    {
        "title": "Trapping Rain Water",
        "difficulty": "hard",
        "points": 350,
        "base_price": 350,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given `n` non-negative integers representing an elevation map where the width "
            "of each bar is `1`, compute how much water it can trap after raining.\n\n"
            "### Example\n\n"
            "**Input:** `height = [0,1,0,2,1,0,1,3,2,1,2,1]` → **Output:** `6`\n\n"
            "### Constraints\n"
            "- `n == height.length`\n"
            "- `1 <= n <= 2 * 10^4`\n"
            "- `0 <= height[i] <= 10^5`"
        ),
    },
    {
        "title": "Word Ladder",
        "difficulty": "hard",
        "points": 400,
        "base_price": 400,
        "time_limit_ms": 5000,
        "memory_limit_mb": 512,
        "description": (
            "A **transformation sequence** from word `beginWord` to word `endWord` using a "
            "dictionary `wordList` is a sequence of words such that:\n\n"
            "- The first word is `beginWord`.\n"
            "- The last word is `endWord`.\n"
            "- Only one letter can be changed at a time.\n"
            "- Each intermediate word must exist in `wordList`.\n\n"
            "Return the **number of words** in the shortest transformation sequence from "
            "`beginWord` to `endWord`, or `0` if no such sequence exists.\n\n"
            "### Example\n\n"
            '**Input:** `beginWord = "hit"`, `endWord = "cog"`, '
            '`wordList = ["hot","dot","dog","lot","log","cog"]`  \n'
            "**Output:** `5` (hit → hot → dot → dog → cog)\n\n"
            "### Constraints\n"
            "- `1 <= beginWord.length <= 10`\n"
            "- `endWord.length == beginWord.length`\n"
            "- `1 <= wordList.length <= 5000`"
        ),
    },
]


async def seed(session: AsyncSession) -> None:
    inserted = 0
    skipped = 0

    for prob in BUILTIN_PROBLEMS:
        slug = _slugify(prob["title"])
        # Check if already exists (idempotent)
        existing = await session.execute(
            select(BuiltinProblem).where(BuiltinProblem.slug == slug)
        )
        if existing.scalar_one_or_none():
            print(f"  [skip] '{prob['title']}' already exists.")
            skipped += 1
            continue

        row = BuiltinProblem(
            id=generate_uuid(),
            title=prob["title"],
            slug=slug,
            description=prob["description"],
            difficulty=prob["difficulty"],
            points=prob["points"],
            base_price=prob["base_price"],
            time_limit_ms=prob["time_limit_ms"],
            memory_limit_mb=prob["memory_limit_mb"],
            is_active=True,
        )
        session.add(row)
        print(f"  [insert] '{prob['title']}' ({prob['difficulty']})")
        inserted += 1

    await session.commit()
    print(f"\nDone. {inserted} inserted, {skipped} skipped.")


async def main() -> None:
    print("Seeding built-in problems...")
    async with AsyncSessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
