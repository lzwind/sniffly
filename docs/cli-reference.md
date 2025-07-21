# Sniffly CLI Reference

Complete reference for all Sniffly command-line interface commands.

## Command Overview

```
sniffly init          Start the analytics dashboard
sniffly config        Manage configuration
sniffly version       Show version information
sniffly help          Show help and usage examples
```

## Commands

### `sniffly init`

Start the Sniffly analytics dashboard server.

```bash
sniffly init [OPTIONS]
```

**Options:**
- `--port INTEGER` - Port to run server on (default: 8081)
- `--host STRING` - Port to run server on (default: localhost)
- `--no-browser` - Don't open browser automatically
- `--clear-cache` - Clear cached data

**Examples:**
```bash
sniffly init                    # Start with defaults
sniffly init --port 9000        # Use custom port
sniffly init --no-browser       # Don't open browser
```

---

### `sniffly config`

Manage configuration settings. This is a command group with subcommands:

#### `config show`

Display current configuration values and their sources.

```bash
sniffly config show [OPTIONS]
```

**Options:**
- `--json` - Output in JSON format

**Example output:**
```
Current configuration:
  auto_browser: True (default)
  port: 8090 (from config file)
  cache_max_projects: 5 (from environment)
```

#### `config set`

Set a configuration value.

```bash
sniffly config set KEY VALUE
```

**Examples:**
```bash
sniffly config set port 8090
sniffly config set auto_browser false
sniffly config set cache_max_projects 10
```

#### `config unset`

Remove a custom configuration value (revert to default).

```bash
sniffly config unset KEY
```

**Example:**
```bash
sniffly config unset port
```

---

### `sniffly version`

Show the current version of Sniffly.

```bash
sniffly version
```

---

### `sniffly help`

Show detailed help and usage examples.

```bash
sniffly help
```

## Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `port` | int | 8081 | Server port |
| `host` | str | 127.0.0.1 | Server host |
| `auto_browser` | bool | true | Auto-open browser |
| `cache_max_projects` | int | 5 | Max projects in memory |
| `cache_max_mb_per_project` | int | 500 | Max MB per project |
| `messages_initial_load` | int | 500 | Initial messages to load |
| `max_date_range_days` | int | 30 | Max days for date range |
| `enable_memory_monitor` | bool | false | Show memory usage |
| `enable_background_processing` | bool | true | Process stats in background |
| `cache_warm_on_startup` | int | 3 | Projects to preload |

## Environment Variables

All configuration keys can be set via environment variables:

```bash
# Examples
export PORT=9000
export AUTO_BROWSER=false
export CACHE_MAX_PROJECTS=10

# Or inline
PORT=9000 sniffly init
```

**Mapping:**
- `port` → `PORT`
- `host` → `HOST`
- `auto_browser` → `AUTO_BROWSER`
- `cache_max_projects` → `CACHE_MAX_PROJECTS`
- `cache_max_mb_per_project` → `CACHE_MAX_MB_PER_PROJECT`
- etc. (uppercase with underscores)

## Configuration Priority

Settings are loaded in priority order:
1. Command-line arguments
2. Environment variables
3. Config file (`~/.sniffly/config.json`)
4. Built-in defaults

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Invalid command or arguments

## File Locations

- **Configuration**: `~/.sniffly/config.json`
- **Claude logs**: `~/.claude/projects/` (auto-detected)
- **Cache**: `~/.sniffly/cache/`