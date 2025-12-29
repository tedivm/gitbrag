# plausible-analytics Specification

## Purpose
TBD - created by archiving change add-web-enhancements. Update Purpose after archive.
## Requirements
### Requirement: Optional Plausible analytics configuration

The system MUST support optional integration with Plausible Analytics through configuration settings, allowing deployments to enable privacy-friendly analytics without code changes by providing a boolean flag and site-specific script hash.

#### Scenario: Add ENABLE_PLAUSIBLE and PLAUSIBLE_SCRIPT_HASH settings to WebSettings

**Given** the `WebSettings` class in `gitbrag/conf/settings.py`
**When** settings are defined
**Then** an `enable_plausible` field exists with type `bool`
**And** the field defaults to `False` when not configured
**And** the field can be set via `ENABLE_PLAUSIBLE` environment variable
**And** the field includes a description: "Enable Plausible Analytics privacy-friendly tracking. Requires PLAUSIBLE_SCRIPT_HASH to be set."
**And** a `plausible_script_hash` field exists with type `str | None`
**And** the hash field defaults to `None` when not configured
**And** the hash field can be set via `PLAUSIBLE_SCRIPT_HASH` environment variable
**And** the hash field includes a description: "Site-specific Plausible script hash (e.g., 'pa-HQtsjLCgyK7ys8q_iRTLl'). Find this in your Plausible site settings under 'Site Installation'."

#### Scenario: Load Plausible settings from environment variables

**Given** the environment variable `ENABLE_PLAUSIBLE` is set to `"true"`
**And** the environment variable `PLAUSIBLE_SCRIPT_HASH` is set to `"pa-HQtsjLCgyK7ys8q_iRTLl"`
**When** the application starts and loads settings
**Then** `settings.enable_plausible` equals `True`
**And** `settings.plausible_script_hash` equals `"pa-HQtsjLCgyK7ys8q_iRTLl"`
**And** both settings are available to templates and application code

#### Scenario: Default to no analytics when settings are unset

**Given** the environment variable `ENABLE_PLAUSIBLE` is not set (or set to `"false"`)
**When** the application starts and loads settings
**Then** `settings.enable_plausible` equals `False`
**And** `settings.plausible_script_hash` may be `None` or any value
**And** no analytics tracking is enabled regardless of hash value

#### Scenario: Require both settings for analytics to be enabled

**Given** the environment variable `ENABLE_PLAUSIBLE` is set to `"true"`
**And** the environment variable `PLAUSIBLE_SCRIPT_HASH` is not set or empty
**When** the application starts and loads settings
**Then** `settings.enable_plausible` equals `True`
**And** `settings.plausible_script_hash` is `None` or empty
**And** analytics tracking should not be enabled (missing hash)
**And** templates should check both conditions before injecting script

### Requirement: Conditional Plausible script injection in templates

The system MUST conditionally inject the Plausible analytics tracking script with site-specific hash in HTML pages only when both `ENABLE_PLAUSIBLE` is true and `PLAUSIBLE_SCRIPT_HASH` is configured, ensuring privacy by default.

#### Scenario: Inject Plausible script when fully configured

**Given** the `ENABLE_PLAUSIBLE` environment variable is set to `"true"`
**And** the `PLAUSIBLE_SCRIPT_HASH` environment variable is set to `"pa-HQtsjLCgyK7ys8q_iRTLl"`
**And** a user requests any page
**When** the base template is rendered
**Then** the HTML `<head>` section includes:

```html
<!-- Privacy-friendly analytics by Plausible -->
<script async src="https://plausible.io/js/pa-HQtsjLCgyK7ys8q_iRTLl.js"></script>
<script>
  window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};  plausible.init()
</script>
```

**And** the script hash in the URL matches the configured `PLAUSIBLE_SCRIPT_HASH` value
**And** the script is placed before the closing `</head>` tag
**And** the `async` attribute ensures non-blocking page load
**And** the initialization script is included immediately after

#### Scenario: Do not inject Plausible script when not fully configured

**Given** either `ENABLE_PLAUSIBLE` is not `"true"` OR `PLAUSIBLE_SCRIPT_HASH` is not set
**And** a user requests any page
**When** the base template is rendered
**Then** no Plausible script tag is present in the HTML
**And** no `<script>` tags reference `plausible.io`
**And** no Plausible initialization code is present
**And** the page functions normally without analytics

#### Scenario: Plausible script failure does not break page functionality

**Given** `ENABLE_PLAUSIBLE` is `"true"` and `PLAUSIBLE_SCRIPT_HASH` is configured
**And** the Plausible script is injected
**And** the Plausible CDN (plausible.io) is unreachable or returns an error
**When** a user loads the page
**Then** the page renders and functions normally
**And** no JavaScript errors are displayed to the user
**And** the `async` attribute ensures the page is not blocked by script loading
**And** the script failure is logged in browser console (but does not affect UX)

#### Scenario: Plausible tracks page views when fully configured

**Given** `ENABLE_PLAUSIBLE` is set to `"true"`
**And** `PLAUSIBLE_SCRIPT_HASH` is set to a valid hash
**And** Plausible is configured with an account linked to that script hash
**And** a user visits `/user/github/octocat`
**When** the page loads successfully
**Then** a page view event is sent to Plausible's analytics API
**And** the event is recorded in the Plausible dashboard linked to the script hash
**And** the event includes the page URL path (`/user/github/octocat`)
**And** no personal data (user IP, cookies, etc.) is tracked by Plausible

### Requirement: Privacy-first analytics implementation

The system MUST implement Plausible analytics in a privacy-respecting manner that complies with GDPR and does not require cookie consent banners.

#### Scenario: No cookies are set by Plausible

**Given** the Plausible script is loaded and tracking is enabled
**When** a user visits any page
**Then** no cookies are set by the Plausible script
**And** browser developer tools show no cookies from plausible.io domain
**And** no cookie consent banner is required for Plausible tracking

#### Scenario: Plausible tracking is optional and disabled by default

**Given** a new GitBrag deployment with default configuration
**When** the application starts without `ENABLE_PLAUSIBLE` set to `"true"`
**Then** no analytics tracking occurs
**And** no external scripts are loaded from analytics providers
**And** user privacy is preserved by default

#### Scenario: Plausible script is loaded from official CDN with hash

**Given** the Plausible script is injected into a page
**When** the script tag is rendered
**Then** the `src` attribute matches `https://plausible.io/js/{PLAUSIBLE_SCRIPT_HASH}.js`
**And** the script is loaded from Plausible's official CDN (not self-hosted)
**And** the script URL uses HTTPS for secure delivery
**And** the hash is site-specific and obtained from Plausible site settings
**And** no modifications or proxying of the script occur

