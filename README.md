# git brag

**Create professional contribution reports for your GitHub open source work.**

Showcase your impact with comprehensive reports perfect for performance reviews, portfolio building, and demonstrating your open source contributions.

**[✨ Try it now at gitbrag.tedivm.com](https://gitbrag.tedivm.com)** — No installation required!

## Why GitBrag?

- **Easy to Use**: Login with GitHub OAuth — no tokens or configuration needed
- **Professional Reports**: Beautiful, shareable contribution summaries with detailed statistics
- **Fast & Cached**: Instant page loads with smart caching and background generation
- **Privacy-Friendly**: Only accesses publicly available GitHub data
- **Rich Insights**: Code statistics, language breakdown, PR sizes, and repository roles

## Features

### Web Interface (Recommended)

Visit **[gitbrag.tedivm.com](https://gitbrag.tedivm.com)** to:

- **Generate reports instantly** with GitHub OAuth authentication
- **Share your achievements** with clean, professional URLs
- **Track your progress** with cached reports and automatic refresh
- **No setup required** — works in any browser

The web interface provides:

- **Instant Page Loads**: Cached reports served in <2 seconds
- **Background Generation**: Reports generate asynchronously without blocking
- **Smart Auto-Refresh**: Pages automatically reload every 10 seconds during generation
- **Code Statistics**: Lines added, deleted, and files changed per PR
- **Language Analysis**: Programming language breakdown
- **PR Size Categories**: One Liner, Small, Medium, Large, Huge, or Massive
- **Repository Roles**: Owner, Member, or Contributor status

### Command-Line Interface

For automation and power users, GitBrag is also available as a CLI tool:

```bash
# Install
pip install gitbrag

# Or run directly with uvx (no installation)
uvx gitbrag list <username>
```

## Getting Started

### Web Interface (Easiest)

1. Visit **[gitbrag.tedivm.com](https://gitbrag.tedivm.com)**
2. Login with your GitHub account
3. View your contribution report instantly!

Share your report URL with others or use it in performance reviews and portfolios.

### Self-Hosting

Host your own instance with Docker:

```bash
docker compose up
```

Then visit `http://localhost` and login with GitHub.

See [Web Interface Documentation](docs/dev/web.md) for detailed setup instructions.

### CLI Configuration

For command-line usage, set your GitHub Personal Access Token:

```bash
export GITHUB_TOKEN="your_token_here"
```

Or create a `.env` file:

```bash
GITHUB_TOKEN=your_token_here
```

## CLI Usage

List pull requests for a GitHub user:

```bash
gitbrag list <username> [OPTIONS]
```

### Options

- `--since DATE` - Start date (ISO format, default: 365 days ago)
- `--until DATE` - End date (ISO format, default: today)
- `--include-private` - Include private repositories
- `--show-urls` - Display PR URLs in output
- `--show-star-increase` - Display repository star increases during the filtered period
- `--sort FIELD[:ORDER]` - Sort by field (can be used multiple times)
  - Valid fields: `repository`, `state`, `created`, `merged`, `title`, `stars` (requires `--show-star-increase`)
  - Valid orders: `asc`, `desc` (default: `desc`)

### Examples

Show all PRs from the last year:

```bash
gitbrag list tedivm
```

Show PRs from a specific date range:

```bash
gitbrag list tedivm --since 2024-12-14 --until 2025-12-14
```

Sort by repository, then by merge date:

```bash
gitbrag list tedivm --since 2024-12-14 --until 2025-12-14 --sort repository --sort merged:desc
```

Show repository star increases during the filtered period:

```bash
gitbrag list tedivm --since 2024-12-14 --until 2025-12-14 --show-star-increase
```

Example output:

```text
╭────────────────────────────── Summary ───────────────────────────────╮
│ Total Pull Requests: 16                                              │
│                                                                      │
│ Code Statistics:                                                     │
│   +12,847 additions                                                  │
│   -3,421 deletions                                                   │
│   247 files changed                                                  │
│                                                                      │
│ Top Languages:                                                       │
│   Python: 68.3%                                                      │
│   JavaScript: 15.2%                                                  │
│   TypeScript: 8.7%                                                   │
│   Go: 4.9%                                                           │
│   YAML: 2.9%                                                         │
│                                                                      │
│ Repository Roles:                                                    │
│   OWNER: 8 repositories                                              │
│   CONTRIBUTOR: 4 repositories                                        │
╰──────────────────────────────────────────────────────────────────────╯

                                           Pull Requests
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Repository                 ┃ PR # ┃ Title                     ┃ Size     ┃ State  ┃ Created    ┃ Merged     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ TerraformInDepth/terrafor… │ 1    │ Version Upgrades          │ Small    │ merged │ 2025-04-05 │ 2025-04-05 │
│ TerraformInDepth/tofupy    │ 1    │ Update version, test      │ Medium   │ merged │ 2025-04-05 │ 2025-04-05 │
│                            │      │ range of python versions  │          │        │            │            │
│ TerraformInDepth/tofupy    │ 5    │ Improve Documentation     │ Small    │ merged │ 2025-08-02 │ 2025-08-02 │
│ tedious/JShrink            │ 149  │ Update PHP versions in CI │ Small    │ merged │ 2025-11-20 │ 2025-11-20 │
│                            │      │ workflow                  │          │        │            │            │
│ tedious/Stash              │ 429  │ Update tested versions of │ One      │ merged │ 2024-12-18 │ 2024-12-18 │
│                            │      │ php                       │ Liner    │        │            │            │
│ tedious/Stash              │ 435  │ Update PHP versions in    │ Small    │ open   │ 2025-11-20 │ -          │
│                            │      │ GitHub Actions workflow   │          │        │            │            │
│ tedivm/paracelsus          │ 39   │ Lock down pydot to v3     │ Small    │ merged │ 2025-08-20 │ 2025-08-20 │
│ tedivm/paracelsus          │ 44   │ Run test suite against    │ Small    │ merged │ 2025-10-10 │ 2025-10-10 │
│                            │      │ 3.14                      │          │        │            │            │
│ tedivm/paracelsus          │ 47   │ Drop tests and docs from  │ Large    │ merged │ 2025-11-22 │ 2025-11-22 │
│                            │      │ wheel build               │          │        │            │            │
│ tedivm/paracelsus          │ 52   │ Switch delimiter for      │ Small    │ merged │ 2025-12-14 │ 2025-12-14 │
│                            │      │ column parameters in      │          │        │            │            │
│                            │      │ Mermaid                   │          │        │            │            │
│ tedivm/paracelsus          │ 53   │ Support PyDot v3 and v4   │ Medium   │ merged │ 2025-12-14 │ 2025-12-14 │
│ tedivm/quasiqueue          │ 15   │ Run Test Suite against    │ Small    │ merged │ 2025-10-10 │ 2025-10-10 │
│                            │      │ Python 3.14               │          │        │            │            │
│ tedivm/robs_awesome_pytho… │ 15   │ fix pytest workflow       │ One      │ merged │ 2025-04-11 │ 2025-04-11 │
│                            │      │ rendering                 │ Liner    │        │            │            │
│ tedivm/robs_awesome_pytho… │ 16   │ Add template test suite   │ Huge     │ merged │ 2025-04-11 │ 2025-04-11 │
│ tedivm/robs_awesome_pytho… │ 19   │ Caching, Testing, and     │ Large    │ merged │ 2025-11-27 │ 2025-11-27 │
│                            │      │ Documentation Updates     │          │        │            │            │
│ tedivm/skysnoop            │ 4    │ Create a high level       │ Medium   │ merged │ 2025-11-30 │ 2025-11-30 │
│                            │      │ unified client            │          │        │            │            │
└────────────────────────────┴──────┴───────────────────────────┴──────────┴────────┴────────────┴────────────┘

Total: 16 pull requests
```

## Developer Documentation

Comprehensive developer documentation is available in [`docs/dev/`](./docs/dev/) covering testing, configuration, deployment, and all project features.

### Quick Start for Developers

```bash
# Install development environment
make install

# Start services with Docker
docker compose up -d

# Run tests
make tests

# Auto-fix formatting
make chores
```

See the [developer documentation](./docs/dev/README.md) for complete guides and reference.
