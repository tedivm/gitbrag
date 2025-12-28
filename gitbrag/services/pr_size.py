"""PR size categorization utilities."""

from logging import getLogger

logger = getLogger(__name__)


def categorize_pr_size(additions: int | None, deletions: int | None) -> str | None:
    """Categorize PR size based on total lines changed.

    Args:
        additions: Number of lines added (None if unknown)
        deletions: Number of lines deleted (None if unknown)

    Returns:
        Size category string or None if data is missing

    Size Categories:
        - "One Liner": 1 line changed
        - "Small": 2-100 lines changed
        - "Medium": 101-500 lines changed
        - "Large": 501-1500 lines changed
        - "Huge": 1501-5000 lines changed
        - "Massive": 5000+ lines changed
    """
    # Handle missing data
    if additions is None or deletions is None:
        return None

    total_lines = additions + deletions

    if total_lines <= 1:
        return "One Liner"
    elif total_lines <= 100:
        return "Small"
    elif total_lines <= 500:
        return "Medium"
    elif total_lines <= 1500:
        return "Large"
    elif total_lines <= 5000:
        return "Huge"
    else:
        return "Massive"


def get_size_category_color(size_category: str | None) -> str:
    """Get color class for size category badge.

    Args:
        size_category: Size category string

    Returns:
        CSS color class name
    """
    if not size_category:
        return "neutral"

    color_map = {
        "One Liner": "blue",
        "Small": "green",
        "Medium": "yellow",
        "Large": "orange",
        "Huge": "red",
        "Massive": "purple",
    }

    return color_map.get(size_category, "neutral")
