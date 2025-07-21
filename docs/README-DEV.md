# Sniffly Development Guide

This guide is for developers who want to contribute to Sniffly or understand its development workflow.

## 🧠 Mental Model: Understanding Sniffly's Architecture

Sniffly consists of three main components that work together:

### 1. **Local Analytics Tool** (`sniffly/`)
The core Python package that users install and run locally:
- **Purpose**: Analyzes Claude Desktop logs on the user's machine
- **Privacy**: All processing happens locally, no data leaves the machine
- **Key Features**: 
  - FastAPI server (`server.py`) serves the dashboard
  - Multi-layered caching for performance
  - Real-time log processing and statistics
- **User Flow**: `pip install sniffly` → `sniffly init` → Browser opens dashboard

### 2. **Static Sharing Site** (`sniffly-site/`)
A Cloudflare Pages website for viewing shared dashboards:
- **Purpose**: Allows users to share their analytics publicly
- **Components**:
  - Public gallery homepage (`index.html`)
  - Share viewer (`share.html` - built from template)
  - Admin dashboard for moderation (`admin.html`)
- **Build Process**: `build.py` bundles JS/CSS from main package
- **Deployment**: Hosted on sniffly.dev via Cloudflare Pages

### 3. **Cloud Storage & Functions**
Backend infrastructure for the sharing feature:
- **Cloudflare R2**: Stores shared dashboard data as JSON
- **Pages Functions**: Dynamic routes for `/share/[id]`
- **Development Mode**: Uses local `fake-r2/` directory
- **Production Mode**: Uses Cloudflare R2 API

### How They Connect

```
User's Machine                    Internet
┌─────────────┐                ┌─────────────┐
│   Sniffly   │                │ sniffly.dev │
│  Dashboard  │ ──[Share]───►  │   (Pages)   │
│  (port 8081)│                │             │
└─────────────┘                └──────┬──────┘
                                      │
                               ┌──────▼──────┐
                               │ Cloudflare  │
                               │     R2      │
                               └─────────────┘
```

**Key Insights**:
- The analytics tool and sharing site are **separate systems**
- Users can use Sniffly without ever sharing
- Shared dashboards are static snapshots, not live data
- The build process ensures share viewer works standalone

## 🏗️ Development Setup

### Prerequisites
- Python 3.10-3.12
- Git
- Node.js (optional - only for JavaScript linting)
- Virtual environment tool (conda, venv, pyenv, etc.)

### Initial Setup

#### Step 1: Clone the Repository
```bash
git clone https://github.com/chiphuyen/sniffly
cd sniffly
```

#### Step 2: Create a Virtual Environment

**Option A: Using Conda (Recommended)**
```bash
# Create conda environment with Python 3.11
conda create -n sniffly python=3.11
conda activate sniffly

# Verify activation
which python  # Should show path in your conda env
```

**Option B: Using venv**
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify activation
which python  # Should show path in your venv
```

**Option C: Using pyenv-virtualenv**
```bash
# Create virtual environment
pyenv virtualenv 3.11.0 sniffly
pyenv activate sniffly

# Verify activation
which python  # Should show path in your pyenv env
```

#### Step 3: Install Dependencies

```bash
# IMPORTANT: Always use pip within your virtual environment to avoid conflicts
# Verify you're in the virtual environment first:
which python  # Should show path in your virtual env, not system Python

