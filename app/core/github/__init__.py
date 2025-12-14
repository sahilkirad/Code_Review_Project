"""
GitHub Integration Module for CodeGuard
Handles webhooks, PR analysis, and comment posting
"""

from .webhook import verify_webhook_signature, parse_webhook_payload
from .client import GitHubClient
from .analyzer import PRAnalyzer
from .formatter import CommentFormatter

__all__ = [
    "verify_webhook_signature",
    "parse_webhook_payload",
    "GitHubClient",
    "PRAnalyzer",
    "CommentFormatter",
]

