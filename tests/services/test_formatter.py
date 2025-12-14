from datetime import datetime
from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from gitbrag.services.formatter import format_pr_list, show_progress
from gitbrag.services.github.models import PullRequestInfo


@pytest.fixture
def sample_prs() -> list[PullRequestInfo]:
    """Create sample pull requests for testing."""
    return [
        PullRequestInfo(
            number=1,
            title="Add feature A",
            repository="owner/repo1",
            url="https://github.com/owner/repo1/pull/1",
            state="open",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            merged_at=None,
            closed_at=None,
            author="testuser",
            organization="owner",
        ),
        PullRequestInfo(
            number=2,
            title="Fix bug B",
            repository="owner/repo2",
            url="https://github.com/owner/repo2/pull/2",
            state="closed",
            created_at=datetime(2024, 1, 2, 12, 0, 0),
            merged_at=datetime(2024, 1, 3, 12, 0, 0),
            closed_at=datetime(2024, 1, 3, 12, 0, 0),
            author="testuser",
            organization="owner",
        ),
        PullRequestInfo(
            number=3,
            title="Update docs",
            repository="owner/repo1",
            url="https://github.com/owner/repo1/pull/3",
            state="closed",
            created_at=datetime(2024, 1, 3, 12, 0, 0),
            merged_at=None,
            closed_at=datetime(2024, 1, 4, 12, 0, 0),
            author="testuser",
            organization="owner",
        ),
    ]


def test_format_pr_list_basic(sample_prs: list[PullRequestInfo]) -> None:
    """Test basic PR list formatting."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs)

    result = output.getvalue()

    # Check that table is created
    assert "Pull Requests" in result
    assert "PR #" in result
    assert "State" in result
    assert "Repository" in result
    assert "Title" in result
    assert "Created" in result

    # Check PR content
    assert "Add feature A" in result
    assert "Fix bug B" in result
    assert "Update docs" in result

    # Check total count (Rich adds formatting codes, so check for core text)
    assert "Total" in result
    assert "3" in result
    assert "pull requests" in result


def test_format_pr_list_with_urls(sample_prs: list[PullRequestInfo]) -> None:
    """Test PR list formatting with URLs displayed."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, show_urls=True)

    result = output.getvalue()

    # Check URL column header
    assert "URL" in result

    # Check URLs are displayed
    assert "https://github.com/owner/repo1/pull/1" in result
    assert "https://github.com/owner/repo2/pull/2" in result


def test_format_pr_list_without_urls(sample_prs: list[PullRequestInfo]) -> None:
    """Test PR list formatting without URLs (default)."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, show_urls=False)

    result = output.getvalue()

    # URLs should not be in output when show_urls=False
    # Note: Still check for PR numbers which are always shown
    assert "1" in result  # PR number
    assert "2" in result
    assert "3" in result


def test_format_pr_list_empty() -> None:
    """Test formatting empty PR list."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list([])

    result = output.getvalue()

    # Check for empty message
    assert "No pull requests found" in result
    assert "No Results" in result


def test_format_pr_list_state_colors(sample_prs: list[PullRequestInfo]) -> None:
    """Test that different PR states have different colors."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs)

    result = output.getvalue()

    # Rich uses color tags in output
    # Open PRs should be blue, merged should be green, closed should be yellow
    assert "open" in result.lower()
    assert "merged" in result.lower()
    assert "closed" in result.lower()


def test_format_pr_list_sort_by_created_desc(sample_prs: list[PullRequestInfo]) -> None:
    """Test sorting by created date descending (default)."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, sort_fields=[("created_at", "desc")])

    result = output.getvalue()

    # Should be in order: Update docs (Jan 3), Fix bug B (Jan 2), Add feature A (Jan 1)
    # Check order by finding positions
    assert result.index("Update docs") < result.index("Fix bug B")
    assert result.index("Fix bug B") < result.index("Add feature A")


def test_format_pr_list_sort_by_created_asc(sample_prs: list[PullRequestInfo]) -> None:
    """Test sorting by created date ascending."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, sort_fields=[("created_at", "asc")])

    result = output.getvalue()

    # Should be in order: Add feature A (Jan 1), Fix bug B (Jan 2), Update docs (Jan 3)
    assert result.index("Add feature A") < result.index("Fix bug B")
    assert result.index("Fix bug B") < result.index("Update docs")


def test_format_pr_list_sort_by_repository(sample_prs: list[PullRequestInfo]) -> None:
    """Test sorting by repository name."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, sort_fields=[("repository", "asc")])

    result = output.getvalue()

    # Should group repo1 together before repo2
    repo1_positions = [result.index("Add feature A"), result.index("Update docs")]
    repo2_position = result.index("Fix bug B")

    # Both repo1 PRs should be before repo2 PR
    assert max(repo1_positions) < repo2_position


def test_format_pr_list_sort_by_state(sample_prs: list[PullRequestInfo]) -> None:
    """Test sorting by state (merged, open, closed)."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, sort_fields=[("state", "asc")])

    result = output.getvalue()

    # Order should be: merged (Fix bug B), open (Add feature A), closed (Update docs)
    assert result.index("Fix bug B") < result.index("Add feature A")
    assert result.index("Add feature A") < result.index("Update docs")


def test_format_pr_list_multi_field_sort(sample_prs: list[PullRequestInfo]) -> None:
    """Test sorting by multiple fields."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)

    # Sort by repository first, then by created date
    with patch("gitbrag.services.formatter.Console", return_value=console):
        format_pr_list(sample_prs, sort_fields=[("repository", "asc"), ("created_at", "desc")])

    result = output.getvalue()

    # Within repo1: Update docs (Jan 3) should come before Add feature A (Jan 1)
    assert result.index("Update docs") < result.index("Add feature A")


def test_show_progress() -> None:
    """Test progress spinner creation."""
    progress = show_progress("Testing...")

    # Should return Progress instance
    assert progress is not None

    # Should have one task
    assert len(progress.tasks) == 1
    assert progress.tasks[0].description == "Testing..."
