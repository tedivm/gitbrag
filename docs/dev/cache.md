# Caching

This project uses [aiocache](https://aiocache.readthedocs.io/) for caching, providing both in-memory and Redis-backed cache backends with full async/await support.

## Configuration

Caching is configured through the settings module with the following environment variables:

### Cache Control

- **CACHE_ENABLED**: Enable or disable caching (default: `True`)
  - When set to `False`, all cache operations become no-ops without requiring code changes

### Redis Configuration

- **CACHE_REDIS_HOST**: Redis hostname (default: `None`)
  - If not set, the persistent cache falls back to in-memory storage
- **CACHE_REDIS_PORT**: Redis port (default: `6379`)

### Default TTLs

- **CACHE_DEFAULT_TTL**: Default TTL for memory cache in seconds (default: `300` / 5 minutes)
- **CACHE_PERSISTENT_TTL**: Default TTL for persistent cache in seconds (default: `3600` / 1 hour)

## Cache Backends

Two cache backends are configured:

### Memory Cache

- **Alias**: `memory`
- **Implementation**: Always uses in-memory storage
- **Use case**: Fast, ephemeral caching for request-scoped or temporary data
- **Serializer**: Pickle
- **Default TTL**: 300 seconds (configurable via `CACHE_DEFAULT_TTL`)

### Persistent Cache

- **Alias**: `persistent`
- **Implementation**: Uses Redis if `CACHE_REDIS_HOST` is configured, otherwise falls back to in-memory
- **Use case**: Data that needs to persist across restarts or be shared across instances
- **Serializer**: Pickle
- **Default TTL**: 3600 seconds (configurable via `CACHE_PERSISTENT_TTL`)

## Usage

### Basic Cache Operations

```python
from gitbrag.services.cache import get_cached, set_cached, delete_cached, clear_cache

# Get a cached value (uses memory cache by default)
value = await get_cached("my_key")

# Get from persistent cache
value = await get_cached("my_key", alias="persistent")

# Set a cached value with default TTL (5 minutes for memory cache)
await set_cached("my_key", "my_value")

# Set with custom TTL
await set_cached("my_key", "my_value", ttl=300, alias="persistent")

# Delete a cached value
await delete_cached("my_key", alias="persistent")

# Clear entire cache
await clear_cache(alias="persistent")
```

### Using Cache Decorators

You can use aiocache's built-in decorators directly:

```python
from aiocache import cached

@cached(ttl=600, alias="persistent", key_builder=lambda f, *args, **kwargs: f"user:{args[0]}")
async def get_user_data(user_id: int):
    # Expensive operation here
    return await fetch_user_from_database(user_id)
```

### Direct Cache Access

For more control, you can get a cache instance directly:

```python
from gitbrag.services.cache import get_cache

# Get memory cache
cache = get_cache("memory")
await cache.set("key", "value", ttl=300)
value = await cache.get("key")

# Get persistent cache (Redis or fallback to memory)
cache = get_cache("persistent")
await cache.set("key", "value", ttl=3600)
value = await cache.get("key")
```

## Initialization

The cache system must be initialized before use.

### FastAPI

Caches are automatically initialized in the FastAPI startup event. No manual initialization is required.

### Manual Initialization

If you need to initialize caches manually (e.g., in a custom script or CLI command), use:

```python
from gitbrag.services.cache import configure_caches
from gitbrag.settings import settings

configure_caches(settings)
```

## Best Practices

1. **Choose the right backend**:
   - Use `memory` cache for request-scoped or temporary data
   - Use `persistent` cache for data that needs to survive restarts or be shared across instances

2. **Set appropriate TTLs**:
   - Default TTLs are configured via settings and automatically applied
   - Override with custom TTLs only when needed
   - Shorter TTLs for frequently changing data, longer TTLs for stable data

3. **Use meaningful keys**:
   - Include version numbers or namespaces in cache keys to avoid conflicts
   - Example: `user:v1:123` instead of just `123`

4. **Handle cache misses**:
   - Always check if cached data is `None` and have a fallback mechanism
   - Cache operations are safe when caching is disabled

5. **Disable caching in development**:
   - Set `CACHE_ENABLED=False` to disable caching without code changes
   - Useful for debugging or testing uncached behavior

6. **Monitor cache size**:
   - Redis caches can grow large; implement eviction policies and monitor memory usage
   - Use appropriate TTLs to prevent unbounded growth

## Two-Tier Caching Strategy

GitBrag implements a two-tier caching approach for PR enrichment data to balance freshness with efficiency:

### Tier 1: Intermediate Cache (6-hour TTL)

**Purpose**: Cache GitHub API responses for PR file lists

**Implementation**:

- File lists fetched via `/repos/{owner}/{repo}/pulls/{number}/files` API
- Stored with 6-hour TTL (default, configurable via settings)
- Used by `fetch_pr_files()` in `pullrequests.py`

**Benefits**:

- Enables efficient regeneration when users request overlapping time periods
- Example: User generates 1-year report, then 2-year report → reuses cached file lists for first year
- Reduces API calls significantly for frequently accessed PRs
- Fresh enough to capture recent changes

**Configuration**:

```python
# In settings or environment
PR_FILES_CACHE_TTL = 21600  # 6 hours in seconds (default)
```

### Tier 2: Permanent Cache (No TTL)

**Purpose**: Store final computed report data with all aggregated metrics

**Implementation**:

- Final report data with calculated code statistics, language percentages, repo roles
- No expiration - cached permanently
- Used by `generate_report_data()` in `reports.py`

**Benefits**:

- Enables public viewing without authentication (no GitHub API calls needed)
- Extremely fast response times for cached reports
- Reduces API rate limit consumption
- User can share report URLs publicly

**Cache Keys**:

```python
# Report cache key format
f"report:{username}:{since_iso}:{until_iso}:{include_private}"

# Example
"report:octocat:2024-01-01:2024-12-31:false"
```

### Workflow Example

1. **First Request** (user generates 1-year report):
   - Fetch PRs from GitHub Search API
   - For each PR, fetch file list → cache with 6-hour TTL
   - Calculate aggregated metrics (languages, code stats, roles)
   - Store final report → cache permanently
   - Return report

2. **Second Request** (same user, 2-year report, within 6 hours):
   - Fetch PRs from GitHub Search API (includes year 1 + year 2)
   - For year 1 PRs: file lists retrieved from cache (no API calls!)
   - For year 2 PRs: fetch file lists → cache with 6-hour TTL
   - Calculate aggregated metrics across both years
   - Store final report → cache permanently
   - Return report

3. **Public Viewing** (anonymous user views report):
   - Check permanent cache for report key
   - If found: return cached report (no GitHub API calls, no auth needed)
   - If not found: report must be regenerated (requires auth)

### Cache Invalidation

**Intermediate Cache (PR Files)**:

- Automatically expires after 6 hours
- Manual flush: `FLUSHALL` on Redis (development only)
- Reasonable staleness for file lists (PRs don't change often after creation)

**Permanent Cache (Reports)**:

- Never expires automatically
- Manual flush: `FLUSHALL` on Redis (development only)
- Intentional design: historical reports are snapshots in time

### Performance Impact

With two-tier caching:

- **First generation**: ~2-5 seconds for 100 PRs (file fetching dominates)
- **Overlapping regeneration**: ~1-2 seconds (50% cache hit on files)
- **Cached report viewing**: <100ms (instant, no API calls)

## Development vs Production

Configure caching behavior through environment variables:

### Development

```bash
# Disable caching entirely for debugging
export CACHE_ENABLED=False

# Or use caching without Redis (both backends use memory)
export CACHE_REDIS_HOST=
export CACHE_DEFAULT_TTL=60
export CACHE_PERSISTENT_TTL=300

# Or use local Redis
export CACHE_REDIS_HOST=localhost
export CACHE_REDIS_PORT=6379
```

### Production

```bash
# Enable caching with Redis
export CACHE_ENABLED=True
export CACHE_REDIS_HOST=redis-cluster
export CACHE_REDIS_PORT=6379
export CACHE_DEFAULT_TTL=300
export CACHE_PERSISTENT_TTL=3600
```

## Disabling Caches

To disable caching without changing code:

1. **Via Environment Variable**: Set `CACHE_ENABLED=False`
2. **Result**: All cache operations (get, set, delete, clear) become no-ops
3. **Use Cases**:
   - Debugging issues related to stale cache data
   - Testing application behavior without caching
   - Temporary troubleshooting in production

When caching is disabled, your application continues to work normally - cache operations simply don't store or retrieve any data.

## References

- [aiocache Documentation](https://aiocache.readthedocs.io/)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
