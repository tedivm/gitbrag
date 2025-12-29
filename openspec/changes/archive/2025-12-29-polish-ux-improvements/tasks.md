# Implementation Tasks

This document breaks down the Polish UX Improvements change into ordered, verifiable tasks.

## Task List

### 1. Add get_user_social_accounts method to GitHubAPIClient

**Description**: Implement new method in `GitHubAPIClient` to fetch social accounts from GitHub API.

**Details**:

- Add `async def get_user_social_accounts(self, username: str) -> list[dict[str, Any]]` method
- Make GET request to `{base_url}/users/{username}/social_accounts`
- Use existing `_request_with_retry()` for rate limiting and timeout handling
- Return list of dicts with `provider` and `url` keys
- Handle 404 responses gracefully (return empty list)
- Add proper type hints and docstring
- Location: `gitbrag/services/github/client.py`

**Validation**:

- Method signature matches spec
- Returns list of social account dictionaries
- Handles errors without raising exceptions (logs and returns empty list)
- Uses retry logic for rate limiting

**Dependencies**: None

**Parallelizable**: Yes (can be done independently)

---

### 2. Modify get_or_fetch_user_profile to fetch social accounts

**Description**: Update `get_or_fetch_user_profile()` function to call social accounts API and merge results into profile dict.

**Details**:

- Call `client.get_user_social_accounts(username)` when fetching user profile
- Merge social accounts into profile dict with key `social_accounts`
- Maintain same caching behavior (1-hour TTL with authenticated requests)
- Log social accounts fetch with `logger.debug()`
- Handle API failures gracefully (continue with profile even if social accounts fail)
- Location: `gitbrag/services/reports.py`

**Validation**:

- Profile dict includes `social_accounts` key with list value
- Caching behavior unchanged
- Errors logged but don't break profile fetch
- Manual test: View user report and check cached profile includes social accounts

**Dependencies**: Task 1 (get_user_social_accounts method)

**Parallelizable**: No (depends on Task 1)

---

### 3. Update user_report.html template for social media links

**Description**: Add rendering logic for Mastodon, LinkedIn, and Bluesky links in user profile section.

**Details**:

- Update `gitbrag/templates/user_report.html` in user metadata section
- Add conditional blocks for each social account provider:
  - Check `user_profile.social_accounts` exists and is not empty
  - Iterate through social accounts array
  - Match on `provider` field (mastodon, linkedin, bluesky)
  - Render link with appropriate icon and target="_blank"
- Use emojis or text icons: Mastodon 🐘, LinkedIn 💼, Bluesky 🦋
- Maintain consistent styling with existing blog and Twitter links
- Ensure links work when social_accounts is missing or empty

**Validation**:

- Social media links display for users with configured accounts
- Links open in new tabs
- Icons are appropriate and visible
- Template doesn't break when social_accounts missing
- Manual test: View reports for users with/without social accounts

**Dependencies**: Task 2 (profile includes social_accounts)

**Parallelizable**: No (depends on Task 2)

---

### 4. Add username normalization to generate_cache_key

**Description**: Modify `generate_cache_key()` function to lowercase username parameter.

**Details**:

- Add `username = username.lower()` at start of function
- Ensure cache key uses lowercase username in format
- Add comment explaining normalization
- Location: `gitbrag/services/reports.py`

**Validation**:

- Cache key generated uses lowercase username
- Test: `generate_cache_key("TedIVM", "1_year")` returns `report:tedivm:1_year:{hash}`
- Existing tests continue to pass

**Dependencies**: None

**Parallelizable**: Yes (independent of other tasks)

---

### 5. Add username normalization to get_or_fetch_user_profile

**Description**: Modify `get_or_fetch_user_profile()` function to lowercase username parameter for cache key.

**Details**:

- Add `username_lower = username.lower()` near start of function
- Use `username_lower` for cache key generation: `cache_key = f"profile:{username_lower}"`
- Continue using original `username` for GitHub API call (GitHub is case-preserving)
- Add comment explaining normalization
- Location: `gitbrag/services/reports.py`

**Validation**:

- Cache key uses lowercase username
- GitHub API receives original case username
- Test: Calling function with "TedIVM" creates `profile:tedivm` cache key
- Profile fetch still works correctly

**Dependencies**: None

**Parallelizable**: Yes (independent of other tasks)

---

### 6. Add username redirect in user_report route

