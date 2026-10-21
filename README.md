# AEOps

Governed, plugin based agentic automation. A Main Engine routes a problem to
plugins (GitHub, AWS, Database). Every plugin follows the same flow:
diagnose, propose, approve, execute, verify, revert. Nothing runs without a
human approval.

## Run

    pip install -r requirements.txt
    python -m aeops.cli "there is an error in my code"

Set `ANTHROPIC_API_KEY` to use a real model. Without it a canned fix is used
for the demo repo. `AEOPS_REPO` points at the repo to fix (default `demo_repo`).

## Test

    python -m pytest tests -q

## Status

- Main Engine with router and plugin registry: done
- GitHub plugin with approval gate and revert: done
- AWS and Database plugins: manifests only
- Knowledge layer, Vault, parallel planning: planned
