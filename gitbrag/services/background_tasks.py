"""Background task management for report generation.

This module wraps FastAPI BackgroundTasks with task tracking and error handling
to provide asynchronous report generation with deduplication.
"""

import hashlib
import json
from datetime import datetime
from logging import getLogger

from fastapi import BackgroundTasks
from pydantic import SecretStr

from gitbrag.services.cache import get_cache
from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.services.reports import calculate_date_range, generate_report_data
from gitbrag.services.task_tracking import can_start_reported_user_task, complete_task, is_task_active, start_task

logger = getLogger(__name__)


def generate_params_hash(show_star_increase: bool = False, **kwargs: bool) -> str:
    """Generate consistent hash from report parameters.

    Uses same algorithm as generate_cache_key() for consistency.

    Args:
        show_star_increase: Whether star increase data is included
        **kwargs: Additional boolean parameters to include in hash

    Returns:
        8-character hex hash of parameters
    """
    params = {"show_star_increase": show_star_increase}
    params.update(kwargs)
    return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]


async def schedule_report_generation(
    background_tasks: BackgroundTasks,
    username: str,
    period: str,
    params_hash: str,
    token: str | None = None,
) -> bool:
    """Schedule background report generation if not already in progress.

    Rate limiting is per reported username (not per authenticated user).
    Only one report generation for a given GitHub username can be active at a time.
    This allows sequential generation to benefit from shared cache for user data.

    Args:
        background_tasks: FastAPI BackgroundTasks instance
        username: GitHub username (subject of the report)
        period: Report period (1_year, 2_years, etc.)
        params_hash: Hash of report parameters
        token: Optional GitHub API token for authenticated requests

    Returns:
        True if task was scheduled, False if already active or rate limited
    """
    task_id = f"{username}:{period}:{params_hash}"

    # Check if task is already active
    if await is_task_active(task_id):
        logger.info(f"Task {task_id} already active, skipping duplicate")
        return False

    # Check if this reported user can start a new task (rate limiting)
    if not await can_start_reported_user_task(username):
        logger.info(f"Rate limit reached for reported user {username}, skipping task scheduling")
        return False

    # Register task start
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": datetime.now().timestamp(),
    }

    if not await start_task(task_id, metadata):
        logger.warning(f"Failed to register task {task_id} (may have been started by another process)")
        return False

    # Schedule background task
    background_tasks.add_task(
        generate_report_background,
        task_id=task_id,
        username=username,
        period=period,
        params_hash=params_hash,
        token=token,
    )

    logger.info(f"Scheduled background task {task_id}")
    return True


async def generate_report_background(
    task_id: str,
    username: str,
    period: str,
    params_hash: str,
    token: str | None,
) -> None:
    """Background task that generates report and updates cache.

    Ensures task cleanup on success or failure. This function is designed to
    fail gracefully without affecting the user's request.

    Args:
        task_id: Task identifier
        username: GitHub username (subject of the report)
        period: Report period
        params_hash: Hash of report parameters
        token: Optional GitHub API token
    """
    try:
        logger.info(f"Starting background report generation for {task_id}")

        # Create authenticated client if token provided
        github_client = None
        if token:
            github_client = GitHubAPIClient(token=SecretStr(token))

        # Generate report
        since, until = calculate_date_range(period)
        show_star_increase = True  # Default for web interface

        # generate_report_data requires a client, skip if not available
        if not github_client:
            logger.warning(f"No GitHub client available for task {task_id}, cannot generate report")
            return

        report_data = await generate_report_data(
            github_client=github_client,
            username=username,
            since=since,
            until=until,
            show_star_increase=show_star_increase,
            period=period,
            exclude_closed_unmerged=True,
        )

        # Update cache using same key format as reports.py
        cache = get_cache("persistent")
        # Recreate cache key using same logic as generate_cache_key
        params = {"show_star_increase": show_star_increase}
        cache_params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
        cache_key = f"report:{username}:{period}:{cache_params_hash}"
        meta_key = f"{cache_key}:meta"

        metadata = {
            "created_at": datetime.now().timestamp(),
            "created_by": "background_task",
            "since": since.isoformat(),
            "until": until.isoformat(),
        }

        await cache.set(cache_key, report_data)
        await cache.set(meta_key, metadata)

        logger.info(f"Successfully completed background task {task_id}, updated cache {cache_key}")

    except Exception as e:
        logger.exception(f"Background task {task_id} failed: {e}")
        # Don't raise - background tasks should fail gracefully

    finally:
        # Always clean up task tracking
        await complete_task(task_id)
