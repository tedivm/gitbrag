from logging import getLogger

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .github.models import PullRequestInfo

logger = getLogger(__name__)


def format_pr_list(
    pull_requests: list[PullRequestInfo],
    show_urls: bool = False,
    sort_fields: list[tuple[str, str]] | None = None,
) -> None:
    """Format and display pull request list using Rich library.

    Args:
        pull_requests: List of pull request information
        show_urls: Whether to display PR URLs (default: False)
        sort_fields: List of (field, direction) tuples for sorting (default: [("created_at", "desc")])

    Valid sort fields: repository, state, created_at, merged_at, title, stars
    Valid sort directions: asc, desc
    """
    console = Console()

    if not pull_requests:
        console.print(
            Panel(
                "[yellow]No pull requests found for the specified criteria.[/yellow]",
                title="No Results",
                border_style="yellow",
            )
        )
        return

    # Sort pull requests
    if sort_fields is None:
        sort_fields = [("created_at", "desc")]

    sorted_prs = _sort_pull_requests(pull_requests, sort_fields)

    # Create table
    table = Table(title="Pull Requests", show_header=True, header_style="bold magenta")

    table.add_column("Repository", style="white")

    # Add star increase column if any PR has star_increase data
    has_star_data = any(pr.star_increase is not None for pr in sorted_prs)
    if has_star_data:
        table.add_column("Stars", style="green", no_wrap=True)

    table.add_column("PR #", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("State", style="white", no_wrap=True)
    table.add_column("Created", style="dim", no_wrap=True)
    table.add_column("Merged", style="dim", no_wrap=True)

    if show_urls:
        table.add_column("URL", style="dim")

    # Add rows
    for pr in sorted_prs:
        # Color code based on state
        display_state = pr.get_display_state()
        if display_state == "merged":
            state_display = "[green]merged[/green]"
        elif display_state == "open":
            state_display = "[blue]open[/blue]"
        else:
            state_display = "[yellow]closed[/yellow]"

        # Format dates
        created_str = pr.created_at.strftime("%Y-%m-%d")
        merged_str = pr.merged_at.strftime("%Y-%m-%d") if pr.merged_at else "-"

        row = [pr.repository]

        # Add star increase if data is available
        if has_star_data:
            if pr.star_increase is None:
                star_display = "-"
            elif pr.star_increase == 0:
                star_display = "0"
            else:
                star_display = f"+{pr.star_increase}"
            row.append(star_display)

        row.extend(
            [
                str(pr.number),
                pr.title,
                state_display,
                created_str,
                merged_str,
            ]
        )

        if show_urls:
            row.append(pr.url)

        table.add_row(*row)

    # Display table
    console.print(table)

    # Display summary
    console.print(f"\n[bold]Total:[/bold] {len(sorted_prs)} pull requests")


def _sort_pull_requests(
    pull_requests: list[PullRequestInfo],
    sort_fields: list[tuple[str, str]],
) -> list[PullRequestInfo]:
    """Sort pull requests by specified fields.

    Args:
        pull_requests: List of pull requests to sort
        sort_fields: List of (field, direction) tuples

    Returns:
        Sorted list of pull requests
    """
    sorted_prs = pull_requests.copy()

    # Sort in reverse order of sort_fields to apply primary sort last
    for field, direction in reversed(sort_fields):
        reverse = direction == "desc"

        # Define sort key function
        from datetime import datetime as dt
        from typing import Any

        def get_sort_key(pr: PullRequestInfo) -> Any:
            if field == "repository":
                return pr.repository
            elif field == "state":
                # Sort order: merged, open, closed
                display_state = pr.get_display_state()
                if display_state == "merged":
                    return 0
                elif display_state == "open":
                    return 1
                else:
                    return 2
            elif field == "created_at":
                return pr.created_at
            elif field == "merged_at":
                # None values go to end
                return pr.merged_at if pr.merged_at else (pr.created_at if reverse else dt.max)
            elif field == "title":
                return pr.title.lower()
            elif field == "stars":
                # Sort by star increase, treating None as -1 (sort to end when descending)
                if pr.star_increase is None:
                    return -1 if reverse else 999999
                return pr.star_increase
            else:
                logger.warning(f"Unknown sort field: {field}, ignoring")
                return pr.created_at

        sorted_prs.sort(key=get_sort_key, reverse=reverse)

    return sorted_prs


def show_progress(message: str) -> Progress:
    """Create and return a progress spinner.

    Args:
        message: Message to display with spinner

    Returns:
        Progress context manager
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    )
    progress.add_task(description=message, total=None)
    return progress
