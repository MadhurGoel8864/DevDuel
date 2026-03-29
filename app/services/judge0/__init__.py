# app/services/judge0/__init__.py
"""
Judge0 code execution service module.

Provides an async HTTP client for communicating with a self-hosted Judge0 CE instance.
"""

from app.services.judge0.client import Judge0Client

__all__ = ["Judge0Client"]