# Install in development mode (editable install)
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional)
pre-commit install
```

**⚠️ Common Issue: Dependency Conflicts**

If you encounter errors like `ModuleNotFoundError: No module named 'boto3'` even after installing requirements:

1. **Check you're using the right Python/pip**:
   ```bash
   which python
   which pip
   python --version
   ```

2. **Avoid mixing conda and pip packages**:
   - If using conda, create a fresh environment
   - If you have conda packages like `aiobotocore` that conflict, use a venv instead
   - Don't use system-wide Python (e.g., `/usr/bin/python`)

3. **If you see dependency conflicts**:
   ```bash
   # Create a fresh virtual environment
   deactivate  # Exit current environment
   rm -rf venv  # Remove old environment
   python -m venv venv  # Create new one
   source venv/bin/activate
   pip install -e .
   ```

#### Why Use a Virtual Environment for Development?

When users install Sniffly with `uvx sniffly init`, UV automatically handles the virtual environment for them. However, as a developer:

1. **Isolation**: Your dev environment won't conflict with other Python projects
2. **Reproducibility**: Ensures all developers have the same dependencies
3. **Testing**: You can test different Python versions and dependency combinations
4. **Editable installs**: The `-e` flag lets you modify code and see changes immediately
5. **Development tools**: Keep linters, formatters, and test tools separate from production


### Note on Node.js
Node.js is **NOT required** to run, build, or use Sniffly. The project is 100% Python-based.

In the development repository, we had optional `package.json` files for:
- ESLint to check JavaScript code quality
- Convenience wrappers that just called Python scripts

However, these files are **not included** in the open-source release because:
- All functionality works without Node.js
- All build scripts, including `build.py` for the static site, are Python-based
- It reduces setup complexity for users
- JavaScript linting is optional for contributors

If you want to lint JavaScript during development:
```bash
# Install ESLint locally
npm init -y
npm install --save-dev eslint
npx eslint sniffly/static/js/
```

## 📦 Building and Publishing

### Local Build

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build package
python -m build

# Check package
twine check dist/*

# Test installation
pip install dist/sniffly-*.whl
```

### Building the Static Site

The `sniffly-site` directory contains the public website (sniffly.dev) with the homepage, gallery, and share viewer. Before deploying to production:

```bash
cd sniffly-site
python build.py
```

**When to run build.py:**

1. **Before deploying to Cloudflare Pages** - Required for production deployment
2. **After modifying these files:**
   - `sniffly/static/css/dashboard.css`
   - `sniffly/static/js/` files (constants.js, utils.js, stats.js, etc.)
   - `sniffly-site/static/js/share-viewer.js`
   - `sniffly-site/share-template.html`
3. **In CI/CD pipelines** - Add to your deployment workflow

**What build.py does:**
- Bundles dashboard CSS from the main sniffly package
- Combines JavaScript files into a self-contained share.html
- Creates share viewer that works without the main sniffly server
- Enables shared dashboards on sniffly.dev

**Note:** You don't need to run this for local development or the main sniffly dashboard (port 8081).

### Publishing to PyPI

#### Initial Setup (First Time Only)

