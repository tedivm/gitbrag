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
    star_increase: int | None = None  # Number of stars gained during filtered period
    additions: int | None = None  # Number of lines added
    deletions: int | None = None  # Number of lines deleted
    changed_files: int | None = None  # Number of files changed
    author_association: str | None = None  # Contributor relationship (OWNER, MEMBER, CONTRIBUTOR, etc.)

    def get_display_state(self) -> str:
        """Get the display state of the PR.

        GitHub API returns "open" or "closed" as state values.
        This method determines the actual semantic state:
        - "merged" if closed with merged_at timestamp
        - "open" if still open
        - "closed" if closed without being merged

        Returns:
            The display state: "merged", "open", or "closed"
        """
        if self.state == "closed" and self.merged_at:
            return "merged"
        return self.state
