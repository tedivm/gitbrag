"""Tests for CLI application."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from gitbrag.cli import app, syncify
from gitbrag.services.github.models import PullRequestInfo

runner = CliRunner()


def test_cli_app_exists():
    """Test that Typer app is properly instantiated."""
    assert app is not None
    assert hasattr(app, "command")


def test_cli_app_has_commands():
    """Test that CLI app has registered commands."""
    assert hasattr(app, "registered_commands")


def test_version_command_exists():
    """Test that version command is registered."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.stdout.lower() or "full_test_project" in result.stdout.lower()


def test_version_command_runs():
    """Test that version command executes successfully."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0


def test_version_output_format():
    """Test that version command outputs correct format."""
    from gitbrag.settings import settings

    result = runner.invoke(app, ["version"])
    assert settings.project_name in result.stdout
    # Should output: "project_name - X.Y.Z"
    assert "-" in result.stdout


def test_version_contains_version_number():
    """Test that version output contains a version number."""
    from gitbrag.settings import settings

    result = runner.invoke(app, ["version"])
    output = result.stdout.strip()
    # Should contain project name and version
    assert settings.project_name in output


def test_help_flag():
    """Test that --help flag works."""
    from gitbrag.settings import settings

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert settings.project_name in result.stdout.lower() or "display" in result.stdout.lower()


def test_help_shows_description():
    """Test that help output shows description."""
    result = runner.invoke(app, ["--help"])
    assert "version" in result.stdout.lower() or "display" in result.stdout.lower()


def test_syncify_decorator_exists():
    """Test that syncify decorator is defined."""
    assert syncify is not None
    assert callable(syncify)


def test_syncify_converts_async_to_sync():
    """Test that syncify properly converts async functions to sync."""

    @syncify
    async def test_async_func():
        await asyncio.sleep(0.01)
        return "success"

    # Should be able to call without await
    result = test_async_func()
    assert result == "success"


def test_syncify_preserves_return_value():
    """Test that syncify preserves the return value."""

    @syncify
    async def test_async_func():
        return 42

    result = test_async_func()
    assert result == 42


def test_syncify_with_arguments():
    """Test that syncify works with function arguments."""

    @syncify
    async def test_async_func(x, y):
        await asyncio.sleep(0.01)
        return x + y

    result = test_async_func(10, 20)
    assert result == 30


def test_syncify_preserves_function_name():
    """Test that syncify preserves the function's name."""

    @syncify
    async def my_function():
        return True

    assert my_function.__name__ == "my_function"


def test_settings_imported():
    """Test that settings can be imported in CLI module."""
    from gitbrag.settings import settings

    assert settings is not None
    assert hasattr(settings, "project_name")


def test_version_uses_settings():
    """Test that version command uses project_name from settings."""
    from gitbrag.settings import settings

    result = runner.invoke(app, ["version"])
    assert settings.project_name in result.stdout


# Tests for list command


@pytest.fixture
def mock_sample_prs() -> list[PullRequestInfo]:
    """Create sample PRs for testing."""
    return [
        PullRequestInfo(
            number=1,
            title="Test PR 1",
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/1",
            state="open",
            created_at=datetime(2024, 1, 1),
            merged_at=None,
            closed_at=None,
            author="testuser",
            organization="owner",
        ),
    ]


