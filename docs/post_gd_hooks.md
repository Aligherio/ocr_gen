# Post-`gd` Automation Hooks

This repository includes an optional helper script that can be invoked after running your `gd` workflow (for example, an alias to `git diff`). The script gives you a predictable place to automate environment updates such as database migrations, seed scripts, or other housekeeping commands.

## Script Overview

- **Entry point:** `scripts/post_gd.py`
- **Default hooks directory:** `scripts/gd_hooks/`
- **Behavior:** executes every executable file in the hooks directory, in lexical order.

Hooks can be authored in any language as long as the file is marked executable (`chmod +x`) and includes an appropriate shebang.

## Usage

Run the helper directly, or wrap it inside your existing `gd` alias:

```bash
# Run hooks immediately after `gd`
./scripts/post_gd.py

# List hooks without running them
./scripts/post_gd.py --dry-run

# Continue processing remaining hooks even if one fails
./scripts/post_gd.py --continue-on-error
```

To integrate with a shell alias:

```bash
alias gd='git diff "$@"; ./scripts/post_gd.py'
```

The alias ensures that every time `gd` runs, the post-processing hooks are triggered.

## Adding Hooks

1. Create a new executable file inside `scripts/gd_hooks/` (for example, `001_refresh_data.sh`).
2. Implement the desired automation.
3. Ensure the file is executable: `chmod +x scripts/gd_hooks/001_refresh_data.sh`.
4. (Optional) Use a numeric prefix so hooks run in a deterministic order.

## Failure Handling

- The runner stops at the first failing hook by default.
- Use `--continue-on-error` when you want all hooks to run regardless of failures.
- Exit codes propagate to your shell, letting CI/CD or wrapper scripts react accordingly.

## Extending the Workflow

Set the `hooks` argument to point at an alternative directory if you need environment-specific hooks:

```bash
./scripts/post_gd.py path/to/custom/hooks
```

This makes it easy to maintain separate hook sets for local development, staging, or production environments.
