"""
Pydantic models for GitHub webhook payloads
"""
from pydantic import BaseModel
from typing import Optional, List

class CommitInfo(BaseModel):
    sha: str
    ref: str

class PRInfo(BaseModel):
    number: int
    state: str
    head: CommitInfo
    base: CommitInfo
    title: Optional[str] = None
    body: Optional[str] = None

class RepoInfo(BaseModel):
    full_name: str
    name: str
    owner: dict

class WebhookPayload(BaseModel):
    action: str
    pull_request: PRInfo
    repository: RepoInfo

class FileInfo(BaseModel):
    filename: str
    status: str  # added, modified, removed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None