1. **Create PyPI Account**:
   - Register at [pypi.org](https://pypi.org/account/register/)
   - Verify your email
   - Enable 2FA (required for new accounts)

2. **Create API Token**:
   - Go to [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
   - Create a token with scope "Entire account" (or project-specific after first upload)
   - Save the token securely (starts with `pypi-`)

3. **Configure GitHub Secrets** (for automated publishing):
   - Go to your repo's Settings → Secrets → Actions
   - Add `PYPI_API_TOKEN` with your token value

4. **Install Publishing Tools**:
   ```bash
   pip install build twine
   ```

#### Publishing a New Version

1. **Update Version Number**:
   ```bash
   # Edit version in sniffly/__version__.py
   # Follow semantic versioning: MAJOR.MINOR.PATCH
   # Example: 0.1.0 → 0.1.1 (patch), 0.2.0 (minor), 1.0.0 (major)
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [0.1.1] - 2025-07-08
   ### Added
   - New feature X
   ### Fixed
   - Bug Y
   ### Changed
   - Behavior Z
   ```

3. **Build the Package**:
   ```bash
   # Clean old builds
   rm -rf dist/ build/ *.egg-info
   
   # Build source distribution and wheel
   python -m build
   
   # Verify the build
   twine check dist/*
   ```

4. **Test Locally**:
   ```bash
   # Create a test virtual environment
   python -m venv test-env
   source test-env/bin/activate  # On Windows: test-env\Scripts\activate
   
   # Install from local wheel
   pip install dist/sniffly-*.whl
   
   # Test the installation
   sniffly version
   sniffly help
   uvx --from dist/sniffly-*.whl sniffly init
   
   # Clean up
   deactivate
   rm -rf test-env
   ```

5. **Create Git Tag and Release**:
   ```bash
   # Commit all changes
   git add -A
   git commit -m "Release version 0.1.1"
   
   # Create annotated tag
   git tag -a v0.1.1 -m "Release version 0.1.1"
   
   # Push commits and tag
   git push origin main
   git push origin v0.1.1
   ```

6. **Automated Publishing** (Recommended):
   - GitHub Actions will automatically publish to PyPI when you push a tag
   - Monitor the Actions tab for build status

7. **Manual Publishing** (If needed):
   ```bash
   # Set PyPI token
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-YOUR-TOKEN-HERE
   
   # Upload to PyPI
   twine upload dist/*
   
   # Or use .pypirc file (more secure)
   # Create ~/.pypirc with:
   # [pypi]
   #   username = __token__
   #   password = pypi-YOUR-TOKEN-HERE
   ```

#### Testing with TestPyPI (Optional)

For testing the publishing process without affecting the real PyPI:

1. **Create TestPyPI Account**: [test.pypi.org](https://test.pypi.org)

2. **Get TestPyPI Token**: Create at test.pypi.org/manage/account/token/

3. **Upload to TestPyPI**:
   ```bash
   twine upload -r testpypi dist/*
   ```

4. **Install from TestPyPI**:
   ```bash
   pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ sniffly
   ```

### Publishing to UV/UVX

UV automatically picks up packages from PyPI, so no separate publishing is needed!

Once published to PyPI:
- Users can immediately use: `uvx sniffly init`
- UV caches packages for fast execution
- Updates are automatic when users run `uv tool upgrade sniffly`

#### Verifying UV/UVX Availability

After publishing to PyPI, test UV availability:

```bash
# Clear UV cache (optional)
uv cache clean

# Test one-time execution
uvx sniffly version

# Test persistent installation
uv tool install sniffly
uv tool list  # Should show sniffly
sniffly version

# Test upgrade (for future versions)
uv tool upgrade sniffly
```

### Version Management Best Practices

1. **Semantic Versioning**:
   - MAJOR (1.x.x): Breaking changes
   - MINOR (x.1.x): New features, backward compatible
   - PATCH (x.x.1): Bug fixes, backward compatible

2. **Pre-release Versions**:
   ```python
   # For alpha/beta releases in __version__.py
   __version__ = "0.2.0a1"  # Alpha 1
   __version__ = "0.2.0b1"  # Beta 1
   __version__ = "0.2.0rc1" # Release Candidate 1
   ```

3. **Version Checklist**:
   - [ ] Update `sniffly/__version__.py`
   - [ ] Update CHANGELOG.md
   - [ ] Update README.md if needed
   - [ ] Run full test suite
   - [ ] Build and check package
   - [ ] Create git tag
   - [ ] Push to GitHub
   - [ ] Verify GitHub Actions success
   - [ ] Test installation from PyPI

### Troubleshooting Publishing

**"Invalid or non-existent authentication" error**:
- Ensure token starts with `pypi-`
- Check token hasn't expired
- Verify you're using `__token__` as username

**"Package already exists" error**:
- Version already published (can't overwrite)
- Increment version number and try again

**GitHub Actions failing**:
- Check PYPI_API_TOKEN secret is set correctly
- Verify tag format matches workflow trigger
- Check Python version compatibility

**UV not finding package**:
- Wait 1-2 minutes for PyPI CDN propagation
- Try `uv cache clean` then retry
- Check package name spelling

## 🏗️ Architecture

### Project Structure

```
sniffly/
├── sniffly/
│   ├── __init__.py
│   ├── __version__.py
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── server.py           # FastAPI application
│   ├── api/                # API endpoints
│   ├── core/               # Core processing logic
│   ├── services/           # Business logic
│   ├── utils/              # Utilities
│   ├── static/             # Frontend assets
│   └── templates/          # HTML templates
├── tests/
├── docs/
├── .github/workflows/      # CI/CD pipelines
└── pyproject.toml          # Package configuration
```

### Key Components

1. **CLI Module** (`cli.py`):
   - Uses Click for command parsing
   - Manages configuration
   - Handles server lifecycle

2. **Config Module** (`config.py`):
   - Layered configuration system
   - Priority: CLI args > env vars > config file > defaults
   - Persists to `~/.sniffly/config.json`

3. **Server Module** (`server.py`):
   - FastAPI application
   - Serves dashboard and API
   - Manages caching layers

4. **Core Processing** (`core/`):
   - `processor.py`: JSONL log parsing
   - `stats.py`: Statistics extraction
   - `global_aggregator.py`: Cross-project aggregation

## 🧪 Testing

For detailed information about the test suite, see [docs/tests.md](docs/tests.md).

### Quick Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sniffly --cov-report=html

# Run specific test file
pytest tests/test_processor.py

# Run tests matching a pattern
pytest -k "streaming"

# Run tests with verbose output
pytest -v
```

## 🔍 Code Quality

### Linting and Formatting

```bash
# Run all linters
./lint.sh

# Or run individually:
ruff check sniffly tests        # Linting
ruff format sniffly tests       # Formatting
mypy sniffly                    # Type checking
```

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
      - id: ruff-format
```

## 🚀 GitHub Actions Workflows

### Overview

GitHub Actions is a CI/CD (Continuous Integration/Continuous Deployment) platform that automatically runs workflows when certain events occur in your repository. For Sniffly, we use GitHub Actions to ensure code quality, test across multiple platforms, and automate releases.

### How GitHub Actions Works

1. **Workflows** are defined in YAML files in `.github/workflows/`
2. **Triggers** (like `push`, `pull_request`) start workflows
3. **Jobs** run on virtual machines (runners) in parallel or sequence
4. **Steps** execute commands or reusable actions within jobs
5. **Matrix strategies** run the same job with different configurations

### Sniffly's CI/CD Pipeline

The project implements four workflows that work together to ensure quality:

```
[Code Push] → [Tests & Lint] → [Build Check] → [Release] → [PyPI]
     ↓              ↓                ↓              ↓           ↓
   Trigger      Quality Gate    Package Test    Tag/Manual   Published
```

### 1. Test Workflow (`.github/workflows/test.yml`)

**Purpose**: Ensures code works correctly across all supported Python versions.

**Triggers**: Every push and pull request

**What it tests**:
- ✅ **Python compatibility**: Tests on Python 3.10, 3.11, 3.12
- ✅ **Unit tests**: Runs 126 tests covering:
  - CLI commands and configuration
  - Log processing and deduplication
  - Statistics extraction
  - API endpoints
  - Memory caching
  - Performance benchmarks
- ✅ **Code coverage**: Enforces 80% minimum coverage
- ✅ **Async operations**: Tests FastAPI endpoints and async processing

**Key Features**:
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```
This matrix strategy runs tests 3 times in parallel, once for each Python version.

**Why it matters**: Ensures Sniffly works for users regardless of their Python version.

### 2. Lint Workflow (`.github/workflows/lint.yml`)

**Purpose**: Maintains consistent code style and catches potential bugs.

**Triggers**: Every push and pull request

**Tools used**:
- **ruff**: Fast Python linter and formatter checking for errors, style issues, and complexity
- **mypy**: Static type checker catching type-related bugs

**Note**: Ruff now handles both linting and formatting (replacing Black)

**Configuration** (from `pyproject.toml`):
- Line length: 120 characters
- Target Python: 3.11 syntax
- Enabled checks: errors, style, imports, naming, security, complexity

**Why it matters**: Consistent code is easier to read, review, and maintain.

### 3. Build Workflow (`.github/workflows/build.yml`)

**Purpose**: Verifies the package builds and installs correctly across platforms.

**Triggers**: Pushes and PRs to main branch

**Test matrix**:
- **Operating Systems**: Ubuntu, macOS, Windows
- **Python versions**: 3.10 and 3.12 (min and latest)
- **Total combinations**: 6 different environments

**What it validates**:
1. Package builds successfully (`python -m build`)
2. Installation works (`pip install dist/*.whl`)
3. CLI commands function post-install:
   - `sniffly version`
   - `sniffly help`
   - `sniffly config show`
4. Package artifacts are valid

**Why it matters**: Ensures users can install Sniffly regardless of their OS.

### 4. Publish Workflow (`.github/workflows/publish.yml`)

**Purpose**: Automates package release to PyPI.

**Triggers**: 
- When a GitHub release is published
- Manual trigger (workflow_dispatch)

**Release process**:
1. **Build stage**: Creates wheel and source distributions
2. **Validation**: Runs `twine check` to ensure package metadata is correct
3. **TestPyPI stage**: Publishes to test repository first
4. **PyPI stage**: Publishes to official PyPI after TestPyPI succeeds

**Security features**:
- Uses PyPA's official publish action
- Requires environment approvals
- Uses API tokens (not passwords)
- Implements staged deployment

**Why it matters**: Automated, secure releases reduce human error.

### Workflow Analysis & Recommendations

#### Are These Workflows Appropriate for Sniffly?

**Yes, the current workflows are well-suited for this project because:**

1. **Python Version Coverage**: Testing 3.10-3.12 is appropriate since:
   - 3.10 is the minimum version we support (for union type syntax)
   - 3.12 is the latest stable Python
   - Many users have different Python versions installed

2. **Cross-Platform Testing**: Essential because:
   - Claude Desktop runs on Windows, macOS, and Linux
   - File path handling differs across OSes
   - Users will install Sniffly on their personal machines

3. **Code Quality Tools**: The combination of ruff + mypy is modern and effective:
   - `ruff` is extremely fast and handles both linting and formatting
   - `mypy` helps catch type-related bugs early
   - Using ruff for formatting is 10-100x faster than Black

4. **80% Coverage Requirement**: Reasonable for this project:
   - High enough to catch most bugs
   - Not so high that it encourages meaningless tests
   - Current coverage is ~85%, so we're meeting this goal

5. **Staged PyPI Release**: Smart approach because:
   - TestPyPI deployment catches packaging issues
   - Manual approval prevents accidental releases
   - Automated process reduces human error

#### Current Coverage ✅:
- Multi-Python version testing (3.10-3.12)
- Cross-platform compatibility (Windows, macOS, Linux)
- Code quality enforcement (lint, format, types)
- Automated releases with safety checks
- 80% test coverage requirement

#### Performance Tests 🏃‍♂️:
Performance tests (`tests/test_performance.py`) are currently **disabled in GitHub Actions** because:
- GitHub Actions runners have variable performance characteristics
- The tests require consistent hardware to produce reliable results
- Performance thresholds (e.g., <500ms cache load, >10k messages/sec) are calibrated for development machines

To run performance tests locally:
```bash
pytest tests/test_performance.py -v
```

These tests verify:
- File cache load time (<500ms)
- Message processing throughput (>10,000 messages/second)
- Large dataset handling (>15 files/second)
- Memory efficiency (<100MB for 10k messages)

#### Potential Improvements 🔧:

1. **Add Integration Tests**: 
   ```yaml
   - name: Run integration test
     run: |
       sniffly init --no-browser &
       sleep 5
       curl -f http://localhost:8081/api/health
       pkill -f sniffly
   ```

2. **Security Scanning**:
   ```yaml
   - name: Security check
     run: |
       pip install pip-audit
       pip-audit --fix
   ```

3. **Performance Regression Testing**:
   ```yaml
   - name: Performance benchmark
     run: |
       pytest tests/test_performance.py --benchmark-only
       # Store results and compare with previous runs
   ```

4. **Cache Dependencies**: Speed up workflows:
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
   ```

5. **Add Pre-release Testing**: Test with real Claude logs:
   ```yaml
   - name: Test with sample logs
     run: |
       python -m sniffly.core.processor tests/mock-data/
   ```

### Setting Up GitHub Actions

#### For Contributors

No setup needed! GitHub Actions run automatically on your PRs.

#### For Fork Maintainers

1. **Enable Actions**: Settings → Actions → Allow all actions
2. **For publishing**, add secrets:
   - Go to Settings → Secrets → Actions
   - Add `PYPI_API_TOKEN` from https://pypi.org/manage/account/token/
   - Add `TESTPYPI_API_TOKEN` from https://test.pypi.org/manage/account/token/

#### Understanding Workflow Runs

1. **Check status**: Click the Actions tab in GitHub
2. **View logs**: Click on any workflow run
3. **Debug failures**: Expand failed steps to see error messages
4. **Re-run jobs**: Click "Re-run failed jobs" if needed

### Local Testing Before Push

Simulate CI locally to catch issues early:

```bash
# Run all quality checks
./lint.sh

# Run tests with coverage
pytest --cov=sniffly --cov-report=term-missing

# Build package
python -m build

# Test installation
pip install dist/*.whl
sniffly version
```

## 🔧 Environment Configuration

### Configuration System Overview

Sniffly uses a sophisticated configuration system with separate environment files for different components:

1. **`.env`** - Main analytics dashboard configuration
2. **`.env.sniffly.dev`** - Site, share, and admin configuration
3. **`Config` class** - Unified configuration management with priority layers

### Environment Files

#### `.env` - Analytics Dashboard Configuration

Used by the main Sniffly analytics server (port 8081):

```bash
# Server settings
PORT=8081                        # Dashboard server port
HOST=127.0.0.1                  # Dashboard server host

# Cache configuration
CACHE_MAX_PROJECTS=5            # Max projects in memory cache
CACHE_MAX_MB_PER_PROJECT=500    # Max MB per project in cache
CACHE_WARM_ON_STARTUP=3         # Projects to pre-load on startup

# Frontend settings
MESSAGES_INITIAL_LOAD=500       # Messages to load in UI
MAX_DATE_RANGE_DAYS=30          # Max days for date range selection
ENABLE_MEMORY_MONITOR=false     # Enable memory monitoring
```

#### `.env.sniffly.dev` - Site Configuration

Used by the share server (port 4001) and gallery/admin server (port 8000):

```bash
# Environment mode
ENV=DEV                         # DEV or PROD

# Development server settings
SITE_PORT=8000                  # Gallery/admin server port
SHARE_PORT=4001                 # Share viewer server port
SHARE_BASE_URL=http://localhost:4001
SHARE_STORAGE_PATH=/path/to/fake-r2

# Production settings (when ENV=PROD)
R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your-key
R2_SECRET_ACCESS_KEY=your-secret
R2_BUCKET_NAME=sniffly-shares

# Google Analytics
GA_MEASUREMENT_ID=G-XXXXXXXXXX

# Admin OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI_DEV=http://localhost:8000/admin/callback
GOOGLE_REDIRECT_URI_PROD=https://sniffly.dev/admin/callback
ADMIN_EMAILS=admin@example.com,other@example.com
```

### How Configuration Works

#### 1. Environment Loading

Different components load their respective environment files:

```python
# In sniffly/server.py (main dashboard)
from dotenv import load_dotenv
load_dotenv()  # Loads .env

# In sniffly/auth.py, share.py, gallery-site-server.py
env_file = Path(__file__).parent.parent / '.env.sniffly.dev'
if env_file.exists():
    load_dotenv(env_file)  # Loads .env.sniffly.dev
```

#### 2. Config Class Priority System

The `Config` class in `sniffly/config.py` implements a layered priority system:

```python
# Priority order (highest to lowest):
1. Environment variables (including from .env files)
2. Config file (~/.sniffly/config.json)
3. Default values (hardcoded in DEFAULTS dict)
```

Example flow:
```python
# .env contains: PORT=8081
# server.py calls: load_dotenv()
# Config usage:
config = Config()
port = config.get("port")  # Returns 8081

# How it works:
# 1. Checks os.getenv("PORT") → finds 8081 (from .env)
# 2. Would check ~/.sniffly/config.json if env var not found
# 3. Would use default (8081) if neither found
```

#### 3. Environment Variable Mappings

The `Config` class maps configuration keys to environment variables:

```python
ENV_MAPPINGS = {
    "port": "PORT",
    "host": "HOST", 
    "cache_max_projects": "CACHE_MAX_PROJECTS",
    # ... etc
}
```

When you call `config.get("cache_max_projects")`, it looks for the `CACHE_MAX_PROJECTS` environment variable.

### Configuration Best Practices

1. **Development Setup**:
   ```bash
   # Copy example files
   cp .env.example .env
   cp .env.sniffly.dev.example .env.sniffly.dev
   
   # Edit with your values
   vim .env.sniffly.dev  # Add OAuth credentials
   ```

2. **Production Deployment**:
   - Set environment variables directly in your hosting platform
   - Don't commit `.env` files to version control
   - Use different OAuth credentials for dev/prod

3. **Testing Different Configurations**:
   ```bash
   # Override via environment
   PORT=9000 sniffly init
   
   # Or use config command
   sniffly config set port 9000
   ```

### Why This Design?

1. **Separation of Concerns**:
   - Analytics tool config separate from site config
   - Different teams can manage different configs
   - Cleaner deployment strategies

2. **Flexibility**:
   - Environment variables for containers/cloud
   - Config files for persistent user preferences
   - Defaults for zero-config startup

3. **Security**:
   - Sensitive credentials in `.env` files (gitignored)
   - Different OAuth apps for dev/prod
   - Admin emails whitelist

### Common Configuration Scenarios

#### Local Development
```bash
# Both files use development settings
ENV=DEV  # in .env.sniffly.dev
# Uses localhost URLs and fake-r2 storage
```

#### Production Deployment
```bash
ENV=PROD  # in .env.sniffly.dev
# Uses Cloudflare R2 and production URLs
# Set via platform environment variables
```

#### Custom Ports
```bash
# Change analytics dashboard port
PORT=9000  # in .env

# Change share server port  
SHARE_PORT=5000  # in .env.sniffly.dev
SHARE_BASE_URL=http://localhost:5000
```

## 🐛 Debugging

### Common Issues

1. **Import errors after renaming**:
   ```bash
   # Clean Python cache
   find . -type d -name __pycache__ -exec rm -rf {} +
   find . -name "*.pyc" -delete
   ```

2. **Test failures**:
   ```bash
   # Run specific test with debugging
   pytest -xvs tests/test_cli.py::TestCLICommands::test_config_set
   ```

3. **Server not starting**:
   ```bash
   # Check port availability
   lsof -i :8081
   
   # Run with debug logging
   LOG_LEVEL=DEBUG sniffly init
   ```

### Performance Profiling

```bash
# Profile backend processing
python profile_backend.py

# Profile specific workflow
python profile_workflow.py
```

## 📝 Documentation

### Building Docs

```bash
# Install docs dependencies
pip install -r docs/requirements.txt

# Build HTML docs
cd docs
make html
```

### Documentation Structure

```
docs/
├── CLAUDE_LOGS_STRUCTURE.md    # Log format reference
├── SNIFFLY_DISTRIBUTION_PLAN.md # Release planning
├── specs.md                     # Technical specifications
├── memory-and-latency-optimization.md
├── installation.md              # User installation guide
└── cli-reference.md             # CLI command reference
```

## 🔄 Development Workflow

### Feature Development

1. **Create feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make changes** and write tests

3. **Run tests and linting**:
   ```bash
   pytest
   ./lint.sh
   ```

4. **Commit with conventional commits**:
   ```bash
   git commit -m "feat: add amazing feature"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/amazing-feature
   ```

### Release Process

1. **Update version**:
   ```python
   # sniffly/__version__.py
   __version__ = "1.1.0"
   ```

2. **Update CHANGELOG**

3. **Create release PR**

4. **After merge, tag release**:
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0"
   git push origin v1.1.0
   ```

5. **GitHub Actions** automatically publishes to PyPI

## 🤝 Contributing Guidelines

### Code Style

- Use type hints for function signatures
- Write docstrings for public functions
- Keep functions focused and small
- Add tests for new functionality

### Commit Messages

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### Pull Request Process

1. Update tests
2. Update documentation
3. Ensure CI passes
4. Request review
5. Address feedback
6. Squash and merge

## 🔗 Testing Share Functionality

### Port Usage Summary

| Port | Service | Purpose | Command |
|------|---------|---------|---------|
| 8081 | Main App | Sniffly analytics dashboard | `sniffly init` or `python -m sniffly.server` |
| 4001 | Share Server | View shared dashboards | `./start-local-share-server.sh` |
| 8000 | Static Site | Homepage, gallery, admin (future) | `cd sniffly-site && python site-dev-server.py` |

### How Sharing Works

#### In Production
- **Your dashboard**: Runs locally on your machine (`sniffly init`)
- **Homepage & Gallery**: `https://sniffly.dev`
- **Shared dashboards**: `https://sniffly.dev/share/{id}`
- **Storage**: Cloudflare R2 (cloud storage)

#### In Development
- **Your dashboard**: `http://localhost:8081`
- **Homepage & Gallery**: `http://localhost:8000` (for future development)
- **Shared dashboards**: `http://localhost:4001/share/{id}`
- **Storage**: Local `fake-r2` folder

### Quick Start

1. **Start your main dashboard**:
   ```bash
   sniffly init
   # Or: python -m sniffly.server
   ```

2. **Start the share viewing server** (in another terminal):
   ```bash
   ./start-local-share-server.sh
   ```

3. **Create a share**:
   - Open your dashboard at http://localhost:8081
   - Click the "Share" button
   - Choose your options
   - Copy the share link

4. **View the share**:
   - The link will be like: `http://localhost:4001/share/abc123`
   - Open it in your browser

### Why Two Different Servers?

This mimics production where:
- Your analytics run locally (privacy-first!)
- Shares are viewed on a public website
- They're completely separate systems

### Customizing Ports

If you need different ports, set environment variables:

```bash
# Change share server port
export SHARE_BASE_URL="http://localhost:9000"

# Change storage location
export SHARE_STORAGE_PATH="/path/to/my/shares"
```

### Troubleshooting

**"Failed to create share link"**
- Make sure you've refreshed your browser (Ctrl+Shift+R)
- Check browser console for errors

**"Share not found"**
- Make sure the share server is running
- Check that the share file exists in `fake-r2/`

**Port conflicts**
- The start script automatically kills processes on port 4001
- Or manually: `lsof -ti:4001 | xargs kill -9`

## 🚨 Security

### Reporting Issues

Report security vulnerabilities to: security@sniffly.dev

### Security Checks

```bash
# Check for known vulnerabilities
pip-audit

# Update dependencies
pip-compile --upgrade requirements.in
```

## 📊 Metrics and Monitoring

### Performance Benchmarks

Current benchmarks (as of latest tests):
- Processing speed: ~12,000 messages/second
- Memory usage: <500MB for typical project
- Startup time: <2 seconds
- API response time: <100ms (cached)

### Monitoring in Production

- Use structured logging with appropriate levels
- Monitor memory usage with `ENABLE_MEMORY_MONITOR=true`
- Track API response times
- Monitor cache hit rates

## 📝 TODO

### Known Issues

1. **Overview Refresh Button Intermittent Issue**:
   - The refresh button in overview.html sometimes doesn't detect changes in projects
   - When clicking Refresh, it shows "No changes" even though some projects have changed
   - Workaround: Navigate to individual project dashboards and refresh there first
   - Root cause: Likely related to how `refresh_all_projects()` checks for changes vs individual project refresh

### Future Improvements

1. **Migrate Share Logs to Cloudflare D1**:
   - Current: shares-log.jsonl stored in R2 (requires downloading/parsing entire file)
   - Proposed: Use D1 database for better query performance and scalability
   - Benefits:
     - SQL queries instead of parsing JSON
     - Better performance with large datasets
     - Atomic operations for concurrent writes
     - Native analytics queries (GROUP BY, COUNT, etc.)
   - D1 Free tier: 5GB storage, 5M reads/day, 100K writes/day (likely sufficient)
   - Implementation: See Phase 4 in docs/sniffly-distribution-plan.md

## 🆘 Getting Help

- **Discord**: [Join our community](https://discord.gg/sniffly)
- **Issues**: [GitHub Issues](https://github.com/chiphuyen/sniffly/issues)
- **Discussions**: [GitHub Discussions](https://github.com/chiphuyen/sniffly/discussions)