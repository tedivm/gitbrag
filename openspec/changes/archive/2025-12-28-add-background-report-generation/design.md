# Design: Background Report Generation

## Architecture Overview

This design implements asynchronous report generation using FastAPI's native BackgroundTasks feature combined with Redis-based task tracking for deduplication and rate limiting.

## Component Design

### 1. Task Tracking Service

**Location**: `gitbrag/services/task_tracking.py`

Manages active task state in Redis to prevent duplicate generation and enforce per-user limits.

**Key Operations**:

- `is_task_active(task_id: str) -> bool`: Check if task is currently running
- `start_task(task_id: str, metadata: dict) -> bool`: Register task start (returns False if already active)
- `complete_task(task_id: str) -> None`: Mark task as complete and clean up
- `get_reported_user_active_tasks(reported_username: str) -> list[str]`: Get all active tasks for a reported GitHub user
- `can_start_reported_user_task(reported_username: str) -> bool`: Check if reported user can have new task (rate limit check)

**Redis Key Patterns**:

```text
task:report:{username}:{period}:{params_hash}  # Individual task tracking
  Value: JSON metadata (started_at, username, worker_id)
  TTL: 300 seconds (auto-cleanup if task hangs)

task:user:{reported_username}:active  # Reported user's active tasks
  Value: SET of task IDs generating reports for this GitHub user
  TTL: 300 seconds per task
  Note: Key is the USERNAME BEING REPORTED ON, not the authenticated requester
```

**Atomic Operations**:

Use Redis SET NX (set if not exists) for task registration to prevent race conditions:

```python
# Pseudo-code
def start_task(task_id: str, metadata: dict) -> bool:
    key = f"task:report:{task_id}"
    result = await redis.set(key, json.dumps(metadata), nx=True, ex=300)
    if result:
        # Successfully registered task
        reported_username = metadata["username"]  # The user being reported on
        await redis.sadd(f"task:user:{reported_username}:active", task_id)
        return True
    return False  # Task already active
```

### 2. Background Task Manager

**Location**: `gitbrag/services/background_tasks.py`

Wraps FastAPI BackgroundTasks with task tracking and error handling.

**Key Functions**:

```python
async def schedule_report_generation(
    background_tasks: BackgroundTasks,
    username: str,
    period: str,
    params_hash: str,
    token: str | None = None,
) -> bool:
    """
    Schedule background report generation if not already in progress.

    Rate limiting is per reported username (not per authenticated user).
    Only one report generation for a given GitHub username can be active at a time.
    This allows sequential generation to benefit from shared cache for user data.

    Returns:
        bool: True if task was scheduled, False if already active
    """
    task_id = f"{username}:{period}:{params_hash}"

    # Check if this reported user can start new task
    # (username here is the GitHub user being reported on)
    if not await can_start_reported_user_task(username):
        logger.info(f"Reported user {username} already has active task, skipping")
        task_id=task_id,
        username=username,
        period=period,
        params_hash=params_hash,
        token=token,
    )

    return True


async def generate_report_background(
    task_id: str,
    username: str,
    period: str,
    params_hash: str,
    token: str | None,
) -> None:
    """
    Background task that generates report and updates cache.

    Ensures task cleanup on success or failure.
    """
    try:
        logger.info(f"Starting background report generation for {task_id}")

        # Create authenticated client if token provided
        github_client = None
        if token:
            github_client = GitHubAPIClient(token=SecretStr(token))

        # Generate report
        since, until = calculate_date_range(period)
        report_data = await generate_report_data(
            github_client=github_client,
            username=username,
            since=since,
            until=until,
            show_star_increase=True,
            period=period,
            exclude_closed_unmerged=True,
        )

        # Update cache
        cache = get_cache("persistent")
        cache_key = generate_cache_key(username, period, show_star_increase=True)
        meta_key = f"{cache_key}:meta"

        metadata = {
            "created_at": datetime.now().timestamp(),
            "created_by": username,
            "since": since.isoformat(),
            "until": until.isoformat(),
        }

        await cache.set(cache_key, report_data)
        await cache.set(meta_key, metadata)

        logger.info(f"Successfully completed background task {task_id}")

    except Exception as e:
        logger.exception(f"Background task {task_id} failed: {e}")
        # Don't raise - background tasks should fail gracefully

    finally:
        # Always clean up task tracking
        await complete_task(task_id)
```

