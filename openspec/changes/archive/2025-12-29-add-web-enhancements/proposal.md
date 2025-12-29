# Proposal: Add Web Enhancements

## Overview

This change adds three enhancements to improve the web interface's shareability, analytics capabilities, and deployment documentation:

1. **Social Media Unfurling**: Add standard HTML meta tags, Open Graph, and Twitter Card metadata to pages so links shared on social media, Slack, and messaging apps display rich previews with title, description, and image. User report pages will use the GitHub profile picture from the report data for personalized previews.
2. **Plausible Analytics Integration**: Support optional privacy-friendly analytics by injecting Plausible tracking script when `ENABLE_PLAUSIBLE` is set to true and `PLAUSIBLE_SCRIPT_HASH` is configured
3. **Deployment Documentation Fix**: Update boolean environment variable examples in deployment docs to use quoted values (e.g., `"true"`, `"false"`) to prevent YAML parsing errors

## Why

### Social Media Unfurling

Currently, when users share GitBrag report URLs on platforms like Twitter, LinkedIn, Slack, or messaging apps, the links display as plain text with no context. This reduces engagement and makes reports less professional. Adding standard HTML meta tags, Open Graph, and Twitter Card metadata will:

- Make shared links more attractive and informative
- Increase click-through rates
- Provide context about the report before users click
- Improve professional presentation for performance reviews and portfolios
- Show personalized GitHub profile pictures for user reports

### Plausible Analytics

Many projects benefit from understanding usage patterns while respecting user privacy. Plausible is a privacy-friendly, open-source analytics platform that doesn't use cookies or track personal data. Adding optional support allows deployments to:

- Understand which features are most used
- Track report generation patterns
- Monitor application health and errors
- Make data-driven decisions about future development
- Comply with GDPR and other privacy regulations without cookie banners

### Deployment Documentation Fix

Docker Compose YAML parsing interprets unquoted `true`/`false` as boolean values, but environment variables are always strings. This mismatch can cause errors or unexpected behavior. Quoting boolean values (e.g., `"true"`) ensures consistent behavior and prevents deployment issues.

## What Changes

- Add `enable_plausible` and `plausible_script_hash` settings to `WebSettings` in `gitbrag/conf/settings.py`
- Add metadata blocks to `gitbrag/templates/base.html` for Open Graph and Twitter Card tags
- Add conditional Plausible script injection to `gitbrag/templates/base.html`
- Override metadata blocks in `gitbrag/templates/user_report.html` with user-specific information and profile pictures
- Make settings globally available to templates via `templates.env.globals` in `gitbrag/www.py`
- Quote boolean environment variables in `docs/dev/deployment.md` and add explanatory comments
- Generate Open Graph preview image using `scripts/generate_og_image.py`
- Add test coverage for new settings and template metadata

## User Impact

### Positive Impact

- **End Users**: Shared report links will display rich previews on social media and messaging platforms
- **Project Maintainers**: Optional analytics provide insights into usage patterns
- **DevOps/Deployers**: Clearer deployment documentation prevents configuration errors

### Breaking Changes

None. All changes are additive:

- Open Graph/Twitter Card metadata is automatically included but doesn't affect functionality
- Plausible analytics only activates when `ENABLE_PLAUSIBLE` is set to `"true"` and `PLAUSIBLE_SCRIPT_HASH` is configured
- Deployment documentation changes are clarifications, not behavior changes

## Dependencies

### Internal

- Existing settings system (`gitbrag/conf/settings.py`)
- Base HTML template (`gitbrag/templates/base.html`)
- Jinja2 template engine

### External

None. Plausible integration uses their CDN-hosted script; no new Python dependencies required.

## Risks and Mitigation

### Risk: Plausible script loading failures

**Mitigation**: Script is loaded asynchronously and failure doesn't block page rendering

### Risk: Excessive metadata requests for images

**Mitigation**: Use static logo/icon files with appropriate cache headers; consider adding to CDN later. For initial implementation, generate a simple branded placeholder image (1200x630px with GitBrag branding on GitHub-style background) using the provided Python script (`scripts/generate_og_image.py`).

### Risk: Incorrect boolean formatting in deployment docs

**Mitigation**: Test all example configurations before merging; add note about why quotes are needed

## Alternatives Considered

### Open Graph Alternatives

- **Twitter-only metadata**: Too limited; Open Graph works across most platforms
- **Dynamic metadata per report**: Too complex for initial implementation; can add later

### Analytics Alternatives

- **Google Analytics**: Privacy concerns, cookies, more intrusive
- **Self-hosted Matomo**: Requires additional infrastructure
- **No analytics**: Misses opportunity for usage insights

### Documentation Alternatives

- **Leave booleans unquoted**: Causes errors; not acceptable
- **Use environment file only**: Misses compose.yaml examples

## Success Criteria

1. Links shared on Twitter/LinkedIn/Slack display rich previews with title, description, and image
2. When `ENABLE_PLAUSIBLE` is `"true"` and `PLAUSIBLE_SCRIPT_HASH` is set, Plausible script loads and tracks page views
3. When `ENABLE_PLAUSIBLE` is not enabled or `PLAUSIBLE_SCRIPT_HASH` is unset, no analytics scripts are loaded
4. All deployment documentation examples use quoted boolean values
5. No existing functionality is broken
6. Tests validate new settings and template rendering

## Timeline

Estimated effort: 1-2 hours

- Social media metadata: 30 minutes
- Plausible integration: 20 minutes
- Deployment docs: 10 minutes
- Testing and validation: 30 minutes

## Related Changes

None currently. Future enhancements could include:

- Dynamic Open Graph images per user report
- Additional analytics providers
- More comprehensive deployment guides