**Description**: Add redirect logic to `user_report()` route to normalize uppercase usernames to lowercase URLs.

**Details**:

- Check if `username` parameter contains uppercase characters
- If uppercase detected:
  - Generate lowercase version with `username_lower = username.lower()`
  - Build redirect URL with `quote()` for URL safety
  - Preserve query parameters (period, force, etc.)
  - Return `RedirectResponse(url=redirect_url, status_code=301)`
- Add early in function before cache/profile logic
- Log redirect with `logger.debug()`
- Location: `gitbrag/www.py` in `user_report()` function

**Validation**:

- Accessing `/user/github/TedIVM` redirects to `/user/github/tedivm`
- Query parameters preserved: `/user/github/TedIVM?period=2_years` → `/user/github/tedivm?period=2_years`
- Status code is 301 (permanent redirect)
- Lowercase usernames process without redirect
- Manual test: Visit uppercase URL in browser, verify redirect

**Dependencies**: Tasks 4 and 5 (cache normalization in place)

**Parallelizable**: No (should follow cache normalization)

---

### 7. Update empty state message in user_report.html

**Description**: Replace neutral empty state message with encouraging version.

**Details**:

- Locate empty state section in `gitbrag/templates/user_report.html`
- Current message: "No pull requests found for this period."
- New message: "No pull requests found for this period. Every open source journey starts somewhere—your next contribution is waiting! 🚀"
- Maintain existing HTML structure and CSS classes
- Ensure message displays in correct location (where repository list would appear)

**Validation**:

- New message displays when no PRs found
- Message tone is encouraging and professional
- Emoji renders correctly
- Page layout remains consistent
- Manual test: Generate report for user with no PRs in specified period

**Dependencies**: None

**Parallelizable**: Yes (independent template change)

---

### 8. Rewrite README.md

**Description**: Reorganize README to lead with hosted service while preserving all existing information.

**Details**:

- Lead with GitBrag description and value proposition
- Add prominent link to gitbrag.tedivm.com with call-to-action
- Highlight web interface benefits (OAuth, no token setup, caching, sharing)
- Move CLI documentation to secondary section (after web interface)
- Reorganize structure:
  1. Title and description
  2. Hosted service call-to-action
  3. Features
  4. Web interface quick start
  5. CLI installation and usage
  6. Configuration
  7. Development documentation links
- Ensure no loss in data (installation, CLI options, Docker, env vars), but feel free to rewrite
- Improve readability with clear section headings
- Maintain professional, welcoming tone

**Validation**:

- README leads with hosted service
- gitbrag.tedivm.com link is prominent and functional
- All existing information preserved
- Sections flow logically
- Writing is clear and concise
- Manual review by team member or user testing
- Check that links work and formatting renders correctly

**Dependencies**: None

**Parallelizable**: Yes (documentation update independent of code)

---

### 9. Add test for username redirect

**Description**: Add test case in `tests/test_www.py` to verify uppercase username redirects.

**Details**:

- Test function: `test_username_redirect_to_lowercase()`
- Use FastAPI test client
- Test scenarios:
  - Uppercase username redirects to lowercase with 301 status
  - Query parameters preserved in redirect
  - Mixed case username redirects
  - Lowercase username doesn't redirect (200 status)
- Verify redirect URL format and status code

**Validation**:

- New test passes
- Test covers all redirect scenarios
- Existing tests continue to pass
- Run with `pytest tests/test_www.py::test_username_redirect_to_lowercase`

**Dependencies**: Task 6 (redirect implemented)

**Parallelizable**: No (depends on implementation)

---

### 10. Add test for cache key normalization

**Description**: Add test case to verify cache keys use lowercase usernames.

**Details**:

- Create `tests/services/test_reports.py` if doesn't exist, or add to existing
- Test function: `test_generate_cache_key_normalizes_username()`
- Test scenarios:
  - Uppercase username produces lowercase cache key
  - Mixed case produces lowercase cache key
  - Lowercase username unchanged
- Verify cache key format matches expected pattern

**Validation**:

- Test passes
- Cache key normalization verified
- Existing cache tests pass
- Run with `pytest tests/ -k test_generate_cache_key`

**Dependencies**: Task 4 (cache key normalization implemented)

**Parallelizable**: No (depends on implementation)

---

### 11. Add test for social accounts API client method

