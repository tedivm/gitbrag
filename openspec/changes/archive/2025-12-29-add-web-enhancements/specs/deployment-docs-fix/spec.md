# Deployment Documentation Fix Spec Delta

## ADDED Requirements

### Requirement: Deployment documentation with correct environment variable formatting

The deployment documentation MUST demonstrate proper formatting of boolean environment variables in Docker Compose YAML files to prevent parsing errors and ensure consistent behavior across environments.

#### Scenario: Boolean environment variables are quoted in compose.yaml examples

**Given** the deployment documentation in `docs/dev/deployment.md`
**When** Docker Compose YAML examples define boolean environment variables
**Then** all boolean values are wrapped in quotes:

- `DEBUG: "false"` (not `DEBUG: false`)
- `CACHE_ENABLED: "true"` (not `CACHE_ENABLED: true`)
- `REQUIRE_HTTPS: "true"` (not `REQUIRE_HTTPS: true`)

**And** unquoted boolean literals are not used in environment variable sections
**And** the formatting is consistent across all compose.yaml examples

#### Scenario: Deployment docs explain why boolean quoting is necessary

**Given** the deployment documentation includes Docker Compose examples
**When** boolean environment variables are demonstrated
**Then** the documentation includes a note explaining:

- YAML interprets unquoted `true`/`false` as boolean types
- Docker Compose passes environment variables as strings to containers
- Python's Pydantic settings expect string values for boolean fields
- Quoting ensures consistent behavior and prevents type confusion
- Example: `DEBUG: "false"` is correct, `DEBUG: false` may cause issues

**And** the note appears near the first occurrence of boolean variables
**And** the explanation is concise and actionable for deployers

#### Scenario: Environment file examples use correct boolean format

**Given** the deployment documentation includes `.env` file examples
**When** boolean variables are defined in `.env` format
**Then** values are shown without quotes (since .env files are not YAML):

- `DEBUG=false` (correct for .env)
- `CACHE_ENABLED=true` (correct for .env)
- `REQUIRE_HTTPS=true` (correct for .env)

**And** the documentation clarifies the difference between compose.yaml and .env formats
**And** examples are consistent with shell environment variable conventions

#### Scenario: All compose.yaml examples in deployment docs use quoted booleans

**Given** the deployment documentation contains multiple compose.yaml examples:

- Production deployment example
- Alternative single-container example
- Resource limits example
- Security options example

**When** each example is reviewed
**Then** all boolean environment variables use quoted format (`"true"`, `"false"`)
**And** no unquoted boolean literals appear in environment sections
**And** other YAML boolean fields (e.g., `read_only: true`) remain unquoted (as they are YAML structure, not env vars)

#### Scenario: Deployment docs distinguish YAML structure booleans from env var booleans

**Given** the deployment documentation includes compose.yaml with both:

- Docker Compose structural booleans (e.g., `read_only: true`, `no-new-privileges: true`)
- Environment variable booleans (e.g., `DEBUG: "false"`)

**When** examples are provided
**Then** structural booleans remain unquoted (correct YAML syntax)
**And** environment variable booleans are quoted (correct env var syntax)
**And** the documentation clarifies this distinction if both appear together
**And** users can distinguish between YAML structure and environment variable configuration

## Related Specs

None directly. This is a documentation-only change to prevent deployment issues.
