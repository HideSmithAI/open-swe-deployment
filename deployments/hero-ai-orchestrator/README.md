# HERO AI Orchestrator deployment

This directory records the deployment-specific configuration for running this
Open SWE fork against the private `HideSmithAI/hero-ai-orchestrator` repository.
Keep the Open SWE runtime in this repository; do not vendor it into HERO.

## 1. GitHub App

Create a GitHub App and install it only on
`HideSmithAI/hero-ai-orchestrator`. Configure the webhook URL as:

```text
https://<open-swe-backend>/webhooks/github
```

Repository permissions:

- Contents: read and write
- Pull requests: read and write
- Issues: read and write
- Checks: read and write
- Actions: read-only
- Metadata: read-only

Organization permissions:

- Members: read-only, because `ALLOWED_GITHUB_ORGS` gates dashboard login

Do not grant Workflows write permission initially. HERO's `AGENTS.md` prevents
workflow edits unless a task explicitly requests them; grant the permission
later only when such work is intentionally delegated.

Subscribe to these events:

- Issue comment
- Pull request
- Pull request review
- Pull request review comment
- Check run
- Check suite
- Workflow run

Subscribe to `Issues` only if mentioning `@openswe` in a newly created Issue
should trigger immediately. The recommended workflow is an explicit
`@openswe` Issue comment after triage.

## 2. Local configuration

Copy the example and populate secrets locally:

```bash
cp deployments/hero-ai-orchestrator/environment.example .env
openssl rand -hex 32      # GITHUB_WEBHOOK_SECRET and DASHBOARD_JWT_SECRET
openssl rand -base64 32   # TOKEN_ENCRYPTION_KEY
```

Create a LangSmith sandbox snapshot from the repository Docker image and put
its UUID in `DEFAULT_SANDBOX_SNAPSHOT_ID`. The snapshot already includes
Python, uv, git, GitHub CLI, ripgrep, and build tools needed by HERO.

## 3. Start the backend and dashboard

```bash
make install
uv run langgraph dev --no-browser
```

In another terminal:

```bash
cd ui
pnpm install
printf '%s\n' 'VITE_DASHBOARD_API_BASE_URL="http://localhost:2024"' > .env
pnpm run dev
```

Add the `imcaptor` GitHub login under **Admin -> User mappings**. Enable
**Always Create PRs** for the profile so every code change is delivered as a
draft pull request.

## 4. Verify the integration

Start with a read-only comment on a HERO Issue:

```text
@openswe Inspect the repository instructions and report the validation command.
Do not modify files.
```

Expected result: an eyes reaction, a LangSmith run, and an Issue reply that
identifies `.venv/bin/pytest -q`.

Then use a small documentation task to verify branch creation, tests, push,
and draft PR creation. Keep `ready-for-agent` as a human triage signal; it does
not trigger work without an explicit `@openswe` request.

