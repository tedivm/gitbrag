"""Language detection and analysis utilities for pull requests."""

import os
from collections import Counter
from logging import getLogger

from gitbrag.services.github.models import PullRequestInfo

logger = getLogger(__name__)

# Comprehensive file extension to programming language mapping
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    # Python
    ".py": "Python",
    ".pyx": "Python",
    ".pyi": "Python",
    ".pyw": "Python",
    ".pyz": "Python",
    ".pth": "Python",
    # JavaScript/TypeScript
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    # Java/JVM
    ".java": "Java",
    ".class": "Java",
    ".jar": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".sc": "Scala",
    ".groovy": "Groovy",
    ".gradle": "Groovy",
    ".clj": "Clojure",
    ".cljs": "Clojure",
    ".cljc": "Clojure",
    ".edn": "Clojure",
    # C/C++
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c++": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".hxx": "C++",
    ".h++": "C++",
    ".cppm": "C++",
    ".ixx": "C++",
    # C#/.NET
    ".cs": "C#",
    ".csx": "C#",
    ".cake": "C#",
    ".cshtml": "C#",
    ".razor": "Razor",
    ".xaml": "XAML",
    # F#
    ".fs": "F#",
    ".fsx": "F#",
    ".fsi": "F#",
    ".fsproj": "F#",
    # Go
    ".go": "Go",
    # Rust
    ".rs": "Rust",
    ".rlib": "Rust",
    # Ruby
    ".rb": "Ruby",
    ".rake": "Ruby",
    ".gemspec": "Ruby",
    ".rbw": "Ruby",
    ".erb": "Ruby",
    # PHP
    ".php": "PHP",
    ".php3": "PHP",
    ".php4": "PHP",
    ".php5": "PHP",
    ".php7": "PHP",
    ".php8": "PHP",
    ".phtml": "PHP",
    ".phar": "PHP",
    # Swift
    ".swift": "Swift",
    # Objective-C
    ".m": "Objective-C",
    ".mm": "Objective-C",
    # R
    ".r": "R",
    ".R": "R",
    ".rmd": "R",
    ".Rmd": "R",
    # Shell/Scripting
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".fish": "Fish",
    ".ksh": "Ksh",
    ".csh": "Csh",
    ".tcsh": "Tcsh",
    ".bashrc": "Bash",
    ".zshrc": "Zsh",
    ".profile": "Shell",
    # PowerShell
    ".ps1": "PowerShell",
    ".psm1": "PowerShell",
    ".psd1": "PowerShell",
    # Batch/CMD
    ".bat": "Batch",
    ".cmd": "Batch",
    # Perl
    ".pl": "Perl",
    ".pm": "Perl",
    ".pod": "Perl",
    ".t": "Perl",
    # Lua
    ".lua": "Lua",
    # Julia
    ".jl": "Julia",
    # Haskell
    ".hs": "Haskell",
    ".lhs": "Haskell",
    ".cabal": "Haskell",
    # OCaml
    ".ml": "OCaml",
    ".mli": "OCaml",
    ".mll": "OCaml",
    ".mly": "OCaml",
    # Elixir
    ".ex": "Elixir",
    ".exs": "Elixir",
    # Erlang
    ".erl": "Erlang",
    ".hrl": "Erlang",
    ".escript": "Erlang",
    # Elm
    ".elm": "Elm",
    # Dart/Flutter
    ".dart": "Dart",
    # Zig
    ".zig": "Zig",
    # Nim
    ".nim": "Nim",
    ".nims": "Nim",
    ".nimble": "Nim",
    # V
    ".v": "V",
    # Crystal
    ".cr": "Crystal",
    # D
    ".d": "D",
    # Pascal/Delphi
    ".pas": "Pascal",
    ".pp": "Pascal",
    ".dpr": "Delphi",
    # Fortran
    ".f": "Fortran",
    ".for": "Fortran",
    ".f90": "Fortran",
    ".f95": "Fortran",
    ".f03": "Fortran",
    ".f08": "Fortran",
    # COBOL
    ".cob": "COBOL",
    ".cbl": "COBOL",
    # Lisp variants
    ".lisp": "Lisp",
    ".lsp": "Lisp",
    ".cl": "Common Lisp",
    ".el": "Emacs Lisp",
    ".scm": "Scheme",
    ".ss": "Scheme",
    ".rkt": "Racket",
    # Prolog
    ".pro": "Prolog",
    # HTML/Web
    ".html": "HTML",
    ".htm": "HTML",
    ".xhtml": "HTML",
    ".shtml": "HTML",
    ".ejs": "EJS",
    ".hbs": "Handlebars",
    ".mustache": "Mustache",
    ".pug": "Pug",
    ".jade": "Jade",
    ".haml": "Haml",
    ".twig": "Twig",
    ".njk": "Nunjucks",
    ".liquid": "Liquid",
    # CSS/Styling
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".styl": "Stylus",
    ".stylus": "Stylus",
    ".postcss": "PostCSS",
    # Web Frameworks
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".astro": "Astro",
    ".marko": "Marko",
    # SQL variants
    ".sql": "SQL",
    ".psql": "PostgreSQL",
    ".plsql": "PL/SQL",
    ".tsql": "T-SQL",
    ".mysql": "MySQL",
    # GraphQL
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    # Protocol Buffers/gRPC
    ".proto": "Protocol Buffers",
    # Thrift
    ".thrift": "Thrift",
    # Avro
    ".avsc": "Avro",
    ".avdl": "Avro",
    # Markdown/Documentation
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".mdown": "Markdown",
    ".mkd": "Markdown",
    ".rst": "reStructuredText",
    ".rest": "reStructuredText",
    ".txt": "Text",
    ".text": "Text",
    ".tex": "LaTeX",
    ".latex": "LaTeX",
    ".adoc": "AsciiDoc",
    ".asciidoc": "AsciiDoc",
    ".org": "Org Mode",
    # Config/Data formats
    ".json": "JSON",
    ".jsonc": "JSON",
    ".json5": "JSON5",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".plist": "Plist",
    ".ini": "INI",
    ".cfg": "Config",
    ".conf": "Config",
    ".config": "Config",
    ".properties": "Properties",
    ".env": "Environment",
    ".editorconfig": "EditorConfig",
    # Infrastructure as Code
    ".tf": "Terraform",
    ".tfvars": "Terraform",
    ".tofu": "Terraform",
    ".tf.json": "Terraform",
    ".tofu.json": "Terraform",
    ".bicep": "Bicep",
    ".cdk": "CDK",
    ".pulumi": "Pulumi",
    # Docker/Containers
    ".dockerfile": "Dockerfile",
    ".containerfile": "Containerfile",
    # Kubernetes
    ".k8s.yaml": "Kubernetes",
    ".k8s.yml": "Kubernetes",
    # Ansible
    ".ansible.yaml": "Ansible",
    ".ansible.yml": "Ansible",
    # CloudFormation
    ".cfn.yaml": "CloudFormation",
    ".cfn.yml": "CloudFormation",
    ".template": "CloudFormation",
    # Build systems
    ".makefile": "Makefile",
    ".mk": "Makefile",
    ".mak": "Makefile",
    ".cmake": "CMake",
    ".bazel": "Bazel",
    ".bzl": "Bazel",
    ".build": "Build",
    ".ninja": "Ninja",
    # CI/CD
    ".gitlab-ci.yml": "GitLab CI",
    ".travis.yml": "Travis CI",
    ".circleci": "CircleCI",
    ".jenkinsfile": "Jenkins",
    # Package managers
    ".package.json": "NPM",
    ".lock": "Lock",
    ".gemfile": "Bundler",
    ".podspec": "CocoaPods",
    ".gradle.kts": "Gradle",
    # Assembly/Low-level
    ".asm": "Assembly",
    ".s": "Assembly",
    ".nasm": "NASM",
    ".wasm": "WebAssembly",
    ".wat": "WebAssembly Text",
    # Hardware Description
    ".vhd": "VHDL",
    ".vhdl": "VHDL",
    ".verilog": "Verilog",
    # Shaders
    ".glsl": "GLSL",
    ".vert": "GLSL",
    ".frag": "GLSL",
    ".hlsl": "HLSL",
    ".metal": "Metal",
    # Game Development
    ".gd": "GDScript",
    ".gdscript": "GDScript",
    ".unity": "Unity",
    ".unreal": "Unreal",
    # Jupyter/Notebooks
    ".ipynb": "Jupyter",
    # AWK/Sed
    ".awk": "AWK",
    ".sed": "Sed",
    # Regular expressions
    ".regex": "Regex",
    # Vim
    ".vim": "Vim Script",
    ".vimrc": "Vim Script",
    # Emacs
    ".emacs": "Emacs Lisp",
    # Git
    ".gitignore": "Git",
    ".gitattributes": "Git",
    ".gitmodules": "Git",
    # Other specialized
    ".dot": "DOT",
    ".bnf": "BNF",
    ".ebnf": "EBNF",
    ".abnf": "ABNF",
    ".pest": "Pest",
}


