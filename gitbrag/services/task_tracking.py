"""Task tracking service for background report generation.

This module manages active task state in Redis to prevent duplicate report
generation and enforce per-reported-user rate limits.
"""

import json
from logging import getLogger
from typing import Any

from gitbrag.services.cache import get_cache
from gitbrag.settings import settings

logger = getLogger(__name__)


async def is_task_active(task_id: str) -> bool:
    """Check if a report generation task is currently active.

    Args:
        task_id: Task identifier in format "{username}:{period}:{params_hash}"

    Returns:
        True if task is active, False otherwise
    """
    cache = get_cache("persistent")
    key = f"task:report:{task_id}"
    result = await cache.get(key)
    return result is not None


async def start_task(task_id: str, metadata: dict[str, Any]) -> bool:
    """Register a new task start using atomic-like operation.

    This operation attempts to prevent race conditions in task registration
    by checking if the key exists before setting it.

    Args:
        task_id: Task identifier in format "{username}:{period}:{params_hash}"
        metadata: Task metadata including:
            - username: GitHub username (the subject of the report)
            - period: Report period
            - started_at: Timestamp when task started
            - worker_id: Optional identifier for the worker process

    Returns:
        True if task was successfully registered (key didn't exist),
        False if task is already active (key exists)
    """
    cache = get_cache("persistent")
    key = f"task:report:{task_id}"
    ttl = settings.task_timeout_seconds

    try:
        # Check if key already exists (use get instead of exists for compatibility)
        existing_data = await cache.get(key)
        if existing_data is not None:
            return False

        # Serialize metadata to JSON
        value = json.dumps(metadata)

        # Set the key
        await cache.set(key, value, ttl=ttl)

        # Add to reported user's active tasks
        reported_username = metadata.get("username")
        if reported_username:
            user_key = f"task:user:{reported_username}:active"
            # For memory cache, we store a set as a list
            active_tasks = await cache.get(user_key) or []
            if isinstance(active_tasks, str):
                try:
                    active_tasks = json.loads(active_tasks)
                except (json.JSONDecodeError, TypeError):
                    active_tasks = []
            if not isinstance(active_tasks, list):
                active_tasks = []

            if task_id not in active_tasks:
                active_tasks.append(task_id)
                await cache.set(user_key, json.dumps(active_tasks), ttl=ttl)

            logger.info(f"Started task {task_id} for reported user {reported_username}")
        else:
            logger.info(f"Started task {task_id}")

        return True

    except Exception as e:
        logger.exception(f"Failed to start task {task_id}: {e}")
        return False


async def complete_task(task_id: str) -> None:
    """Mark a task as complete and clean up Redis keys.

    Args:
        task_id: Task identifier in format "{username}:{period}:{params_hash}"
    """
    cache = get_cache("persistent")
    key = f"task:report:{task_id}"

    try:
        # Get metadata to find reported username
        task_data = await cache.get(key)
        if task_data:
            try:
                metadata = json.loads(task_data) if isinstance(task_data, str) else task_data
                reported_username = metadata.get("username")
                if reported_username:
                    # Remove from reported user's active tasks
                    user_key = f"task:user:{reported_username}:active"
                    active_tasks = await cache.get(user_key) or []
                    if isinstance(active_tasks, str):
                        try:
                            active_tasks = json.loads(active_tasks)
                        except (json.JSONDecodeError, TypeError):
                            active_tasks = []
                    if not isinstance(active_tasks, list):
                        active_tasks = []

                    if task_id in active_tasks:
                        active_tasks.remove(task_id)
                        await cache.set(user_key, json.dumps(active_tasks), ttl=settings.task_timeout_seconds)

                    logger.info(f"Completed task {task_id} for reported user {reported_username}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Could not parse task metadata for cleanup: {e}")

        # Delete task key
        await cache.delete(key)
        logger.debug(f"Cleaned up task key {key}")

    except Exception as e:
        logger.exception(f"Failed to complete task {task_id}: {e}")


async def get_reported_user_active_tasks(reported_username: str) -> list[str]:
    """Get list of active tasks for a reported GitHub user.

    Note: This tracks tasks for the user being reported on, not the authenticated user.

    Args:
        reported_username: GitHub username that is the subject of reports

    Returns:
        List of active task IDs for this reported user
    """
    cache = get_cache("persistent")
    user_key = f"task:user:{reported_username}:active"

    try:
        # Get the stored list
        tasks_data = await cache.get(user_key)
        if tasks_data:
            if isinstance(tasks_data, str):
                try:
                    result: list[str] = json.loads(tasks_data)
                    return result
                except (json.JSONDecodeError, TypeError):
                    return []
            elif isinstance(tasks_data, list):
                return tasks_data
        return []
    except Exception as e:
        logger.exception(f"Failed to get active tasks for reported user {reported_username}: {e}")
        return []


async def can_start_reported_user_task(reported_username: str) -> bool:
    """Check if a new report generation task can be started for a reported user.

    Enforces per-reported-user rate limit to allow only one concurrent task
    per GitHub username being reported on. This allows sequential generation
    to benefit from shared cache (user profiles, repositories, PR data).

    Note: Rate limiting is per reported username (subject of the report),
    not per authenticated user making the request.

    Args:
        reported_username: GitHub username that is the subject of the report

    Returns:
        True if a new task can be started, False if limit is reached
    """
    active_tasks = await get_reported_user_active_tasks(reported_username)
    max_tasks = settings.max_reported_user_concurrent_tasks

    can_start = len(active_tasks) < max_tasks

    if not can_start:
        logger.info(
            f"Rate limit reached for reported user {reported_username}: {len(active_tasks)}/{max_tasks} active tasks"
        )

    return can_start
