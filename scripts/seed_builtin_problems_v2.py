"""Seed script: populate the builtin_problems table with 20 curated problems.

Run once after applying migrations:
    python scripts/seed_builtin_problems_v2.py

The script is idempotent - it skips rows whose slugs already exist.
"""

import asyncio
import re
import sys
from pathlib import Path

# Allow running from the project root without installing the package.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env before importing settings so pydantic_settings can find the vars.
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings  # noqa: E402
from app.database.models.problems import BuiltinProblem  # noqa: E402
from app.database.utils import generate_uuid  # noqa: E402

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
        "title": "Palindrome Number",
        "difficulty": "easy",
        "points": 80,
        "base_price": 80,
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "description": (
            "## Palindrome Number\n\n"
            "Given an integer `x`, return `true` if `x` is a **palindrome**, and `false` otherwise.\n\n"
            "An integer is a palindrome when it reads the same forward and backward.\n\n"
            "### Examples\n\n"
            "**Input:** `x = 121` → **Output:** `true`  \n"
            "**Input:** `x = -121` → **Output:** `false`  \n"
            "**Input:** `x = 10` → **Output:** `false`\n\n"
            "### Constraints\n"
            "- `-2^31 <= x <= 2^31 - 1`"
        ),
    },
    {
        "title": "Best Time to Buy and Sell Stock",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "## Best Time to Buy and Sell Stock\n\n"
            "You are given an array `prices` where `prices[i]` is the price of a given stock on the `i`-th day.\n\n"
            "You want to maximize your profit by choosing a **single day** to buy one stock and choosing a "
            "**different day in the future** to sell that stock.\n\n"
            "Return the **maximum profit** you can achieve. If no profit is possible, return `0`.\n\n"
            "### Example\n\n"
            "**Input:** `prices = [7,1,5,3,6,4]` → **Output:** `5`\n\n"
            "### Constraints\n"
            "- `1 <= prices.length <= 10^5`\n"
            "- `0 <= prices[i] <= 10^4`"
        ),
    },
    {
        "title": "Merge Two Sorted Lists",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "## Merge Two Sorted Lists\n\n"
            "You are given the heads of two sorted linked lists `list1` and `list2`.\n\n"
            "Merge the two lists into one **sorted** list. The list should be made by splicing together "
            "the nodes of the first two lists.\n\n"
            "Return the head of the merged linked list.\n\n"
            "### Example\n\n"
            "**Input:** `list1 = [1,2,4]`, `list2 = [1,3,4]` → **Output:** `[1,1,2,3,4,4]`\n\n"
            "### Constraints\n"
            "- The number of nodes in both lists is in the range `[0, 50]`.\n"
            "- `-100 <= Node.val <= 100`\n"
            "- Both `list1` and `list2` are sorted in non-decreasing order."
        ),
    },
    {
        "title": "Maximum Depth of Binary Tree",
        "difficulty": "easy",
        "points": 80,
        "base_price": 80,
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "description": (
            "## Maximum Depth of Binary Tree\n\n"
            "Given the `root` of a binary tree, return its **maximum depth**.\n\n"
            "A binary tree's maximum depth is the number of nodes along the longest path "
            "from the root node down to the farthest leaf node.\n\n"
            "### Example\n\n"
            "**Input:** `root = [3,9,20,null,null,15,7]` → **Output:** `3`\n\n"
            "### Constraints\n"
            "- The number of nodes is in the range `[0, 10^4]`.\n"
            "- `-100 <= Node.val <= 100`"
        ),
    },
    {
        "title": "Single Number",
        "difficulty": "easy",
        "points": 80,
        "base_price": 80,
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "description": (
            "## Single Number\n\n"
            "Given a **non-empty** array of integers `nums`, every element appears *twice* except for one. "
            "Find that single one.\n\n"
            "You must implement a solution with linear runtime complexity and use only constant extra space.\n\n"
            "### Example\n\n"
            "**Input:** `nums = [4,1,2,1,2]` → **Output:** `4`\n\n"
            "### Constraints\n"
            "- `1 <= nums.length <= 3 * 10^4`\n"
            "- `-3 * 10^4 <= nums[i] <= 3 * 10^4`\n"
            "- Each element appears twice except for exactly one element."
        ),
    },
    {
        "title": "Contains Duplicate",
        "difficulty": "easy",
        "points": 80,
        "base_price": 80,
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "description": (
            "## Contains Duplicate\n\n"
            "Given an integer array `nums`, return `true` if any value appears **at least twice** "
            "in the array, and return `false` if every element is distinct.\n\n"
            "### Examples\n\n"
            "**Input:** `nums = [1,2,3,1]` → **Output:** `true`  \n"
            "**Input:** `nums = [1,2,3,4]` → **Output:** `false`\n\n"
            "### Constraints\n"
            "- `1 <= nums.length <= 10^5`\n"
            "- `-10^9 <= nums[i] <= 10^9`"
        ),
    },
    # ── Medium ─────────────────────────────────────────────────────────────────
    {
        "title": "3Sum",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 3000,
        "memory_limit_mb": 256,
        "description": (
            "## 3Sum\n\n"
            "Given an integer array `nums`, return all the triplets `[nums[i], nums[j], nums[k]]` "
            "such that `i != j`, `i != k`, `j != k`, and `nums[i] + nums[j] + nums[k] == 0`.\n\n"
            "The solution set must **not contain duplicate triplets**.\n\n"
            "### Example\n\n"
            "**Input:** `nums = [-1,0,1,2,-1,-4]` → **Output:** `[[-1,-1,2],[-1,0,1]]`\n\n"
            "### Constraints\n"
            "- `3 <= nums.length <= 3000`\n"
            "- `-10^5 <= nums[i] <= 10^5`"
        ),
    },
    {
        "title": "Product of Array Except Self",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "## Product of Array Except Self\n\n"
            "Given an integer array `nums`, return an array `answer` such that `answer[i]` is equal to "
            "the product of all the elements of `nums` except `nums[i]`.\n\n"
            "The product of any prefix or suffix of `nums` is **guaranteed to fit** in a 32-bit integer.\n\n"
            "You must write an algorithm that runs in `O(n)` time and **without using the division** operation.\n\n"
            "### Example\n\n"
            "**Input:** `nums = [1,2,3,4]` → **Output:** `[24,12,8,6]`\n\n"
            "### Constraints\n"
            "- `2 <= nums.length <= 10^5`\n"
            "- `-30 <= nums[i] <= 30`"
        ),
    },
    {
        "title": "Longest Palindromic Substring",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 3000,
        "memory_limit_mb": 256,
        "description": (
            "## Longest Palindromic Substring\n\n"
            "Given a string `s`, return the **longest palindromic substring** in `s`.\n\n"
            "### Examples\n\n"
            '**Input:** `s = "babad"` → **Output:** `"bab"` (or `"aba"` is also valid)  \n'
            '**Input:** `s = "cbbd"` → **Output:** `"bb"`\n\n'
            "### Constraints\n"
            "- `1 <= s.length <= 1000`\n"
            "- `s` consists of only digits and English letters."
        ),
    },
    {
        "title": "Jump Game",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "## Jump Game\n\n"
            "You are given an integer array `nums`. You are initially positioned at the array's "
            "**first index**, and each element in the array represents your maximum jump length at that position.\n\n"
            "Return `true` if you can reach the last index, or `false` otherwise.\n\n"
            "### Examples\n\n"
            "**Input:** `nums = [2,3,1,1,4]` → **Output:** `true`  \n"
            "**Input:** `nums = [3,2,1,0,4]` → **Output:** `false`\n\n"
            "### Constraints\n"
            "- `1 <= nums.length <= 10^4`\n"
            "- `0 <= nums[i] <= 10^5`"
        ),
    },
    {
        "title": "Find Minimum in Rotated Sorted Array",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "## Find Minimum in Rotated Sorted Array\n\n"
            "Suppose an array of length `n` sorted in ascending order is **rotated** between `1` and `n` times.\n\n"
            "Given the sorted rotated array `nums` of **unique** elements, return the **minimum element** "
            "of this array.\n\n"
            "You must write an algorithm that runs in `O(log n)` time.\n\n"
            "### Example\n\n"
            "**Input:** `nums = [3,4,5,1,2]` → **Output:** `1`\n\n"
            "### Constraints\n"
            "- `n == nums.length`\n"
            "- `1 <= n <= 5000`\n"
            "- `-5000 <= nums[i] <= 5000`\n"
            "- All integers are **unique**."
        ),
    },
    {
        "title": "Subarray Sum Equals K",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 3000,
        "memory_limit_mb": 256,
        "description": (
            "## Subarray Sum Equals K\n\n"
            "Given an array of integers `nums` and an integer `k`, return the **total number of subarrays** "
            "whose sum equals to `k`.\n\n"
            "A subarray is a contiguous **non-empty** sequence of elements within an array.\n\n"
            "### Example\n\n"
            "**Input:** `nums = [1,1,1]`, `k = 2` → **Output:** `2`\n\n"
            "### Constraints\n"
            "- `1 <= nums.length <= 2 * 10^4`\n"
            "- `-1000 <= nums[i] <= 1000`\n"
            "- `-10^7 <= k <= 10^7`"
        ),
    },
    {
        "title": "Decode Ways",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "## Decode Ways\n\n"
            "A message containing letters from `A-Z` can be **encoded** into numbers using the following mapping:\n\n"
            "```\n'A' -> \"1\", 'B' -> \"2\", ..., 'Z' -> \"26\"\n```\n\n"
            "Given a string `s` containing only digits, return the **number of ways** to decode it.\n\n"
            "### Examples\n\n"
            '**Input:** `s = "12"` → **Output:** `2` (decoded as `"AB"` or `"L"`)  \n'
            '**Input:** `s = "226"` → **Output:** `3`\n\n'
            "### Constraints\n"
            "- `1 <= s.length <= 100`\n"
            "- `s` contains only digits and may contain leading zeros."
        ),
    },
    # ── Hard ───────────────────────────────────────────────────────────────────
    {
        "title": "Merge K Sorted Lists",
        "difficulty": "hard",
        "points": 400,
        "base_price": 400,
        "time_limit_ms": 4000,
        "memory_limit_mb": 512,
        "description": (
            "## Merge K Sorted Lists\n\n"
            "You are given an array of `k` linked-lists `lists`, each linked-list is sorted in ascending order.\n\n"
            "Merge all the linked-lists into one sorted linked-list and return it.\n\n"
            "### Example\n\n"
            "**Input:** `lists = [[1,4,5],[1,3,4],[2,6]]` → **Output:** `[1,1,2,3,4,4,5,6]`\n\n"
            "### Constraints\n"
            "- `k == lists.length`\n"
            "- `0 <= k <= 10^4`\n"
            "- `0 <= lists[i].length <= 500`\n"
            "- `-10^4 <= lists[i][j] <= 10^4`\n"
            "- `lists[i]` is sorted in ascending order.\n"
            "- The sum of `lists[i].length` will not exceed `10^4`."
        ),
    },
    {
        "title": "Minimum Window Substring",
        "difficulty": "hard",
        "points": 400,
        "base_price": 400,
        "time_limit_ms": 4000,
        "memory_limit_mb": 256,
        "description": (
            "## Minimum Window Substring\n\n"
            "Given two strings `s` and `t` of lengths `m` and `n` respectively, return the **minimum window "
            "substring** of `s` such that every character in `t` (including duplicates) is included in the window. "
            "If there is no such substring, return the empty string `\"\"`.\n\n"
            "### Example\n\n"
            '**Input:** `s = "ADOBECODEBANC"`, `t = "ABC"` → **Output:** `"BANC"`\n\n'
            "### Constraints\n"
            "- `m == s.length`, `n == t.length`\n"
            "- `1 <= m, n <= 10^5`\n"
            "- `s` and `t` consist of uppercase and lowercase English letters."
        ),
    },
    {
        "title": "Serialize and Deserialize Binary Tree",
        "difficulty": "hard",
        "points": 400,
        "base_price": 400,
        "time_limit_ms": 4000,
        "memory_limit_mb": 512,
        "description": (
            "## Serialize and Deserialize Binary Tree\n\n"
            "Serialization is the process of converting a data structure or object into a sequence of bits "
            "so that it can be stored in a file or memory buffer, or transmitted across a network.\n\n"
            "Design an algorithm to **serialize** and **deserialize** a binary tree. There is no restriction "
            "on how your serialization/deserialization algorithm should work. Just make sure that a binary "
            "tree can be serialized to a string and this string can be deserialized to the original tree structure.\n\n"
            "### Example\n\n"
            "**Input:** `root = [1,2,3,null,null,4,5]`  \n"
            "**Output:** `[1,2,3,null,null,4,5]`\n\n"
            "### Constraints\n"
            "- The number of nodes in the tree is in the range `[0, 10^4]`.\n"
            "- `-1000 <= Node.val <= 1000`"
        ),
    },
    {
        "title": "Longest Consecutive Sequence",
        "difficulty": "hard",
        "points": 350,
        "base_price": 350,
        "time_limit_ms": 3000,
        "memory_limit_mb": 256,
        "description": (
            "## Longest Consecutive Sequence\n\n"
            "Given an unsorted array of integers `nums`, return the length of the **longest consecutive "
            "elements sequence**.\n\n"
            "You must write an algorithm that runs in `O(n)` time.\n\n"
            "### Example\n\n"
            "**Input:** `nums = [100,4,200,1,3,2]` → **Output:** `4`  \n"
            "(The longest consecutive sequence is `[1, 2, 3, 4]`)\n\n"
            "### Constraints\n"
            "- `0 <= nums.length <= 10^5`\n"
            "- `-10^9 <= nums[i] <= 10^9`"
        ),
    },
    {
        "title": "Regular Expression Matching",
        "difficulty": "hard",
        "points": 450,
        "base_price": 450,
        "time_limit_ms": 5000,
        "memory_limit_mb": 256,
        "description": (
            "## Regular Expression Matching\n\n"
            "Given an input string `s` and a pattern `p`, implement regular expression matching with "
            "support for `'.'` and `'*'` where:\n\n"
            "- `'.'` matches any single character.\n"
            "- `'*'` matches zero or more of the preceding element.\n\n"
            "The matching should cover the **entire** input string (not partial).\n\n"
            "### Examples\n\n"
            '**Input:** `s = "aa"`, `p = "a"` → **Output:** `false`  \n'
            '**Input:** `s = "aa"`, `p = "a*"` → **Output:** `true`  \n'
            '**Input:** `s = "ab"`, `p = ".*"` → **Output:** `true`\n\n'
            "### Constraints\n"
            "- `1 <= s.length <= 20`\n"
            "- `1 <= p.length <= 30`\n"
            "- `s` contains only lowercase English letters.\n"
            "- `p` contains only lowercase English letters, `'.'`, and `'*'`."
        ),
    },
    {
        "title": "N-Queens",
        "difficulty": "hard",
        "points": 450,
        "base_price": 450,
        "time_limit_ms": 5000,
        "memory_limit_mb": 512,
        "description": (
            "## N-Queens\n\n"
            "The **n-queens** puzzle is the problem of placing `n` queens on an `n x n` chessboard such that "
            "no two queens attack each other.\n\n"
            "Given an integer `n`, return **all distinct solutions** to the n-queens puzzle. "
            "You may return the answer in any order.\n\n"
            "Each solution contains a distinct board configuration of the n-queens' placement, where `'Q'` "
            "and `'.'` both indicate a queen and an empty space, respectively.\n\n"
            "### Example\n\n"
            "**Input:** `n = 4`  \n"
            "**Output:** `[[\".Q..\",\"...Q\",\"Q...\",\"..Q.\"], [\"..Q.\",\"Q...\",\"...Q\",\".Q..\"]]`\n\n"
            "### Constraints\n"
            "- `1 <= n <= 9`"
        ),
    },
    {
        "title": "Alien Dictionary",
        "difficulty": "hard",
        "points": 400,
        "base_price": 400,
        "time_limit_ms": 4000,
        "memory_limit_mb": 256,
        "description": (
            "## Alien Dictionary\n\n"
            "There is a new alien language that uses the English alphabet. However, the order among the "
            "letters is unknown to you.\n\n"
            "You are given a list of strings `words` from the alien language's dictionary, where the strings "
            "in `words` are **sorted lexicographically** by the rules of this new language.\n\n"
            "Return a string of the unique letters in the new alien language sorted in **lexicographically "
            "increasing order** by the new language's rules. If there is no solution, return `\"\"`. "
            "If there are multiple solutions, return **any of them**.\n\n"
            "### Example\n\n"
            '**Input:** `words = ["wrt","wrf","er","ett","rftt"]` → **Output:** `"wertf"`\n\n'
            "### Constraints\n"
            "- `1 <= words.length <= 100`\n"
            "- `1 <= words[i].length <= 100`\n"
            "- `words[i]` consists of only lowercase English letters."
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
    print("Seeding built-in problems (batch 2)...")
    async with AsyncSessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
