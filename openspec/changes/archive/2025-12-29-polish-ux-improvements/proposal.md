# Proposal: Polish UX Improvements

## Overview

This change addresses four small UX improvements to make GitBrag more professional and user-friendly:

1. **Username Normalization**: Standardize cache keys to lowercase usernames and redirect uppercase URLs to lowercase for consistency
2. **Expanded Social Media Links**: Display all available social media profiles (Mastodon, LinkedIn, Bluesky) by calling the GitHub `/users/{username}/social_accounts` API endpoint, not just Twitter and blog URL
3. **Encouraging Empty State Message**: When no pull requests are found, display an encouraging message rather than just "No pull requests found"
4. **README Website Focus**: Rewrite README to highlight the hosted service at gitbrag.tedivm.com as the primary use case, with CLI as secondary

## Why

### Username Normalization

GitHub usernames are case-insensitive (e.g., `tedivm` and `TedIVM` refer to the same user), but the current implementation treats them differently in cache keys and URLs. This causes:

- **Duplicate cache entries**: Same user data cached multiple times with different cases
- **Inconsistent URLs**: Users may share links with different capitalizations, creating confusion
- **Poor SEO**: Search engines may treat case variants as different pages

Normalizing to lowercase and redirecting uppercase URLs (with 301 permanent redirects) ensures consistent caching, URLs, and better user experience.

### Expanded Social Media Links

Currently, the user profile section only displays:

- Blog URL (from `blog` field)
- Twitter/X handle (from `twitter_username` field)

However, GitHub's API provides a `/users/{username}/social_accounts` endpoint that returns additional platforms:

- Mastodon
- LinkedIn
- Bluesky

Many developers use these platforms for professional networking and community engagement. Not displaying these links means Git Brag reports are missing valuable professional context that could be useful for portfolio building and performance reviews.

### Encouraging Empty State Message

The current message "No pull requests found for this period." is accurate but neutral. Since GitBrag is used for professional development and self-promotion, the empty state should:

- Be encouraging rather than discouraging
- Suggest action (e.g., "Start contributing to open source!")
- Maintain professional tone
- Acknowledge that everyone starts somewhere

This improves the emotional experience for new contributors or users exploring different time periods.

### README Website Focus

The current README emphasizes CLI usage and treats the web interface as secondary. However:

- The hosted service at gitbrag.tedivm.com is the primary way most users will interact with GitBrag
- Web interface provides better UX (OAuth, caching, sharing, no token management)
- README should guide users to the easiest path (web) while still documenting CLI for power users
- Better aligns with the project's goal of helping developers create professional contribution reports

The rewrite will:

- Lead with the hosted service and its URL
- Make CLI documentation secondary but still accessible
- Emphasize the web interface's advantages
- Keep technical details for developers who need them

## What Changes

### Code Changes

**Username Normalization:**

- Modify `generate_cache_key()` in `gitbrag/services/reports.py` to lowercase the username parameter
- Modify `get_or_fetch_user_profile()` in `gitbrag/services/reports.py` to lowercase the username parameter
- Add username normalization check in `user_report()` route in `gitbrag/www.py`
- If incoming `username` parameter contains uppercase, return `RedirectResponse` with 301 status to lowercase version
- Preserve query parameters (period, force) in redirect URL

**Expanded Social Media Links:**

- Add `get_user_social_accounts()` method to `GitHubAPIClient` in `gitbrag/services/github/client.py`
- Modify `get_or_fetch_user_profile()` in `gitbrag/services/reports.py` to fetch and merge social accounts into profile dict
- Cache social accounts with same TTL as user profile (1 hour refresh when authenticated)
- Update `gitbrag/templates/user_report.html` to display social media links with appropriate icons:
  - Mastodon: 🐘 or appropriate icon
  - LinkedIn: 💼 or appropriate icon
  - Bluesky: 🦋 or appropriate icon
- Ensure links open in new tabs with `target="_blank"`
- Handle missing/null social accounts gracefully

**Encouraging Empty State Message:**

- Update `gitbrag/templates/user_report.html` empty state section
- Replace "No pull requests found for this period." with encouraging message
- Example: "No pull requests found for this period. Every open source journey starts somewhere—your next contribution is waiting! 🚀"
- Maintain professional, positive tone

**README Rewrite:**

- Lead with GitBrag description and link to gitbrag.tedivm.com
- Add "Try it now" or "View your contributions" call-to-action
- Move CLI documentation to later section
- Emphasize web interface features and benefits
- Keep installation instructions but make them secondary
- Maintain all existing technical documentation in appropriate sections

### Testing

- Add test for username normalization redirect in `tests/test_www.py`
- Add test for lowercase cache key generation in `tests/test_reports.py`
- Add test for social accounts API call in `tests/test_github_client.py`
- Add test for social accounts display in template rendering
- Manual validation of empty state message
- Manual validation of README readability and flow

### Documentation

- Update `docs/dev/web.md` to document username normalization behavior
- Update `docs/dev/github-api.md` to document social accounts endpoint usage
- No changes needed for README (it's being rewritten as part of this change)

## Success Criteria

1. **Username Normalization:**
   - Uppercase usernames in URLs redirect to lowercase with 301 status
   - Query parameters preserved in redirect
   - All cache keys use lowercase usernames
   - No duplicate cache entries for same user with different cases

2. **Expanded Social Media:**
   - All available social media platforms display on user reports
   - Mastodon, LinkedIn, and Bluesky links render with appropriate icons
   - Links open in new tabs
   - Missing/null accounts don't break layout
   - Social accounts cached with profile data

3. **Empty State Message:**
   - Encouraging message displays when no PRs found
   - Message is positive and actionable
   - Professional tone maintained
   - Visual styling matches existing design

4. **README:**
   - gitbrag.tedivm.com featured prominently at top
   - Clear call-to-action for web interface
   - CLI documentation still present but secondary
   - All existing information preserved
   - Improved readability and flow

5. **Testing:**
   - All new tests pass
   - Existing tests continue to pass
   - Manual validation confirms UX improvements

## Timeline

Estimated effort: 2-3 hours

- Username normalization: 30 minutes
- Social media expansion: 1 hour (API integration + template updates)
- Empty state message: 15 minutes
- README rewrite: 30-45 minutes
- Testing and validation: 30 minutes

## Related Changes

- Related to `web-user-interface` spec (extends user profile display)
- Related to `github-pull-request-collection` spec (affects caching strategy)
- No dependencies on other active changes
- No breaking changes to existing functionality

## Risks and Mitigations

**Risk:** 301 redirects could affect existing bookmarks/shared links
**Mitigation:** 301 (permanent redirect) is standard practice for URL normalization and browsers/crawlers handle it correctly

**Risk:** Social accounts API call adds latency
**Mitigation:** Cache with same TTL as user profile; accounts are fetched in same async context

**Risk:** Empty state message tone may not suit all users
**Mitigation:** Keep message brief, professional, and universal; focus on encouragement without being overly casual

**Risk:** README rewrite may confuse existing users
**Mitigation:** All existing information preserved; only organization changes; CLI docs still prominent in structure