def detect_language_from_extension(filename: str) -> str | None:
    """Detect programming language from file extension.

    Args:
        filename: Name of the file (can be full path)

    Returns:
        Language name or None if unknown
    """
    basename = os.path.basename(filename).lower()

    # Check for special files without extensions or with special naming
    special_files = {
        "dockerfile": "Dockerfile",
        "containerfile": "Containerfile",
        "makefile": "Makefile",
        "rakefile": "Ruby",
        "gemfile": "Ruby",
        "podfile": "Ruby",
        "vagrantfile": "Ruby",
        "berksfile": "Ruby",
        "thorfile": "Ruby",
        "guardfile": "Ruby",
        "capfile": "Ruby",
        "brewfile": "Ruby",
        "fastfile": "Ruby",
        "appfile": "Ruby",
        "deliverfile": "Ruby",
        "matchfile": "Ruby",
        "scanfile": "Ruby",
        "snapfile": "Ruby",
        "gymfile": "Ruby",
        "procfile": "Procfile",
        "justfile": "Just",
        "cmakelists.txt": "CMake",
        "build.gradle": "Gradle",
        "settings.gradle": "Gradle",
        "build.gradle.kts": "Gradle",
        "settings.gradle.kts": "Gradle",
        ".bashrc": "Bash",
        ".zshrc": "Zsh",
        ".profile": "Shell",
        ".bash_profile": "Bash",
        ".bash_aliases": "Bash",
        ".gitignore": "Git",
        ".gitattributes": "Git",
        ".gitmodules": "Git",
        ".dockerignore": "Docker",
        ".editorconfig": "EditorConfig",
        ".pylintrc": "Python",
        ".flake8": "Python",
        ".eslintrc": "JavaScript",
        ".prettierrc": "JavaScript",
        ".babelrc": "JavaScript",
    }

    if basename in special_files:
        return special_files[basename]

    # Get the file extension
    _, ext = os.path.splitext(filename)

    if not ext:
        return None

    # Look up in our mapping (case-insensitive)
    ext_lower = ext.lower()
    return EXTENSION_TO_LANGUAGE.get(ext_lower)


