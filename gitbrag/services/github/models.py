from dataclasses import dataclass
from datetime import datetime


@dataclass
class PullRequestInfo:
    """Domain model for pull request information."""

    number: int
    title: str
    repository: str
    url: str
    state: str
    created_at: datetime
    merged_at: datetime | None
    closed_at: datetime | None
    author: str
    organization: str