### 3. Modified Request Handler

**Location**: `gitbrag/www.py` - `user_report()` function

**New Flow**:

```python
@app.get("/user/github/{username}")
async def user_report(
    request: Request,
    username: str,
    period: str = Query(default="1_year"),
    force: bool = Query(default=False),
    github_client: GitHubAPIClient | None = Depends(get_optional_github_client),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Response:
    period = normalize_period(period)
    token_str = github_client.token if github_client else None

    # Get cached report
    cache = get_cache("persistent")
    cache_key = generate_cache_key(username, period, show_star_increase=True)
    cached_data = await cache.get(cache_key)
    cached_meta = await cache.get(f"{cache_key}:meta")

    # Calculate cache state
    cache_age = None
    is_stale = False
    is_regenerating = False

    if cached_meta:
        cache_age = datetime.now().timestamp() - cached_meta["created_at"]
        is_stale = cache_age >= settings.report_cache_stale_age

    # Check if already regenerating
    task_id = f"{username}:{period}:{generate_params_hash(...)}"
    is_regenerating = await is_task_active(task_id)

    # Decide whether to schedule background regeneration
    should_regenerate = False

    if force and token_str:
        # Force refresh requested by authenticated user
        should_regenerate = True
    elif is_stale and token_str and not is_regenerating:
        # Auto-refresh stale cache if authenticated and not already regenerating
        should_regenerate = True
    elif not cached_data and token_str and not is_regenerating:
        # No cache and authenticated - generate
        should_regenerate = True

    # Schedule background task if needed
    if should_regenerate:
        scheduled = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=generate_params_hash(...),
            token=token_str,
        )
        if scheduled:
            is_regenerating = True

    # Determine response based on state
    if not cached_data:
        if not token_str:
            # No cache, no auth - prompt login
            return render_error_template(..., "Login to generate")
        else:
            # No cache, generating - show loading message
            return render_generating_template(...)

    # Serve cached data
    return templates.TemplateResponse(
        ...,
        context={
            ...,
            "is_regenerating": is_regenerating,
            "is_stale": is_stale,
            "cache_age": cache_age,
        },
    )
```

### 4. Template Updates

**Location**: `gitbrag/templates/user_report.html`

**New UI Elements**:

```html
{% if is_regenerating %}
<div class="alert alert-info regenerating-notice">
    <span class="spinner"></span>
    This report is being updated with the latest data.
    Refresh this page in a few moments to see the updated report.
</div>
{% elif is_stale and not authenticated %}
<div class="alert alert-warning stale-notice">
    This report was last updated {{ cache_age }} ago.
    <a href="/auth/login?return_to={{ request.url }}" class="btn btn-primary">
        Login to Refresh
    </a>
</div>
{% elif is_stale %}
<div class="alert alert-warning stale-notice">
    This report was last updated {{ cache_age }} ago.
    <a href="?force=true" class="btn btn-primary">Refresh Now</a>
</div>
{% endif %}
```

**CSS for Loading Spinner**:

```css
.regenerating-notice {
    background-color: #d1ecf1;
    border-color: #bee5eb;
    padding: 1rem;
    border-radius: 0.25rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}

.spinner {
    display: inline-block;
    width: 1.5rem;
    height: 1.5rem;
    border: 3px solid rgba(0,0,0,.1);
    border-radius: 50%;
    border-top-color: #007bff;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

## Data Flow Diagrams

### Flow 1: Authenticated User with Stale Cache

```
User Request → Check Cache → Cache Stale
             ↓
Schedule Background Task → Serve Stale Cache with "Regenerating" Notice
             ↓
Background Task → Generate Report → Update Cache → Complete Task
             ↓
User Refreshes → Serve Fresh Cache
```

### Flow 2: Unauthenticated User with Stale Cache

```
User Request → Check Cache → Cache Stale
             ↓
Serve Stale Cache with "Login to Refresh" Button
(No background task scheduled)
```

### Flow 3: Authenticated User with No Cache

```
User Request → Check Cache → No Cache
             ↓
Schedule Background Task → Show "Generating Report" Message
             ↓
Background Task → Generate Report → Update Cache → Complete Task
             ↓
