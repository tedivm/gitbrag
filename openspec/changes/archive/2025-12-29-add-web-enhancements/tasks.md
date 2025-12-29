# Implementation Tasks

## Overview

This document outlines the ordered tasks for implementing web enhancements including social media unfurling, Plausible analytics, and deployment documentation fixes.

## Task List

### 1. Add Plausible analytics settings to configuration

**Description**: Add `ENABLE_PLAUSIBLE` boolean and `PLAUSIBLE_SCRIPT_HASH` string settings to `WebSettings` class.

**Validation**:

- `enable_plausible` boolean field exists in `gitbrag/conf/settings.py`
- Field defaults to `False`
- Field can be loaded from `ENABLE_PLAUSIBLE` environment variable
- Field includes description explaining its purpose
- `plausible_script_hash` field exists with type `str | None`
- Hash field defaults to `None`
- Hash field can be loaded from `PLAUSIBLE_SCRIPT_HASH` environment variable
- Hash field includes description with example and instructions to find it in Plausible site settings

**Dependencies**: None

**Parallelizable**: Yes (independent of other tasks)

---

### 2. Add basic meta tags and Open Graph metadata to base template

**Description**: Add standard HTML meta tags and Open Graph meta tags to `gitbrag/templates/base.html` `<head>` section for social media unfurling and SEO.

**Details**:

- Add basic meta tags: `description`, `author`, `keywords`
- Add `og:type`, `og:site_name`, `og:url`, `og:title`, `og:description` tags
- Make `description`, `og:title` and `og:description` overridable via Jinja2 blocks
- Add `og:image` pointing to static logo/icon file (default)

**Validation**:

- All meta tags render in HTML output
- Jinja2 blocks allow child templates to override description and title
- Basic description meta tag mirrors Open Graph description
- HTML validates correctly
- Test with social media debugging tools (Twitter Card Validator, LinkedIn Post Inspector)

**Dependencies**: None

**Parallelizable**: Yes (independent of other tasks)

---

### 3. Add Twitter Card metadata to base template

**Description**: Add Twitter Card meta tags to `gitbrag/templates/base.html` `<head>` section.

**Details**:

- Add `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image` tags
- Use `summary_large_image` card type
- Reference same title/description blocks as Open Graph
- Add `twitter:site` tag if project has official Twitter handle

**Validation**:

- Meta tags render in HTML output
- Twitter Card Validator shows proper preview
- Image displays correctly in card preview

**Dependencies**: Task 2 (Open Graph metadata)

**Parallelizable**: No (depends on Open Graph blocks)

---

### 4. Customize metadata for user report pages

**Description**: Override Open Graph/Twitter metadata in `user_report.html` to include user-specific information and GitHub profile picture.

**Details**:

- Override `og:title` to include username (e.g., "GitHub Contributions for @username")
- Override `og:description` to include report summary (PR count, date range)
- Override `og:image` to use user's GitHub profile picture URL from report data
- Override `twitter:image` to use user's GitHub profile picture URL
- Add fallback to default `/static/images/og-image.png` if profile picture unavailable
- Ensure URL includes query parameters for accurate sharing

**Validation**:

- User report pages display custom metadata
- Shared links show username and stats in preview
- User's GitHub profile picture appears in social media previews
- Fallback to default image works when profile picture unavailable
- Test with multiple usernames and date ranges

**Dependencies**: Tasks 2 and 3 (metadata infrastructure)

**Parallelizable**: No (depends on metadata infrastructure)

---

### 5. Inject Plausible analytics script in base template

**Description**: Add conditional Plausible script tag to `gitbrag/templates/base.html` when both `ENABLE_PLAUSIBLE` is true and `PLAUSIBLE_SCRIPT_HASH` is configured.

**Details**:

- Check if `settings.enable_plausible` is `True` AND `settings.plausible_script_hash` is set in template context
- If both conditions met, inject the Plausible script with the site-specific hash:

  ```html
  <!-- Privacy-friendly analytics by Plausible -->
  <script async src="https://plausible.io/js/{{settings.plausible_script_hash}}.js"></script>
  <script>
    window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};    plausible.init()
  </script>
  ```

- Place script in `<head>` with `async` attribute
- Ensure script only loads when both settings are properly configured

**Validation**:

- Script renders when `ENABLE_PLAUSIBLE="true"` and `PLAUSIBLE_SCRIPT_HASH` is set
- Script does not render when either setting is missing
- Script URL includes the configured hash value
- Page views are tracked in Plausible dashboard (manual test)
- Script loading failure doesn't break page functionality

**Dependencies**: Task 1 (Plausible setting)

**Parallelizable**: No (depends on setting)

---

### 6. Update deployment documentation with quoted booleans

**Description**: Update `docs/dev/deployment.md` to wrap all boolean environment variables in quotes.

**Details**:

- Find all instances of `DEBUG: false`, `CACHE_ENABLED: true`, `REQUIRE_HTTPS: true`
- Change to `DEBUG: "false"`, `CACHE_ENABLED: "true"`, `REQUIRE_HTTPS: "true"`
- Add note explaining why quotes are needed (YAML parsing vs environment variables)
- Update `.env` file examples similarly

**Validation**:

- All boolean values in compose.yaml examples are quoted
- Documentation note explains reasoning
- No other values are accidentally changed
- Examples remain functional

**Dependencies**: None

**Parallelizable**: Yes (independent of other tasks)

---

### 7. Add tests for Plausible settings

**Description**: Add test cases for Plausible analytics settings in `tests/test_settings.py`.

**Details**:

- Test `enable_plausible` loads from environment variable
- Test `enable_plausible` defaults to `False`
- Test `plausible_script_hash` loads from environment variable
- Test `plausible_script_hash` defaults to `None`
- Test valid configuration with both settings enabled
- Test empty string is treated appropriately

**Validation**:

- All new tests pass
- Test coverage includes both new settings
- Tests follow existing patterns in file

**Dependencies**: Task 1 (Plausible setting)

**Parallelizable**: No (depends on setting implementation)

---

### 8. Add tests for template metadata rendering

**Description**: Add test cases for basic meta tags, Open Graph, and Twitter Card metadata rendering in `tests/test_www.py`.

**Details**:

- Test base template includes basic meta tags (description, author, keywords)
- Test base template includes default Open Graph tags
- Test base template includes Twitter Card tags
- Test user report template overrides title/description
- Test user report template uses GitHub profile picture for og:image
- Test user report template falls back to default image when profile unavailable
- Test Plausible script renders when both `ENABLE_PLAUSIBLE` and `PLAUSIBLE_SCRIPT_HASH` are configured
- Test Plausible script does not render when `ENABLE_PLAUSIBLE` is false
- Test Plausible script does not render when `PLAUSIBLE_SCRIPT_HASH` is unset
- Test script includes correct hash in URL

**Validation**:

- All new tests pass
- Tests verify basic meta tags are present and consistent with Open Graph
- Tests verify metadata content and structure
- Tests verify profile picture image override and fallback logic
- Tests verify both Plausible settings are required
- Tests use FastAPI TestClient to render templates
- Test coverage includes all conditional branches

**Dependencies**: Tasks 2, 3, 4, 5 (all template changes)

**Parallelizable**: No (depends on template implementations)

---

### 9. Generate Open Graph image for social media previews

**Description**: Run the provided script to generate a branded Open Graph image for social media previews.

**Details**:

- Install Pillow dev dependency: `uv pip install --group dev`
- Run the generation script: `python scripts/generate_og_image.py`
- Script creates a 1200x630px image with GitHub dark background (#24292e)
- Image contains centered white "git brag" text in monospace font
- Image includes tagline "Open Source Contribution Reports" in gray
- Script automatically saves to `gitbrag/static/images/og-image.png`
- Script optimizes PNG for smaller file size
- Update metadata tags to reference `/static/images/og-image.png`

**Validation**:

- Image file exists at `gitbrag/static/images/og-image.png`
- Image is exactly 1200x630px (optimal for all platforms)
- Image displays correctly in social media previews
- Image file size is < 100KB (script optimizes PNG)
- Image meets platform requirements (Twitter, LinkedIn, Open Graph)
- Image loads successfully from static URL path
- Script can be re-run if design changes are needed

**Dependencies**: Tasks 2 and 3 (metadata tags reference image)

**Parallelizable**: Yes (can be done anytime, just update path in templates)

---

### 10. Manual validation with social media debugging tools

**Description**: Test metadata with platform-specific debugging tools to ensure proper unfurling.

**Details**:

- Test with [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- Test with [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
- Test with [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
- Test with Slack's unfurling (paste link in Slack)
- Test multiple page types (home, user report, error pages)

**Validation**:

- All platforms show rich previews
- Title, description, and image display correctly
- No validation errors or warnings
- Links are clickable and direct to correct pages

**Dependencies**: Tasks 2, 3, 4, 9 (all metadata and image)

**Parallelizable**: No (requires deployed/running application)

---

## Task Sequencing

### Parallel Track 1: Social Media Unfurling

1. Task 2: Add Open Graph metadata
2. Task 3: Add Twitter Card metadata
3. Task 4: Customize metadata for user reports
4. Task 9: Add static logo/icon
5. Task 10: Manual validation

### Parallel Track 2: Plausible Analytics

1. Task 1: Add Plausible setting
2. Task 5: Inject Plausible script
3. Task 7: Add tests for setting

### Parallel Track 3: Documentation

1. Task 6: Update deployment docs (can run anytime)

### Final Integration

1. Task 8: Add template rendering tests (after all template changes)
2. Task 10: Manual validation (final step)

## Notes

- Tasks 1, 2, 6 can start in parallel
- Task 8 should be last code task (tests all template changes)
- Task 10 requires deployed instance for full validation
- Total estimated time: 1-2 hours
- All tasks deliver incremental, verifiable progress