def test_list_command_exists() -> None:
    """Test that list command is registered."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout.lower()


def test_list_command_requires_username() -> None:
    """Test that list command requires username argument."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code != 0


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_basic(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test basic list command execution."""
    # Mock GitHub client
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    # Mock PR collector
    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "testuser"])

    assert result.exit_code == 0
    mock_collector.collect_user_prs.assert_called_once()
    mock_format.assert_called_once()


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_with_date_range(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with custom date range."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(
        app,
        ["list", "testuser", "--since", "2024-01-01", "--until", "2024-12-31"],
    )

    assert result.exit_code == 0
    # Verify dates were passed to collector
    call_kwargs = mock_collector.collect_user_prs.call_args.kwargs
    assert "since" in call_kwargs
    assert "until" in call_kwargs


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_include_private(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with --include-private flag."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "testuser", "--include-private"])

    assert result.exit_code == 0
    call_kwargs = mock_collector.collect_user_prs.call_args.kwargs
    assert call_kwargs["include_private"] is True


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_show_urls(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with --show-urls flag."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "testuser", "--show-urls"])

    assert result.exit_code == 0
    call_kwargs = mock_format.call_args.kwargs
    assert call_kwargs["show_urls"] is True


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_with_sort(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with --sort option."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "testuser", "--sort", "repository:asc"])

    assert result.exit_code == 0
    call_kwargs = mock_format.call_args.kwargs
    assert "sort_fields" in call_kwargs
    assert call_kwargs["sort_fields"] == [("repository", "asc")]


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_with_multiple_sort(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with multiple --sort flags."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(
        app,
        ["list", "testuser", "--sort", "repository", "--sort", "created:desc"],
    )

    assert result.exit_code == 0
    call_kwargs = mock_format.call_args.kwargs
    sort_fields = call_kwargs["sort_fields"]
    assert len(sort_fields) == 2
    assert ("repository", "desc") in sort_fields
    assert ("created_at", "desc") in sort_fields


@patch("gitbrag.cli.GitHubClient")
def test_list_command_invalid_sort_field(mock_client_class: MagicMock) -> None:
    """Test list command with invalid sort field."""
    result = runner.invoke(app, ["list", "testuser", "--sort", "invalid:asc"])
    assert result.exit_code != 0
    assert "Invalid sort field" in result.stdout


@patch("gitbrag.cli.GitHubClient")
def test_list_command_invalid_sort_direction(mock_client_class: MagicMock) -> None:
    """Test list command with invalid sort direction."""
    result = runner.invoke(app, ["list", "testuser", "--sort", "repository:invalid"])
    assert result.exit_code != 0
    assert "Invalid sort direction" in result.stdout


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_with_token_override(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with --token override."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "testuser", "--token", "custom_token"])

    assert result.exit_code == 0
    # Verify token override was passed to GitHubClient
    mock_client_class.assert_called_once_with(token_override="custom_token")


def test_list_command_invalid_date_format() -> None:
    """Test list command with invalid date format."""
    result = runner.invoke(app, ["list", "testuser", "--since", "not-a-date"])
    assert result.exit_code != 0
    assert "Invalid date format" in result.stdout


@patch("gitbrag.cli.GitHubClient")
def test_list_command_since_after_until(mock_client_class: MagicMock) -> None:
    """Test list command with --since date after --until date."""
    result = runner.invoke(
        app,
        ["list", "testuser", "--since", "2024-12-31", "--until", "2024-01-01"],
    )
    assert result.exit_code != 0
    assert "--since date must be before --until date" in result.stdout


@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_user_not_found(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
) -> None:
    """Test list command with non-existent user."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(side_effect=ValueError("User 'nonexistent' not found"))
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "nonexistent"])

    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.stdout


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_combined_flags(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test list command with multiple flags combined."""
    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(
        app,
        ["list", "testuser", "--include-private", "--show-urls", "--sort", "repository:asc"],
    )

    assert result.exit_code == 0

    collector_kwargs = mock_collector.collect_user_prs.call_args.kwargs
    assert collector_kwargs["include_private"] is True

    format_kwargs = mock_format.call_args.kwargs
    assert format_kwargs["show_urls"] is True
    assert format_kwargs["sort_fields"] == [("repository", "asc")]


def test_cache_configured_on_cli_import() -> None:
    """Test that caches are configured when CLI module is imported."""
    from aiocache import caches

    # Re-configure caches by calling configure_caches directly
    # (since cli module might already be imported and cached)
    from gitbrag.services.cache import configure_caches

    configure_caches()

    # Verify that cache aliases are configured
    cache_config = caches.get_config()
    assert "default" in cache_config
    assert "memory" in cache_config
    assert "persistent" in cache_config

    # Verify we can get each cache without error
    default_cache = caches.get("default")
    assert default_cache is not None

    memory_cache = caches.get("memory")
    assert memory_cache is not None

    persistent_cache = caches.get("persistent")
    assert persistent_cache is not None


def test_parse_date_returns_timezone_aware() -> None:
    """Test that _parse_date returns timezone-aware datetimes."""
    from datetime import timezone

    from gitbrag.cli import _parse_date

    # Test with None (default)
    default_date = _parse_date(None, default_days_ago=365)
    assert default_date.tzinfo is not None
    assert default_date.tzinfo == timezone.utc

    # Test with ISO string (naive)
    parsed_date = _parse_date("2024-12-15", default_days_ago=0)
    assert parsed_date.tzinfo is not None
    assert parsed_date.tzinfo == timezone.utc

    # Test with ISO string (aware)
    parsed_aware = _parse_date("2024-12-15T10:30:00+00:00", default_days_ago=0)
    assert parsed_aware.tzinfo is not None


def test_parse_date_naive_assumed_utc() -> None:
    """Test that naive date strings are assumed to be UTC."""
    from datetime import timezone

    from gitbrag.cli import _parse_date

    parsed = _parse_date("2024-12-15T10:30:00", default_days_ago=0)
    assert parsed.tzinfo == timezone.utc
    assert parsed.year == 2024
    assert parsed.month == 12
    assert parsed.day == 15
    assert parsed.hour == 10
    assert parsed.minute == 30


@patch("gitbrag.cli.format_pr_list")
@patch("gitbrag.cli.PullRequestCollector")
@patch("gitbrag.cli.GitHubClient")
def test_list_command_dates_are_timezone_aware(
    mock_client_class: MagicMock,
    mock_collector_class: MagicMock,
    mock_format: MagicMock,
    mock_sample_prs: list[PullRequestInfo],
) -> None:
    """Test that dates passed to collector are timezone-aware."""
    from datetime import timezone

    mock_client_instance = MagicMock()
    mock_github = MagicMock()
    mock_client_instance.get_authenticated_client = AsyncMock(return_value=mock_github)
    mock_client_class.return_value = mock_client_instance

    mock_collector = MagicMock()
    mock_collector.collect_user_prs = AsyncMock(return_value=mock_sample_prs)
    mock_collector_class.return_value = mock_collector

    result = runner.invoke(app, ["list", "testuser", "--since", "2024-01-01", "--until", "2024-12-31"])

    assert result.exit_code == 0

    # Verify dates passed to collector are timezone-aware
    collector_kwargs = mock_collector.collect_user_prs.call_args.kwargs
    since_date = collector_kwargs["since"]
    until_date = collector_kwargs["until"]

    assert since_date.tzinfo is not None
    assert since_date.tzinfo == timezone.utc
    assert until_date.tzinfo is not None
    assert until_date.tzinfo == timezone.utc


def test_calculate_repo_roles_basic():
    """Test calculating repository roles from PRs."""
    from gitbrag.cli import _calculate_repo_roles

    prs = [
        PullRequestInfo(
            number=1,
            title="PR 1",
            repository="owner/repo1",
            url="https://github.com/owner/repo1/pull/1",
            state="open",
            created_at=datetime(2024, 1, 1),
            merged_at=None,
            closed_at=None,
            author="testuser",
            organization="owner",
            author_association="OWNER",
        ),
        PullRequestInfo(
            number=2,
            title="PR 2",
            repository="owner/repo2",
            url="https://github.com/owner/repo2/pull/2",
            state="merged",
            created_at=datetime(2024, 1, 2),
            merged_at=datetime(2024, 1, 3),
            closed_at=datetime(2024, 1, 3),
            author="testuser",
            organization="owner",
            author_association="CONTRIBUTOR",
        ),
    ]

    repo_roles = _calculate_repo_roles(prs)

    assert repo_roles == {
        "owner/repo1": "OWNER",
        "owner/repo2": "CONTRIBUTOR",
    }


def test_calculate_repo_roles_uses_most_recent():
    """Test that _calculate_repo_roles uses the most recent PR for each repo."""
    from gitbrag.cli import _calculate_repo_roles

    prs = [
        PullRequestInfo(
            number=1,
            title="Older PR",
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/1",
            state="merged",
            created_at=datetime(2024, 1, 1),
            merged_at=datetime(2024, 1, 2),
            closed_at=datetime(2024, 1, 2),
            author="testuser",
            organization="owner",
            author_association="CONTRIBUTOR",
        ),
        PullRequestInfo(
            number=2,
            title="Newer PR",
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/2",
            state="open",
            created_at=datetime(2024, 6, 1),
            merged_at=None,
            closed_at=None,
            author="testuser",
            organization="owner",
            author_association="MEMBER",
        ),
    ]

    repo_roles = _calculate_repo_roles(prs)

    # Should use MEMBER from the newer PR
    assert repo_roles == {"owner/repo": "MEMBER"}


def test_calculate_repo_roles_handles_none():
    """Test that _calculate_repo_roles handles None author_association."""
    from gitbrag.cli import _calculate_repo_roles

    prs = [
        PullRequestInfo(
            number=1,
            title="PR without role",
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/1",
            state="open",
            created_at=datetime(2024, 1, 1),
            merged_at=None,
            closed_at=None,
            author="testuser",
            organization="owner",
            author_association=None,
        ),
    ]

    repo_roles = _calculate_repo_roles(prs)

    assert repo_roles == {"owner/repo": None}
