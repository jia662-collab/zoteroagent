# Codex Instructions

Use the smallest working path for this repository.

## Local and Worktree

- Use `.codex/environments/environment.toml` for Codex app worktree setup and quick actions.
- Do not commit secrets. Put local-only values in `.env` or `.env.local`.
- If a worktree needs ignored local files, list only those files in `.worktreeinclude`.

## Cloud

- Codex Cloud requires this repository to be hosted on GitHub and authorized in Codex settings.
- Configure the Cloud environment setup script to mirror the local setup logic:

```sh
if [ -f package.json ]; then
  npm install
elif [ -f requirements.txt ]; then
  python -m pip install -r requirements.txt
elif [ -f pyproject.toml ]; then
  python -m pip install -e .
else
  echo "No dependency manifest found; setup skipped."
fi
```

## Checks

- Before reporting code changes, run the smallest available check: `npm test`, `python -m pytest`, or a direct command that exercises the edited file.
