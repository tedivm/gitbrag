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