**Description**: Add test for `get_user_social_accounts()` method in GitHub API client.

**Details**:

- Location: `tests/services/test_github_client.py` (create if needed)
- Test function: `test_get_user_social_accounts()`
- Mock GitHub API response with httpx_mock or similar
- Test scenarios:
  - Successful response returns list of social accounts
  - Empty response returns empty list
  - 404 response returns empty list
  - Rate limiting is handled with retries
- Verify response format matches expected structure

**Validation**:

- Test passes with mocked responses
- Method handles all edge cases
- Retry logic verified
- Run with `pytest tests/services/test_github_client.py`

**Dependencies**: Task 1 (method implemented)

**Parallelizable**: No (depends on implementation)

---

### 12. Add test for social accounts in template

**Description**: Add test to verify social media links render in user report template.

**Details**:

- Location: `tests/test_www.py`
- Test function: `test_social_media_links_display()`
- Mock user profile with social_accounts data
- Verify template renders:
  - Mastodon link with correct URL and icon
  - LinkedIn link with correct URL and icon
  - Bluesky link with correct URL and icon
- Test that template doesn't break when social_accounts missing
- Verify links have `target="_blank"` attribute

**Validation**:

- Template renders social media links correctly
- Missing social accounts handled gracefully
- HTML structure is valid
- Run with `pytest tests/test_www.py::test_social_media_links_display`

**Dependencies**: Task 3 (template updated)

**Parallelizable**: No (depends on template changes)

---

### 13. Manual testing and validation

**Description**: Perform end-to-end manual testing of all changes in development environment.

**Details**:

- Start development environment: `docker compose up`
- Test username normalization:
  - Visit `/user/github/TEDIVM` and verify redirect
  - Verify cache entries use lowercase keys (check Redis)
  - Test with multiple case variations
- Test social media links:
  - View report for user with social accounts (e.g., tedivm)
  - Verify Mastodon, LinkedIn, Bluesky links display
  - Click links to ensure they work and open in new tabs
  - Test user without social accounts (ensure no errors)
- Test empty state message:
  - Generate report for user with no PRs in selected period
  - Verify encouraging message displays
  - Check message styling and tone
- Review README:
  - Read through rewritten README
  - Check that hosted service is prominent
  - Verify all links work
  - Ensure information is clear and well-organized

**Validation**:

- All features work as expected in live environment
- No console errors or warnings
- Cache behavior is correct
- Links and redirects work properly
- README is clear and actionable

**Dependencies**: All implementation tasks (1-8)

**Parallelizable**: No (final integration test)

---

### 14. Update development documentation

**Description**: Add documentation for new behaviors in developer docs.

**Details**:

- Update `docs/dev/web.md`:
  - Document username normalization and redirect behavior
  - Note that cache keys are lowercase
  - Explain 301 redirect for uppercase usernames
- Update `docs/dev/github-api.md`:
  - Document `/users/{username}/social_accounts` endpoint
  - Describe social account data structure
  - Note caching behavior for social accounts
- Update `docs/dev/templates.md` (if exists) or add section to `web.md`:
  - Document new social media link rendering
  - Describe empty state message change

**Validation**:

- Documentation is accurate and complete
- Examples are clear
- Format matches existing documentation style
- Links and references are correct

**Dependencies**: All implementation tasks

**Parallelizable**: No (should document after implementation)

---

## Task Sequencing

### Parallel Track 1: Social Media Expansion

1. Task 1: Add get_user_social_accounts method
2. Task 2: Modify get_or_fetch_user_profile
3. Task 3: Update user_report.html template
4. Task 11: Add test for social accounts API
5. Task 12: Add test for template rendering

### Parallel Track 2: Username Normalization

1. Task 4: Normalize in generate_cache_key
2. Task 5: Normalize in get_or_fetch_user_profile
3. Task 6: Add redirect in user_report route
4. Task 9: Add test for redirect
5. Task 10: Add test for cache key normalization

### Parallel Track 3: Independent Changes

1. Task 7: Update empty state message (can run anytime)
2. Task 8: Rewrite README (can run anytime)

### Final Integration

1. Task 13: Manual testing (after all implementations)
2. Task 14: Update documentation (after implementations)

**Notes:**

- Tracks 1 and 2 can run in parallel
- Track 3 items are independent and can be done anytime
- Testing tasks should follow their respective implementation tasks
- Final integration testing requires all tracks complete
