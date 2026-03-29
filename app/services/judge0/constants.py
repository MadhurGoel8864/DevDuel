# app/services/judge0/constants.py
"""Judge0 status codes, verdict mapping, and supported language IDs."""


class Judge0StatusId:
    """Judge0 submission status IDs."""

    IN_QUEUE = 1
    PROCESSING = 2
    ACCEPTED = 3
    WRONG_ANSWER = 4
    TIME_LIMIT_EXCEEDED = 5
    COMPILATION_ERROR = 6
    RUNTIME_ERROR_SIGSEGV = 7
    RUNTIME_ERROR_SIGXFSZ = 8
    RUNTIME_ERROR_SIGFPE = 9
    RUNTIME_ERROR_SIGABRT = 10
    RUNTIME_ERROR_NZEC = 11
    RUNTIME_ERROR_OTHER = 12
    INTERNAL_ERROR = 13
    EXEC_FORMAT_ERROR = 14


# Judge0 status ID → DevDuel SubmissionVerdict value
JUDGE0_TO_VERDICT: dict[int, str] = {
    3: "ACCEPTED",
    4: "WRONG_ANSWER",
    5: "TIME_LIMIT_EXCEEDED",
    6: "COMPILATION_ERROR",
    7: "RUNTIME_ERROR",
    8: "RUNTIME_ERROR",
    9: "RUNTIME_ERROR",
    10: "RUNTIME_ERROR",
    11: "RUNTIME_ERROR",
    12: "RUNTIME_ERROR",
    13: "INTERNAL_ERROR",
    14: "RUNTIME_ERROR",
}

# Curated language map: display name → Judge0 language ID
# Verified against self-hosted Judge0 CE instance via GET /languages.
SUPPORTED_LANGUAGES: dict[str, int] = {
    "python": 71,        # Python (3.8.1)
    "javascript": 63,    # JavaScript (Node.js 12.14.0)
    "typescript": 74,    # TypeScript (3.7.4)
    "cpp": 54,           # C++ (GCC 9.2.0)
    "c": 50,             # C (GCC 9.2.0)
    "java": 62,          # Java (OpenJDK 13.0.1)
    "go": 60,            # Go (1.13.5)
    "rust": 73,          # Rust (1.40.0)
}

# Reverse lookup: Judge0 language ID → display name
LANGUAGE_ID_TO_NAME: dict[int, str] = {v: k for k, v in SUPPORTED_LANGUAGES.items()}