async def calculate_language_percentages(
    prs: list[PullRequestInfo],
    top_n: int = 5,
) -> list[tuple[str, float]]:
    """Calculate language contribution percentages from pull requests.

    Analyzes file extensions from all PRs and calculates the percentage
    contribution of each language based on number of files changed.

    Args:
        prs: List of PullRequestInfo objects
        top_n: Number of top languages to return (default: 5)

    Returns:
        List of (language, percentage) tuples, sorted by percentage descending
    """
    # We'll need to fetch the file lists from cache
    # Since we already fetched and cached them in collect_user_prs,
    # we need to access that data. However, the design says to calculate
    # from file extensions, but we didn't store the file lists in PullRequestInfo.
    # Let me re-check the design...

    # Actually, looking at the design more carefully, it says we should
    # calculate language percentages from file extensions across all PRs.
    # We need to fetch the cached file lists.

    from gitbrag.services.cache import get_cache

    cache = get_cache("persistent")
    language_counter: Counter = Counter()

    for pr in prs:
        try:
            # Parse repository info
            repo_parts = pr.repository.split("/", 1)
            if len(repo_parts) != 2:
                continue

            owner, repo = repo_parts

            # Get cached file list
            cache_key = f"pr_files:{owner}:{repo}:{pr.number}"
            cached_data = await cache.get(cache_key)

            if not cached_data:
                continue

            file_names, _, _, _ = cached_data

            # Count languages from file extensions
            for filename in file_names:
                language = detect_language_from_extension(filename)
                if language:
                    language_counter[language] += 1

        except Exception as e:
            logger.warning(f"Failed to analyze languages for PR {pr.repository}#{pr.number}: {e}")
            continue

    # Calculate percentages
    total_files = sum(language_counter.values())

    if total_files == 0:
        return []

    # Get top N languages with percentages
    language_percentages = [
        (language, (count / total_files) * 100) for language, count in language_counter.most_common(top_n)
    ]

    return language_percentages