User Refreshes → Serve Fresh Cache
```

### Flow 4: Concurrent Requests (Deduplication)

```
User A Request → Check Cache → Stale → Check Task Active → Task Not Active
               ↓
Schedule Task → Start Task (SET NX) → Success → Run Generation
               ↓
User B Request (same report) → Check Cache → Stale → Check Task Active → Task Active
               ↓
Serve Stale Cache with "Regenerating" Notice (No new task scheduled)
```

## Error Handling

### Task Failures

Background tasks must fail gracefully without affecting the user's current request:

1. **Exception in background task**: Logged, task cleaned up, cache remains unchanged
2. **GitHub API errors**: Logged, task cleaned up, old cache remains valid
3. **Task timeout**: Redis TTL automatically cleans up after 5 minutes
4. **Redis connection loss**: Task tracking fails open (allows duplicate tasks), regeneration still succeeds

### Recovery Strategies

- **Hung tasks**: Redis TTL (300s) auto-expires task keys
- **Failed generations**: Old cache remains available, users can retry with force=true
- **Partial updates**: Use atomic cache updates (write to temp key, rename)

## Performance Considerations

### Resource Limits

- **Max concurrent background tasks**: Controlled by FastAPI's default thread pool (typically 40)
- **Per-reported-user limit**: 1 active report generation per reported GitHub username (e.g., only one report for "tedivm" at a time)
- **Rationale**: Sequential generation for the same user allows cache reuse - user profiles, repositories, and PR data can be shared between reports
- **Redis memory**: Task keys are small (~200 bytes), TTL keeps memory bounded
- **GitHub API rate limits**: Shared across all report generations, but per-reported-user limiting reduces redundant calls

### Scaling Considerations

**Current Design (FastAPI BackgroundTasks)**:

- Suitable for: Single-server deployment, moderate traffic
- Limitations: Tasks run in same process, no distribution
- Max throughput: ~40 concurrent generations (thread pool limit)

**Future Migration Path (if needed)**:

If traffic exceeds single-server capacity:

1. Add Celery with Redis backend
2. Convert background task functions to Celery tasks (minimal code changes)
3. Deploy separate worker processes
4. Task tracking infrastructure remains unchanged

## Testing Strategy

### Unit Tests

1. `test_task_tracking.py`: Task start/complete/check operations
2. `test_background_tasks.py`: Task scheduling and deduplication logic
3. `test_reports.py`: Modified report generation with background support

### Integration Tests

1. Test concurrent requests to same report (deduplication)
2. Test per-user rate limiting
3. Test task cleanup on success/failure
4. Test background task execution and cache updates

### E2E Tests

1. User visits stale report → sees "regenerating" message → refreshes → sees fresh data
2. Unauthenticated user sees stale cache with login prompt
3. Multiple users trigger same report → only one generation occurs

### Performance Tests

1. Load test: 100 concurrent requests to same report URL
2. Measure task deduplication rate (should be >95%)
3. Measure cache hit rate before/after (should improve)
4. Measure API call reduction (should be 50-70%)

## Monitoring and Observability

### Logging

Add structured logging for:

- Task scheduling: "Scheduling background task {task_id}"
- Task start: "Starting background task {task_id}"
- Task completion: "Completed background task {task_id} in {duration}s"
- Task failure: "Background task {task_id} failed: {error}"
- Deduplication: "Skipping duplicate task {task_id}"

### Metrics (Future Enhancement)

- Task queue length
- Task completion time distribution
- Task failure rate
- Cache hit rate by period
- Concurrent task count

## Security Considerations

1. **Token handling**: Tokens passed to background tasks remain in memory, not persisted
2. **Rate limiting**: Per-reported-user limits prevent redundant work
3. **Task isolation**: Tasks run with principle of least privilege (only access needed data)
4. **Error messages**: Background task errors logged server-side, not exposed to users

## Open Questions

1. **Auto-refresh interval**: Should popular reports auto-refresh on schedule? (Deferred to future enhancement)
2. **Task status API**: Should we expose `/api/task/{task_id}/status` endpoint? (Deferred)
3. **WebSocket updates**: Real-time completion notifications? (Deferred)
4. **Retry logic**: Should failed tasks auto-retry? (No - user can manually retry with force=true)

## References

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Redis SET NX Documentation](https://redis.io/commands/set/)
- [aiocache Documentation](https://aiocache.readthedocs.io/)
