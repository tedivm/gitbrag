import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from logging import getLogger
from typing import Any

import typer
from rich.console import Console

from .services.cache import configure_caches
from .services.formatter import format_pr_list, show_progress
from .services.github.auth import GitHubClient
from .services.github.pullrequests import PullRequestCollector
from .settings import settings

# Configure caches on module load
configure_caches()

app = typer.Typer()
logger = getLogger(__name__)
console = Console()


def syncify(f: Callable[..., Any]) -> Callable[..., Any]:
    """This simple decorator converts an async function into a sync function,
    allowing it to work with Typer.
    """

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@app.command(help=f"Display the current installed version of {settings.project_name}.")
def version() -> None:
    from . import __version__

    typer.echo(f"{settings.project_name} - {__version__}")


@app.command(help="Display a friendly greeting.")
def hello() -> None:
    typer.echo(f"Hello from {settings.project_name}!")


@app.command(name="list", help="List pull requests for a GitHub user across all organizations.")
@syncify
async def list_contributions(
    username: str = typer.Argument(
        ...,
        help="GitHub username to fetch contributions for",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Start date for filtering PRs (ISO format YYYY-MM-DD, default: 365 days ago)",
    ),
    until: str | None = typer.Option(
        None,
        "--until",
        help="End date for filtering PRs (ISO format YYYY-MM-DD, default: today)",
    ),
    token: str | None = typer.Option(
        None,
        "--token",
        help="GitHub Personal Access Token (overrides env var)",
    ),
    include_private: bool = typer.Option(
        False,
        "--include-private",
        help="Include private repositories (requires repo scope)",
    ),
    show_urls: bool = typer.Option(
        False,
        "--show-urls",
        help="Display PR URLs in output",
    ),
    show_star_increase: bool = typer.Option(
        False,
        "--show-star-increase",
        help="Display star increase (stars gained during time period) for repositories",
    ),
    sort: list[str] | None = typer.Option(
        None,
        "--sort",
        help="Sort fields (format: field or field:asc/desc). Can be specified multiple times. Valid fields: repository, state, created, merged, title, stars",
    ),
) -> None:
    """List pull requests for a GitHub user across all organizations."""
    try:
        # Parse dates
        since_date = _parse_date(since, default_days_ago=365)
        until_date = _parse_date(until, default_days_ago=0)

        # Validate date range
        if since_date > until_date:
            console.print("[red]Error:[/red] --since date must be before --until date")
            raise typer.Exit(1)

        # Parse and validate sort fields
        sort_fields = _parse_sort_fields(sort, show_star_increase)

        # Authenticate with GitHub
        with show_progress("Authenticating with GitHub..."):
            github_client_factory = GitHubClient(token_override=token)
            github_client = await github_client_factory.get_authenticated_client()

        # Collect pull requests using async context manager
        async with github_client:
            with show_progress(f"Collecting pull requests for {username}..."):
                collector = PullRequestCollector(github_client)
                pull_requests = await collector.collect_user_prs(
                    username=username,
                    since=since_date,
                    until=until_date,
                    include_private=include_private,
                    include_star_increase=show_star_increase,
                )

        # Calculate repository-level roles
        repo_roles = _calculate_repo_roles(pull_requests)

        # Format and display results
        format_pr_list(
            pull_requests,
            show_urls=show_urls,
            sort_fields=sort_fields,
            repo_roles=repo_roles,
        )

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        logger.exception("Unexpected error during PR collection")
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _parse_date(date_str: str | None, default_days_ago: int) -> datetime:
    """Parse date string or return default.

    Args:
        date_str: ISO format date string or None
        default_days_ago: Days ago to use if date_str is None

    Returns:
        Parsed datetime (timezone-aware UTC)

    Raises:
        ValueError: If date string is invalid
    """
    from datetime import timezone

    if date_str is None:
        return datetime.now(timezone.utc) - timedelta(days=default_days_ago)

    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # If the parsed datetime is naive, assume UTC
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: {date_str}. Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        ) from e


def _parse_sort_fields(sort: list[str] | None, show_star_increase: bool = False) -> list[tuple[str, str]]:
    """Parse sort field specifications.

    Args:
        sort: List of sort specs (e.g., ["repository:asc", "created:desc"])
        show_star_increase: Whether star increase display is enabled

    Returns:
        List of (field, direction) tuples

    Raises:
        ValueError: If sort specification is invalid
    """
    if not sort:
        return [("created_at", "desc")]

    valid_fields = {"repository", "state", "created", "merged", "title", "stars"}
    valid_directions = {"asc", "desc"}

    parsed_fields: list[tuple[str, str]] = []

    for spec in sort:
        parts = spec.split(":")
        if len(parts) == 1:
            field = parts[0]
            direction = "desc"
        elif len(parts) == 2:
            field, direction = parts
        else:
            raise ValueError(f"Invalid sort specification: {spec}. Expected format: field or field:direction")

        # Normalize field names (created -> created_at, merged -> merged_at)
        if field == "created":
            field = "created_at"
        elif field == "merged":
            field = "merged_at"

        # Validate stars field requires --show-star-increase
        if field == "stars" and not show_star_increase:
            raise ValueError("Sorting by 'stars' requires --show-star-increase flag")

        if field not in valid_fields and field not in {"created_at", "merged_at"}:
            raise ValueError(f"Invalid sort field: {field}. Valid fields: {', '.join(sorted(valid_fields))}")

        if direction not in valid_directions:
            raise ValueError(f"Invalid sort direction: {direction}. Valid directions: asc, desc")

        parsed_fields.append((field, direction))

    return parsed_fields


def _calculate_repo_roles(pull_requests: list) -> dict[str, str | None]:
    """Calculate repository-level roles from pull requests.

    Uses the author_association from the most recent PR for each repository.

    Args:
        pull_requests: List of PullRequestInfo objects

    Returns:
        Dictionary mapping repository names to roles
    """
    from .services.github.models import PullRequestInfo

    repo_roles: dict[str, str | None] = {}

    # Group PRs by repository and find most recent
    repo_to_prs: dict[str, list[PullRequestInfo]] = {}
    for pr in pull_requests:
        if pr.repository not in repo_to_prs:
            repo_to_prs[pr.repository] = []
        repo_to_prs[pr.repository].append(pr)

    # Get role from most recent PR per repository
    for repo_name, prs in repo_to_prs.items():
        most_recent = max(prs, key=lambda p: p.created_at)
        repo_roles[repo_name] = most_recent.author_association

    return repo_roles


if __name__ == "__main__":
    app()
