# HERO AI Orchestrator deployment

This directory records only the HERO-specific differences from the canonical
[installation guide](../../docs/INSTALLATION.md). Keep the Open SWE runtime in
this repository; do not vendor it into HERO.

## 1. GitHub App

Follow the installation guide to create a GitHub App, with these HERO-specific
settings:

- App owner: `HideSmithAI`
- Installation access: only `HideSmithAI/hero-ai-orchestrator`
- OAuth provider ID: `hidesmithai-open-swe`
- Request user authorization during installation: enabled
- Production webhook URL: `https://<backend>/webhooks/github`
- Local webhook URL: `https://<ngrok-host>/webhooks/github`
- LangSmith OAuth callback:
  `https://smith.langchain.com/host-oauth-callback/hidesmithai-open-swe`
- Local dashboard callback:
  `http://localhost:2024/dashboard/api/auth/callback`
- Production dashboard callback:
  `https://<dashboard-api>/dashboard/api/auth/callback`

Use the canonical permission and event lists from the installation guide. For
this deployment, do not grant Workflows write permission initially. HERO's
`AGENTS.md` prevents workflow edits unless a task explicitly requests them;
grant that permission later only when such work is intentionally delegated.

The repository installation is the hard access limit. The environment example
also sets only the exact repository allowlist. It deliberately leaves
`ALLOWED_GITHUB_ORGS` empty because Open SWE treats the organization and
repository allowlists as alternatives, not cumulative restrictions.

Keep the dashboard on a private network or behind an access proxy. With
`ALLOWED_GITHUB_ORGS` empty, Open SWE does not apply an organization-membership
gate to dashboard login; `CONFIGURED_ADMINS` still limits admin endpoints.

The webhook endpoint is:

```text
https://<open-swe-backend>/webhooks/github
```

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

The current `Personal` Developer workspace does not have LangSmith Sandbox
access (the API returns `403` and the Sandboxes page requires an upgrade). For
the free, single-repository POC, use the built-in local backend:

```dotenv
SANDBOX_TYPE="local"
LOCAL_SANDBOX_ROOT_DIR="./.open-swe-workspaces"
DEFAULT_SANDBOX_SNAPSHOT_ID=""
```

Local mode runs agent commands directly on this machine. It has no process or
filesystem isolation, so keep human-in-the-loop enabled, retain the exact HERO
repository allowlist, and stop the backend/tunnel when testing is complete. Do
not use this mode for untrusted tasks or a persistent public deployment.

Once the LangSmith workspace has Sandbox access, switch back to
`SANDBOX_TYPE="langsmith"` and create the documented reference snapshot:

```bash
uv run python scripts/create_sandbox_snapshot.py \
  --name hero-open-swe \
  --image johanneslangchain/open-swe-sandbox:gh-cli-amd64
```

Put the printed UUID in `DEFAULT_SANDBOX_SNAPSHOT_ID`. Before production, build
the checked-in `Dockerfile` under a registry controlled by HideSmithAI and
create a replacement snapshot from that pinned image.

## 3. Start the backend and dashboard

For local verification, follow the installation guide to expose port 2024 with
ngrok, then run:

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

## 4. Deploy continuously

For asynchronous operation, do not leave the backend on a developer laptop.
Follow the installation guide's production section and connect
`HideSmithAI/open-swe-deployment` to LangGraph Platform. Configure the values
from `environment.example` in the deployment, then update these values to the
public HTTPS endpoints:

```text
LANGGRAPH_URL=https://<backend>
DASHBOARD_API_BASE_URL=https://<dashboard-api>
DASHBOARD_BASE_URL=https://<dashboard>
DASHBOARD_ALLOWED_ORIGINS=https://<dashboard>
```

Update the GitHub App webhook and production OAuth callback to the same public
backend URL. Deploy the optional `ui/` dashboard separately as described in
the installation guide. The backend health check must return success before
enabling the webhook:

```bash
curl --fail --silent https://<backend>/health
```

## 5. Verify the integration

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
