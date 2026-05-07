"""Seed script: insert 10 classic DSA problems into builtin_problems,
then upload their test cases to GCS.

Problems seeded:
  1. Binary Search           (easy,   100 pts)
  2. Valid Parentheses       (easy,   100 pts)
  3. Maximum Subarray Sum    (easy,   150 pts)
  4. Climbing Stairs         (easy,   100 pts)
  5. Merge Intervals         (medium, 250 pts)
  6. Coin Change             (medium, 250 pts)
  7. Longest Common Subseq.  (medium, 300 pts)
  8. 0/1 Knapsack            (medium, 300 pts)
  9. Unique Paths            (medium, 200 pts)
 10. Longest Increasing Subseq. (medium, 300 pts)

Run from backend/DevDuel/ after applying migrations:
    python scripts/seed_10_dsa_problems.py

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
    # ── 1. Binary Search ──────────────────────────────────────────────────────
    {
        "title": "Binary Search",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given a **sorted** array of `n` distinct integers and a `target` value, "
            "return the **0-based index** of `target` in the array.\n\n"
            "If `target` is not present, return `-1`.\n\n"
            "Your solution must run in **O(log n)** time."
        ),
        "input_format": (
            "- First line: two integers `n` and `target`.\n"
            "- Second line: `n` space-separated integers in strictly ascending order."
        ),
        "output_format": (
            "Print a single integer — the 0-based index of `target`, or `-1` if not found."
        ),
        "constraints": (
            "- `1 ≤ n ≤ 10^5`\n"
            "- `-10^9 ≤ nums[i], target ≤ 10^9`\n"
            "- All elements are distinct and sorted in ascending order."
        ),
        "test_cases": [
            # samples
            _tc("5 3\n1 2 3 4 5",              "2",  is_sample=True),
            _tc("5 6\n1 2 3 4 5",              "-1", is_sample=True),
            _tc("1 7\n7",                       "0",  is_sample=True),
            # hidden
            _tc("6 4\n1 2 3 4 5 6",            "3"),   # mid-array
            _tc("4 1\n1 3 5 7",                "0"),   # first element
            _tc("4 7\n1 3 5 7",                "3"),   # last element
            _tc("7 10\n2 4 6 8 10 12 14",      "4"),   # sorted even array
            _tc("5 -3\n-5 -3 -1 1 3",          "1"),   # negative values
            _tc("6 100\n10 20 50 70 90 100",    "5"),   # last element, sparse
            _tc("5 50\n10 20 30 40 50",         "4"),   # last element
            _tc("4 15\n5 10 15 20",             "2"),   # exact middle
            _tc("3 0\n-2 0 2",                  "1"),   # zero in array
            _tc("6 -10\n-20 -15 -10 -5 0 5",   "2"),   # negative target
            _tc("5 99\n1 2 3 4 5",             "-1"),   # target not present
            _tc("6 3\n1 2 3 4 5 6",            "2"),   # standard lookup
        ],
    },

    # ── 2. Valid Parentheses ──────────────────────────────────────────────────
    {
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given a string `s` containing only the characters `(`, `)`, `{`, `}`, `[`, and `]`, "
            "determine if the input string is **valid**.\n\n"
            "A string is valid if:\n"
            "1. Open brackets are closed by the same type of bracket.\n"
            "2. Open brackets are closed in the correct order.\n"
            "3. Every close bracket has a corresponding open bracket of the same type."
        ),
        "input_format": "- A single line containing the bracket string `s`.",
        "output_format": 'Print `YES` if the string is valid, otherwise print `NO`.',
        "constraints": (
            "- `1 ≤ |s| ≤ 10^4`\n"
            "- `s` consists only of `()[]{}` characters."
        ),
        "test_cases": [
            # samples
            _tc("()",        "YES", is_sample=True),
            _tc("()[]{}",    "YES", is_sample=True),
            _tc("(]",        "NO",  is_sample=True),
            # hidden
            _tc("([)]",      "NO"),    # interleaved brackets
            _tc("{[]}",      "YES"),   # nested
            _tc("(",         "NO"),    # unclosed
            _tc(")",         "NO"),    # extra close
            _tc("{",         "NO"),    # unclosed curly
            _tc("[({})]",    "YES"),   # nested mixed
            _tc("(((())))",  "YES"),   # deeply nested same type
            _tc("((()",      "NO"),    # too many opens
            _tc(")))",       "NO"),    # too many closes
            _tc("{[()]}",    "YES"),   # triple nested
            _tc("([{}])",    "YES"),   # reversed nesting order
            _tc("{[}]",      "NO"),    # mismatched inner pair
        ],
    },

    # ── 3. Maximum Subarray Sum ───────────────────────────────────────────────
    {
        "title": "Maximum Subarray Sum",
        "difficulty": "easy",
        "points": 150,
        "base_price": 150,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given an integer array `nums`, find the **contiguous subarray** (containing at least "
            "one number) which has the **largest sum** and return that sum.\n\n"
            "A subarray is a contiguous non-empty part of an array."
        ),
        "input_format": (
            "- First line: integer `n`.\n"
            "- Second line: `n` space-separated integers."
        ),
        "output_format": "Print a single integer — the maximum subarray sum.",
        "constraints": (
            "- `1 ≤ n ≤ 10^5`\n"
            "- `-10^6 ≤ nums[i] ≤ 10^6`"
        ),
        "test_cases": [
            # samples
            _tc("9\n-2 1 -3 4 -1 2 1 -5 4",        "6",       is_sample=True),
            _tc("1\n1",                               "1",       is_sample=True),
            _tc("5\n5 4 -1 7 8",                     "23",      is_sample=True),
            # hidden
            _tc("4\n-1 -2 -3 -4",                    "-1"),     # all negative → best single element
            _tc("6\n1 2 3 4 5 6",                     "21"),     # all positive → whole array
            _tc("5\n-5 4 -1 4 -5",                   "7"),      # 4-1+4=7
            _tc("3\n-2 -1 -3",                        "-1"),     # all negative, -1 is max
            _tc("7\n3 -1 4 -1 5 -9 2",               "10"),     # 3-1+4-1+5=10
            _tc("6\n-4 3 1 -2 5 -1",                 "7"),      # 3+1-2+5=7
            _tc("4\n100 -200 100 100",                "200"),    # last two: 100+100=200
            _tc("5\n0 0 0 0 0",                       "0"),      # all zeros
            _tc("8\n-3 2 -1 4 -2 1 3 -4",            "7"),      # 2-1+4-2+1+3=7
            _tc("4\n1000000 -1 1000000 -1",           "1999999"),# 1000000-1+1000000=1999999
            _tc("5\n-1 0 1 -1 2",                    "2"),      # 0+1-1+2=2
            _tc("6\n2 3 -100 2 3 4",                 "9"),      # 2+3+4=9
        ],
    },

    # ── 4. Climbing Stairs ────────────────────────────────────────────────────
    {
        "title": "Climbing Stairs",
        "difficulty": "easy",
        "points": 100,
        "base_price": 100,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "You are climbing a staircase. It takes `n` steps to reach the top.\n\n"
            "Each time you can either climb **1** or **2** steps. "
            "In how many distinct ways can you climb to the top?"
        ),
        "input_format": "- A single integer `n`.",
        "output_format": "Print a single integer — the number of distinct ways to climb `n` stairs.",
        "constraints": "- `1 ≤ n ≤ 45`",
        "test_cases": [
            # samples
            _tc("1",  "1",          is_sample=True),
            _tc("2",  "2",          is_sample=True),
            _tc("5",  "8",          is_sample=True),
            # hidden — answers follow f(n) = f(n-1)+f(n-2), f(1)=1, f(2)=2
            _tc("3",  "3"),
            _tc("4",  "5"),
            _tc("6",  "13"),
            _tc("7",  "21"),
            _tc("8",  "34"),
            _tc("9",  "55"),
            _tc("10", "89"),
            _tc("15", "987"),
            _tc("20", "10946"),
            _tc("30", "1346269"),
            _tc("40", "165580141"),
            _tc("45", "1836311903"),
        ],
    },

    # ── 5. Merge Intervals ────────────────────────────────────────────────────
    {
        "title": "Merge Intervals",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given an array of intervals where `intervals[i] = [left_i, right_i]`, "
            "merge all **overlapping** intervals and return an array of the non-overlapping "
            "intervals that cover all the intervals in the input.\n\n"
            "Two intervals `[a, b]` and `[c, d]` overlap if `c ≤ b`."
        ),
        "input_format": (
            "- First line: integer `n` — the number of intervals.\n"
            "- Next `n` lines: each containing two integers `l r` representing an interval `[l, r]`."
        ),
        "output_format": (
            "Print the merged intervals sorted by start time, one per line, "
            "each as two space-separated integers `l r`."
        ),
        "constraints": (
            "- `1 ≤ n ≤ 10^4`\n"
            "- `0 ≤ l ≤ r ≤ 10^9`"
        ),
        "test_cases": [
            # samples
            _tc("4\n1 3\n2 6\n8 10\n15 18",          "1 6\n8 10\n15 18", is_sample=True),
            _tc("2\n1 4\n4 5",                         "1 5",             is_sample=True),
            _tc("3\n1 5\n2 3\n4 6",                   "1 6",             is_sample=True),
            # hidden
            _tc("1\n1 1",                              "1 1"),             # single interval
            _tc("3\n1 2\n3 4\n5 6",                   "1 2\n3 4\n5 6"),  # no overlaps
            _tc("4\n1 10\n2 3\n4 5\n6 7",             "1 10"),            # large interval contains all
            _tc("3\n1 3\n3 5\n5 7",                   "1 7"),             # chain via shared endpoints
            _tc("5\n6 8\n1 9\n2 4\n4 7\n3 5",        "1 9"),             # unsorted, all inside [1,9]
            _tc("3\n1 2\n2 3\n3 4",                   "1 4"),             # chain merge
            _tc("4\n5 10\n1 3\n15 20\n12 16",         "1 3\n5 10\n12 20"),# unsorted input, two merges
            _tc("5\n1 2\n3 4\n5 6\n7 8\n9 10",       "1 2\n3 4\n5 6\n7 8\n9 10"), # no overlaps
            _tc("3\n0 0\n0 0\n0 0",                   "0 0"),             # identical degenerate
            _tc("4\n1 4\n0 2\n3 5\n8 9",             "0 5\n8 9"),        # unsorted, two groups
            _tc("5\n2 3\n4 5\n6 7\n8 9\n1 10",       "1 10"),            # one interval covers all
            _tc("3\n1 3\n2 4\n5 7",                   "1 4\n5 7"),        # one merge + separate
        ],
    },

    # ── 6. Coin Change ───────────────────────────────────────────────────────
    {
        "title": "Coin Change",
        "difficulty": "medium",
        "points": 250,
        "base_price": 250,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "You are given an integer array `coins` representing coins of different denominations "
            "and an integer `amount` representing a total amount of money.\n\n"
            "Return the **fewest number of coins** needed to make up that amount. "
            "If that amount cannot be made up by any combination of the coins, return `-1`.\n\n"
            "You may use an unlimited number of each coin denomination."
        ),
        "input_format": (
            "- First line: two integers `n` and `amount`.\n"
            "- Second line: `n` space-separated integers representing coin denominations."
        ),
        "output_format": (
            "Print a single integer — the minimum number of coins needed, or `-1` if impossible."
        ),
        "constraints": (
            "- `1 ≤ n ≤ 12`\n"
            "- `1 ≤ coins[i] ≤ 1000`\n"
            "- `0 ≤ amount ≤ 10^4`"
        ),
        "test_cases": [
            # samples
            _tc("3 11\n1 5 6",        "2",  is_sample=True),  # 5+6
            _tc("2 3\n2 3",           "1",  is_sample=True),  # single coin
            _tc("1 3\n2",             "-1", is_sample=True),  # impossible
            # hidden
            _tc("2 0\n1 2",           "0"),    # amount=0 → 0 coins
            _tc("3 7\n1 3 4",         "2"),    # 3+4=7
            _tc("2 11\n3 5",          "3"),    # 3+3+5=11
            _tc("3 12\n1 6 9",        "2"),    # 6+6=12
            _tc("3 11\n1 6 9",        "3"),    # 9+1+1=11
            _tc("3 100\n1 5 10",      "10"),   # 10×10=100
            _tc("1 1\n1",             "1"),    # single coin equals amount
            _tc("1 5\n2",             "-1"),   # 5 is odd, can't make with 2s
            _tc("3 6\n1 3 4",         "2"),    # 3+3=6
            _tc("2 4\n2 3",           "2"),    # 2+2=4
            _tc("4 15\n1 3 5 7",      "3"),    # 7+5+3=15
            _tc("3 30\n10 15 20",     "2"),    # 15+15=30
        ],
    },

    # ── 7. Longest Common Subsequence ────────────────────────────────────────
    {
        "title": "Longest Common Subsequence",
        "difficulty": "medium",
        "points": 300,
        "base_price": 300,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given two strings `text1` and `text2`, return the length of their "
            "**longest common subsequence** (LCS).\n\n"
            "A *subsequence* of a string is a new string generated from the original string "
            "with some characters (can be none) deleted without changing the relative order "
            "of the remaining characters.\n\n"
            "A *common subsequence* of two strings is a subsequence that appears in both strings."
        ),
        "input_format": (
            "- First line: string `text1`.\n"
            "- Second line: string `text2`."
        ),
        "output_format": "Print a single integer — the length of the longest common subsequence.",
        "constraints": (
            "- `1 ≤ |text1|, |text2| ≤ 1000`\n"
            "- Both strings consist of only lowercase and uppercase English letters."
        ),
        "test_cases": [
            # samples
            _tc("ABCBDAB\nBDCABA",     "4", is_sample=True),
            _tc("AGGTAB\nGXTXAYB",     "4", is_sample=True),
            _tc("ABC\nAC",             "2", is_sample=True),
            # hidden
            _tc("ABCD\nABCD",          "4"),   # identical strings
            _tc("ABC\nDEF",            "0"),   # no common chars
            _tc("ABCDE\nACE",          "3"),   # ACE
            _tc("AAAA\nAA",            "2"),   # repeated chars
            _tc("XYZW\nXYWZ",          "3"),   # XYZ or XYW
            _tc("ABCDE\nBCDAE",        "4"),   # BCDE
            _tc("HELLO\nHELLO",        "5"),   # same string
            _tc("A\nA",                "1"),   # single matching char
            _tc("A\nB",                "0"),   # single non-matching char
            _tc("ABCDEF\nACEG",        "3"),   # ACE (G not in s1)
            _tc("ABCABC\nABC",         "3"),   # ABC appears in both
            _tc("KITTEN\nSITTING",     "4"),   # ITTN
        ],
    },

    # ── 8. 0/1 Knapsack ──────────────────────────────────────────────────────
    {
        "title": "0/1 Knapsack",
        "difficulty": "medium",
        "points": 300,
        "base_price": 300,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "You are given `n` items, each with a **weight** and a **value**. "
            "You have a knapsack with a maximum weight capacity of `W`.\n\n"
            "Each item can be included **at most once** (0 or 1 times). "
            "Find the **maximum total value** you can carry without exceeding the weight limit."
        ),
        "input_format": (
            "- First line: two integers `n` and `W` — number of items and weight capacity.\n"
            "- Next `n` lines: each containing two integers `weight_i` and `value_i`."
        ),
        "output_format": "Print a single integer — the maximum value achievable.",
        "constraints": (
            "- `1 ≤ n ≤ 100`\n"
            "- `1 ≤ W ≤ 1000`\n"
            "- `1 ≤ weight_i ≤ 100`\n"
            "- `1 ≤ value_i ≤ 1000`"
        ),
        "test_cases": [
            # samples
            _tc("4 7\n1 1\n3 4\n4 5\n5 7",             "9",   is_sample=True),
            _tc("3 50\n10 60\n20 100\n30 120",           "220", is_sample=True),
            _tc("1 10\n10 100",                          "100", is_sample=True),
            # hidden
            _tc("1 5\n10 100",                           "0"),    # item too heavy, nothing fits
            _tc("2 3\n1 10\n2 20",                       "30"),   # both fit: 1+2=3
            _tc("3 10\n5 10\n4 40\n3 30",               "70"),   # items 2+3: w=7, v=70
            _tc("4 10\n2 1\n3 3\n5 5\n6 6",             "9"),    # items 2+3+1: w=10, v=9
            _tc("2 15\n12 40\n6 20",                     "40"),   # items too heavy combined; best alone=40
            _tc("3 7\n1 10\n2 15\n3 20",                "45"),   # all fit: w=6≤7, v=45
            _tc("5 100\n20 200\n30 300\n40 400\n50 500\n60 600",
                                                         "1000"), # items 3+5 or 1+2+4: v=1000
            _tc("4 5\n3 4\n3 4\n3 4\n3 4",              "4"),    # only 1 item fits
            _tc("3 100\n1 1\n2 2\n3 3",                 "6"),    # all fit: v=1+2+3=6
            _tc("2 10\n6 10\n5 8",                       "10"),   # can't take both; best=10
            _tc("3 6\n2 5\n3 8\n4 9",                   "14"),   # items 1+3: w=6, v=14
            _tc("4 8\n2 3\n3 4\n4 5\n5 8",              "12"),   # items 2+4: w=8, v=12
        ],
    },

    # ── 9. Unique Paths ───────────────────────────────────────────────────────
    {
        "title": "Unique Paths",
        "difficulty": "medium",
        "points": 200,
        "base_price": 200,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "A robot is located at the **top-left corner** of an `m × n` grid. "
            "The robot can only move either **down** or **right** at any point in time.\n\n"
            "The robot is trying to reach the **bottom-right corner** of the grid.\n\n"
            "How many possible **unique paths** are there?"
        ),
        "input_format": "- A single line containing two integers `m` and `n`.",
        "output_format": "Print a single integer — the number of unique paths.",
        "constraints": (
            "- `1 ≤ m, n ≤ 15`\n"
            "- The answer is guaranteed to fit in a 32-bit signed integer."
        ),
        "test_cases": [
            # samples — answers = C(m+n-2, m-1)
            _tc("3 7",   "28",    is_sample=True),   # C(8,2)=28
            _tc("3 2",   "3",     is_sample=True),   # C(3,2)=3
            _tc("1 1",   "1",     is_sample=True),   # C(0,0)=1
            # hidden
            _tc("2 2",   "2"),    # C(2,1)=2
            _tc("4 4",   "20"),   # C(6,3)=20
            _tc("5 5",   "70"),   # C(8,4)=70
            _tc("3 3",   "6"),    # C(4,2)=6
            _tc("2 10",  "10"),   # C(10,1)=10
            _tc("5 3",   "15"),   # C(6,2)=15
            _tc("1 10",  "1"),    # C(9,0)=1
            _tc("10 1",  "1"),    # C(9,9)=1
            _tc("7 3",   "28"),   # C(8,2)=28
            _tc("4 3",   "10"),   # C(5,2)=10
            _tc("6 6",   "252"),  # C(10,5)=252
            _tc("10 10", "48620"),# C(18,9)=48620
        ],
    },

    # ── 10. Longest Increasing Subsequence ───────────────────────────────────
    {
        "title": "Longest Increasing Subsequence",
        "difficulty": "medium",
        "points": 300,
        "base_price": 300,
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "description": (
            "Given an integer array `nums`, return the length of the **longest strictly "
            "increasing subsequence**.\n\n"
            "A *subsequence* is a sequence derived from the array by deleting some or no "
            "elements without changing the order of the remaining elements."
        ),
        "input_format": (
            "- First line: integer `n`.\n"
            "- Second line: `n` space-separated integers."
        ),
        "output_format": "Print a single integer — the length of the longest increasing subsequence.",
        "constraints": (
            "- `1 ≤ n ≤ 2500`\n"
            "- `-10^4 ≤ nums[i] ≤ 10^4`"
        ),
        "test_cases": [
            # samples
            _tc("8\n10 9 2 5 3 7 101 18",         "4", is_sample=True),
            _tc("4\n0 1 0 3",                      "3", is_sample=True),
            _tc("6\n7 7 7 7 7 7",                  "1", is_sample=True),
            # hidden
            _tc("5\n1 2 3 4 5",                    "5"),   # fully increasing
            _tc("5\n5 4 3 2 1",                    "1"),   # fully decreasing
            _tc("1\n42",                            "1"),   # single element
            _tc("7\n1 3 2 5 4 6 5",               "4"),   # LIS: 1,2,4,5 or 1,3,4,5
            _tc("10\n2 1 5 3 6 4 8 9 7 10",       "6"),   # LIS: 1,3,4,8,9,10
            _tc("6\n3 5 6 2 5 4",                  "3"),   # 3,5,6
            _tc("5\n2 2 2 2 2",                    "1"),   # all equal (strictly increasing)
            _tc("6\n1 5 2 6 3 7",                  "4"),   # LIS: 1,2,3,7 or 1,5,6,7
            _tc("4\n10 20 10 30",                  "3"),   # 10,20,30
            _tc("9\n3 10 2 1 20 5 8 15 7",        "4"),   # LIS: 3,5,8,15
            _tc("5\n4 3 2 1 5",                    "2"),   # best: any_single+5
            _tc("7\n5 1 4 2 8 6 3",               "3"),   # LIS: 1,2,3 or 1,4,8 or 1,2,8
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
            await session.flush()
            print(f"  [insert] '{prob['title']}' ({prob['difficulty']})")
            inserted += 1
        else:
            if row.test_cases_url:
                print(f"  [skip]   '{prob['title']}' already exists with test cases.")
                skipped += 1
                continue
            print(f"  [found]  '{prob['title']}' exists but has no test cases — uploading.")

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
    print("Seeding 10 classic DSA problems...\n")
    async with AsyncSessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
