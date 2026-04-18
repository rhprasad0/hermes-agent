# Hermes chat abort fix: Honcho prefetch shutdown

This runbook documents a real local failure mode seen while validating the YNAB budget-channel MCP integration.

## Symptom

A non-interactive CLI invocation such as:

```bash
hermes chat --quiet -q "Use the YNAB MCP tools ..."
```

prints a correct answer, then exits with:

```text
Aborted (core dumped)
```

Typical exit code:

```text
134
```

## Actual root cause

The problem was not the YNAB MCP server itself.

The real failure was in the installed Hermes Honcho integration:
- Honcho background prefetch threads could still be alive during interpreter shutdown
- the Honcho provider shutdown path flushed remaining work but did not call the session manager shutdown path
- as a result, the process could abort during final interpreter teardown after a successful CLI response

## Observable clue

A useful investigation trick was to run Hermes with a temporary `sitecustomize.py` that dumps live threads at interpreter exit.

Before the fix, a typical clue was a surviving thread such as:

```text
honcho-context-prefetch
```

## Files to inspect in the installed Hermes source

These are local installed-source paths, not repo-tracked files in this public repo:

- `~/.hermes/hermes-agent/plugins/memory/honcho/session.py`
- `~/.hermes/hermes-agent/plugins/memory/honcho/__init__.py`

## Fix that worked

### 1. Track and join Honcho prefetch threads

In `~/.hermes/hermes-agent/plugins/memory/honcho/session.py`:
- add a shutdown event
- track spawned prefetch threads
- route prefetch spawning through a helper
- join tracked prefetch threads during `shutdown()`

Conceptually:
- add `_prefetch_threads`
- add `_prefetch_threads_lock`
- add `_shutdown_event`
- replace direct daemon thread spawning in:
  - `prefetch_context()`
  - `prefetch_dialectic()`
- join those threads in `shutdown()`

### 2. Ensure provider shutdown reaches manager shutdown

In `~/.hermes/hermes-agent/plugins/memory/honcho/__init__.py`:
- after `flush_all()`, also call `self._manager.shutdown()`

Without this, the session manager's thread cleanup may never run.

## Regression tests that proved the fix

Installed Hermes source tests:

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -m pytest \
  tests/plugins/test_honcho_provider_shutdown.py \
  tests/plugins/test_honcho_prefetch_shutdown.py \
  tests/test_honcho_client_config.py \
  tests/agent/test_honcho_gateway_scoping.py -q
```

## Validation that the fix worked

### CLI repeat test

```bash
python3 - <<'PY'
import subprocess, json
cmd = ['/home/USER/.local/bin/hermes','chat','--quiet','-q','Use the YNAB MCP tools to tell me how many YNAB plans are available to the configured token. Reply with just the number.']
results=[]
for i in range(3):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    results.append({'run': i+1, 'returncode': proc.returncode})
print(json.dumps(results))
PY
```

Expected after the fix:
- return code `0`
- no `Aborted (core dumped)` line

### Thread-dump sanity check

With a temporary `sitecustomize.py` atexit hook, the clean case should no longer show a live `honcho-context-prefetch` thread at exit.

## When to reach for this runbook

Use this runbook when:
- a YNAB CLI smoke test succeeds but `hermes chat` still aborts afterward
- a tool-using non-interactive Hermes CLI command exits with code `134`
- the failure looks like an MCP crash, but tool calls themselves succeeded

## Bottom line

If Hermes answers correctly and then crashes on exit, blame the shutdown path before blaming the YNAB server.

In this case the durable fix was:
- clean up Honcho prefetch threads
- make provider shutdown call manager shutdown
