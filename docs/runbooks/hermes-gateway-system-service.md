# Hermes gateway system service install

Problem:
- running `sudo hermes gateway ...` can fail with `sudo: hermes: command not found`

Root cause:
- Hermes is often installed in a user-local location such as `~/.local/bin/hermes`
- that path is available in the normal user shell, but not always in the `sudo` environment
- when `sudo` cannot see the Hermes executable, the command fails before Hermes even starts

Do not use:
```bash
sudo hermes gateway install --system
```

Use this instead:
```bash
sudo "$(command -v hermes)" gateway install --system --run-as-user "$USER"
```

What this does:
- `command -v hermes` resolves the full path to the Hermes executable before `sudo` runs
- `--system` installs the gateway as a Linux system-level service
- `--run-as-user "$USER"` tells the service to run as your normal account instead of root

Start the installed service:
```bash
sudo "$(command -v hermes)" gateway start --system
```

Check service status:
```bash
sudo "$(command -v hermes)" gateway status --system
```

Optional: if you want a user service instead of a system service:
```bash
hermes gateway install
```

Troubleshooting:
- if `sudo hermes ...` says `command not found`, the issue is the `sudo` PATH
- if `sudo "$(command -v hermes)" ...` instead says a password is required, the PATH problem is fixed and only normal sudo authentication remains
- if you want to see where Hermes is installed, run:
  ```bash
  command -v hermes
  ```

Notes:
- this runbook is safe to keep in the public repo because it uses generic commands and does not include secrets, tokens, or machine-specific private values
