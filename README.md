# DeepCurrent MCP (Local + Hosted)

DeepCurrent brings **web3 intelligence + automation** to any MCP client (desktop, CLI, or agent gateways like OpenClaw).

This repo is the **open-source Local MCP server** (BYOD connectors + optional DeepCurrent Cloud tools). For the best experience, connect to **DeepCurrent Cloud** for managed data, credits, and premium workflows.

**Learn more / upgrade:** `https://deepcurrent.app` *(landing page)*
**Cloud dashboard:** `https://dashboard.deepcurrent.app` *(app)*

## What you get (Cloud vs local)

DeepCurrent is more than “lists”. The Cloud product is where the premium capabilities live:

- **Intelligence workflows**: curated discovery with rationale, then expand into actionable access (contacts + network paths)
- **Web scraping & crawling**: quote-first, metered runs with structured outputs
- **Lead generation pipelines**: enrich targets, dedupe, and turn criteria into outreach-ready lists
- **Telegram operations**: moderation workflows, monitoring, and automation surfaces
- **Outreach automation**: email and messaging workflows (plan-dependent / evolving)
- **Credits + entitlements**: consistent quote → confirm → execute UX across tools

Local MCP (this repo) gives you:

- **BYOD connectors** (local files + user-owned APIs/keys)
- A **thin bridge** to DeepCurrent Cloud tools using `X-API-Key` (optional)

## Transports: what works where


| Transport                    | This server                                                      | Typical clients                                                                                                                                                                                                                            |
| ---------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **STDIO** (default)          | `deepcurrent-local-mcp` with no `DEEPCURRENT_MCP_TRANSPORT`      | Cursor, Claude Desktop, Claude Code, OpenAI Codex, OpenClaw, most MCP hosts                                                                                                                                                                |
| **Streamable HTTP** (local)  | `DEEPCURRENT_MCP_TRANSPORT=http` (debugging on `127.0.0.1` only) | Same clients that can point MCP at a `http(s)://` URL (e.g. Cursor, Codex) — see *Optional: local HTTP* below                                                                                                                              |
| **Streamable HTTP** (hosted) | `https://mcp.deepcurrent.app/mcp`                                | No local install; use in clients that support remote MCP by URL + headers (Cursor, Codex, Anthropic [Messages API MCP connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector) for **remote** HTTP only — not stdio) |


**Anthropic API note:** The [MCP connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector) attaches to **public HTTP** MCP servers from the Messages API. It does **not** run local STDIO processes; use the hosted DeepCurrent URL there, not this Python binary.

## Quick start

### Hosted (no install)

Connect to the DeepCurrent Cloud MCP gateway:

- **MCP URL**: `https://mcp.deepcurrent.app/mcp` *(beta; Streamable HTTP)*
- **Auth header**: `X-API-Key: <your DeepCurrent API key>`

This is ideal when you do not want a local Python install. Community/BYOD plugins are intentionally **local only**; the hosted surface is the official cloud-backed tool set.

Note: while the hosted MCP is in beta, it may be backed by the staging Cloud environment as we finalize production rollout.

### Local (BYOD + full control)

Run the local server on your machine (best for BYOD files and strict data residency). **Default transport is STDIO**, which is what most MCP clients expect.

## Requirements

- Python 3.11+

## Install

### Option A: From source (pip)

```bash
git clone https://github.com/Ulmo-AI/DeepCurrent.git
cd DeepCurrent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install .
```

Run:

```bash
deepcurrent-local-mcp
```

Use `cd` into whichever directory your clone created that contains this repo’s `pyproject.toml` (folder name may differ if you use a fork or mirror).

**Verify the package is installed** (before MCP Inspector, Cursor, or any client that spawns the stdio binary):

```bash
.venv/bin/python -c "import deepcurrent_local_mcp; print('ok')"
```

If you see `ModuleNotFoundError: No module named 'deepcurrent_local_mcp'`, the project is not on that interpreter’s `sys.path`. From the repo root, run `pip install .` (or `poetry install`) using **this** venv’s `pip`.

**Editable install on macOS + Python 3.14+:** `pip install -e .` writes a `*.pth` file under `site-packages`. If that file has the **hidden** file flag, CPython’s `site` module **skips** it and the package still won’t import. Fix one of: use a normal install `pip install .` (recommended for local MCP), or run `chflags nohidden .venv/lib/python3.*/site-packages/deepcurrent_local_mcp.pth` (adjust the `python3.*` folder to match your venv), then re-run the one-liner above.

### Option B: Poetry (contributors)

```bash
poetry install
poetry run deepcurrent-local-mcp
```

### Option C: Smithery (optional)

If this package is listed on [Smithery](https://smithery.ai), install into a client with the Smithery CLI, for example:

```bash
npx -y @smithery/cli@latest install <smithery-server-id> --client claude
npx -y @smithery/cli@latest install <smithery-server-id> --client cursor
```

Replace `<smithery-server-id>` with the ID from the server’s Smithery page. List supported install targets: `npx -y @smithery/cli@latest list clients`.

## Configure (env + config file)

You can use community/BYOD tools with **no DeepCurrent account**.

To enable official DeepCurrent Cloud tools, set:

```bash
export DEEPCURRENT_API_KEY="dc_..."
export DEEPCURRENT_API_URL="https://api.deepcurrent.app"  # optional override
```

Optional config file (env vars override file values):

- `~/.config/deepcurrent/local-mcp.json`
- `~/.deepcurrent/local-mcp.json`

Example:

```json
{
  "api_url": "https://api.deepcurrent.app",
  "api_key": "dc_..."
}
```

## Add to an MCP client

**Agent-assisted setup:** In **Cursor**, **Claude Code**, or any IDE with a coding agent, you can point the agent at this README (open the file in the workspace, or paste a link to the same document in your public repo) and ask it to **register the DeepCurrent MCP server** in your client config. Have it use the examples below, resolve `**which deepcurrent-local-mcp` / `where deepcurrent-local-mcp`** to an **absolute path**, and put the API key in **config `env` / TOML `env` / `headers` expansion** — not in the chat transcript.

This server uses **STDIO** by default. Most clients need an **absolute path** to the executable because they do not load your shell `PATH`.

Find the path:

```bash
# macOS / Linux
which deepcurrent-local-mcp

# Windows (PowerShell)
where deepcurrent-local-mcp
```

Replace `/absolute/path/to/deepcurrent-local-mcp` in the examples below. After editing client config, **fully restart the client** (not only reload window) so the MCP process starts cleanly.

### Cursor

- **Project:** `.cursor/mcp.json` in the repo root
- **User (global):** `~/.cursor/mcp.json` (Windows: `%USERPROFILE%\.cursor\mcp.json`)

You can also use **Settings → Tools & MCP** to add a server; Cursor writes the same JSON shape.

**Local (stdio):**

```json
{
  "mcpServers": {
    "deepcurrent": {
      "command": "/absolute/path/to/deepcurrent-local-mcp",
      "args": [],
      "env": {
        "DEEPCURRENT_API_KEY": "dc_..."
      }
    }
  }
}
```

**Hosted (Streamable HTTP, no local install):**

```json
{
  "mcpServers": {
    "deepcurrent-cloud": {
      "url": "https://mcp.deepcurrent.app/mcp",
      "headers": {
        "X-API-Key": "dc_..."
      }
    }
  }
}
```

If your Cursor build only supports `Authorization`, map your key there per client docs, or keep using the local stdio server and pass the key in `env` as above.

### Claude Code (CLI / IDE extension)

Full reference: [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp). Options such as `--transport`, `--env`, and `--scope` must appear **before** the server name; the command to run the server comes **after** `--`.

**Local (stdio) via CLI (recommended):**

```bash
claude mcp add --transport stdio --env DEEPCURRENT_API_KEY=dc_... deepcurrent -- /absolute/path/to/deepcurrent-local-mcp
```

**Hosted (Streamable HTTP) via CLI:**

```bash
claude mcp add --transport http deepcurrent-cloud https://mcp.deepcurrent.app/mcp --header "X-API-Key: dc_..."
```

Use `claude mcp list`, `claude mcp get <name>`, and `claude mcp --help` for lifecycle commands. In-session, `/mcp` shows server status.

**Manual JSON (project `.mcp.json` or as generated by the CLI):** stdio servers use `command` / `args` / `env` (no extra `type` field required). User-scoped entries also live in `~/.claude.json` if you add with `--scope user` — see the doc for scope and precedence.

```json
{
  "mcpServers": {
    "deepcurrent": {
      "command": "/absolute/path/to/deepcurrent-local-mcp",
      "args": [],
      "env": {
        "DEEPCURRENT_API_KEY": "dc_..."
      }
    }
  }
}
```

**Hosted in `.mcp.json` (optional):**

```json
{
  "mcpServers": {
    "deepcurrent-cloud": {
      "type": "http",
      "url": "https://mcp.deepcurrent.app/mcp",
      "headers": {
        "X-API-Key": "dc_..."
      }
    }
  }
}
```

Claude Code supports `${VAR}` expansion in `command`, `url`, and `headers` (see the same doc) so you can avoid committing API keys.

### Claude Desktop

**Settings → Developer → Edit config.**

```json
{
  "mcpServers": {
    "deepcurrent": {
      "command": "/absolute/path/to/deepcurrent-local-mcp",
      "args": [],
      "env": {
        "DEEPCURRENT_API_KEY": "dc_..."
      }
    }
  }
}
```

Config locations:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### OpenAI Codex (CLI + IDE extension)

Codex stores MCP servers in **TOML**: default `~/.codex/config.toml`, or project-scoped `.codex/config.toml` in trusted projects. The [Codex MCP doc](https://developers.openai.com/codex/mcp) is authoritative.

**CLI (stdio):**

```bash
codex mcp add deepcurrent --env DEEPCURRENT_API_KEY=dc_... -- /absolute/path/to/deepcurrent-local-mcp
```

**Manual `config.toml` (stdio):**

```toml
[mcp_servers.deepcurrent]
command = "/absolute/path/to/deepcurrent-local-mcp"
args = []
# env block for the child process
[mcp_servers.deepcurrent.env]
DEEPCURRENT_API_KEY = "dc_..."
DEEPCURRENT_API_URL = "https://api.deepcurrent.app"
```

**Hosted (Streamable HTTP) example:**

```toml
[mcp_servers.deepcurrent-cloud]
url = "https://mcp.deepcurrent.app/mcp"
# Prefer env var for the key in real setups:
env_http_headers = { "X-API-Key" = "DEEPCURRENT_API_KEY" }
```

Set `DEEPCURRENT_API_KEY` in your environment (or use Codex’s supported secret mechanisms) so the header resolves.

### OpenClaw (agent gateway)

OpenClaw supports MCP via gateway config (often `clawdbot.json5`).

- macOS: `~/.clawdbot/clawdbot.json5`
- Linux: `~/.config/clawdbot/clawdbot.json5` (or `~/.clawdbot/clawdbot.json5`)
- Windows: `%APPDATA%\clawdbot\clawdbot.json5`

```json5
{
  mcp: {
    servers: {
      deepcurrent: {
        command: "/absolute/path/to/deepcurrent-local-mcp",
        args: [],
        env: {
          DEEPCURRENT_API_KEY: "dc_...",
          DEEPCURRENT_API_URL: "https://api.deepcurrent.app",
        },
      },
    },
  },
}
```

### Optional: local Streamable HTTP (debugging)

For local integration tests or a trusted LAN, you can run HTTP on loopback (do not expose to the public internet with a single shared `DEEPCURRENT_API_KEY`).

```bash
export DEEPCURRENT_MCP_TRANSPORT=http
export DEEPCURRENT_MCP_HTTP_HOST=127.0.0.1
export DEEPCURRENT_MCP_HTTP_PORT=8009
export DEEPCURRENT_MCP_HTTP_PATH=/mcp
deepcurrent-local-mcp
```

Point clients that support MCP over HTTP at `http://127.0.0.1:8009/mcp` (or your chosen path/port).

## What local does not include (yet)

**Orchestrator bundle** tools that run as multi-stage Python flows in the **hosted remote** MCP only (`community_health_bundle`, `lead_pipeline_bundle`) are not shipped in this binary — they depend on the remote server’s in-process stages. `get_website_crawl_cost` is available locally (same backend as remote); `run_website_crawl` may be disabled in some remote builds. See `PRD Chat Phase 15 - Local MCP Parity and Code Mode Exploration.md` (**§4.3**, **§12.6 Parity matrix**). Intelligence, **growth**, credits, result-handle utilities, BYOD, and crawl **cost** are available here when an API key is configured.

## Tool provenance (official vs community)

Tool outputs include a `source` block so it is clear what ran where:

- `badge`: `official` | `certified` | `community`
- `publisher`: who shipped the tool
- `execution_mode`: `deepcurrent-cloud` | `byok-api` | `local`

Design intent:

- Community and certified connectors run locally and keep your data on your machine.
- Official tools are a thin local wrapper that calls DeepCurrent Cloud for curated intelligence and paid unlocks.
- Hosted deployments (if used) should expose official tools only (no arbitrary community code execution on DeepCurrent infrastructure).
- Outputs are bounded by default (avoid dumping huge record sets into model context).

### Badge ladder (community → certified → official)

- `community`: local-only, unreviewed BYOD/BYOK connectors
- `certified`: local-only, reviewed connectors with stable schemas + bounded outputs (pipeline to official)
- `official`: cloud-backed tools operated by DeepCurrent (eligible for paid credits + entitlements)

## Tool surface (current)

Official (cloud-backed when an API key is configured):

- `connect_deepcurrent_cloud`
- `get_credit_status`
- `claim_growth_credits`
- `resolve_growth_outcome`
- `quote_growth_plan`
- `run_growth_plan`
- `get_growth_plan_status`
- `resolve_intelligence_intent`
- `preview_quote_intelligence_package`
- `quote_intelligence_package`
- `execute_intelligence_package`
- `fetch_intelligence_result`
- `expand_intelligence_package`
- `fetch_result_summary`
- `fetch_result_artifact`
- `get_website_crawl_cost`

Community (BYOD):

- `list_byod_connectors`
- `run_byod_connector`

## How agents should use it

- Start with `resolve` to validate the intent with a redacted preview.
- Use `preview_quote` / `quote` before any paid or proprietary action.
- Use `execute` to get curated results.
- Use `expand` only for the specific entities you want to action (contacts / network depth).
- For lead enrichment and growth workflows, use the growth tools (`resolve_growth_outcome` → `quote_growth_plan` → `run_growth_plan`, then `get_growth_plan_status` as needed).

For plan details and pricing, use the Cloud landing page: `https://deepcurrent.app`.

## Testing & QA

- **`bash scripts/qa_mcp.sh`** — `compileall` on `src` plus `pytest`.
- **`bash scripts/inspector_smoke.sh`** — one `tools/call` to `list_byod_connectors` via MCP Inspector **CLI** (uses an absolute path to the venv binary).
- **Full Inspector / staging checklist (Phase 15):** in the `DeepCurrent-APIv1.0` tree, `PRDs/Phase 15/QA Chat Phase 15 - Local and Remote MCP.md` (§3 `tools/list`, env + `connect_deepcurrent_cloud`, sign-off). Use the **absolute** path to `.venv/bin/deepcurrent-local-mcp` in the UI or CLI.

## Troubleshooting

- `**command` not found:** Use the full path from `which` / `where`, not a shell alias.
- **No cloud tools / auth errors:** Set `DEEPCURRENT_API_KEY` in the MCP entry `env` block (or your client’s secret mechanism), not in chat.
- **Client does not see changes:** Quit and relaunch the host app; MCP is usually started once at startup.
- **Too many tools:** Some clients have practical limits on total MCP tools across servers; split optional servers or disable unused ones.

## Telemetry (on by default, opt out)

```bash
export DEEPCURRENT_TELEMETRY=0
```

Telemetry is **metadata only** (event name, tool name, status, latency). It never includes tool inputs/outputs or API keys.

## Smithery (dev)

- `smithery.yaml` (runtime: python)
- `pyproject.toml` `[tool.smithery]` server entrypoint

```bash
poetry run dev
poetry run playground
```

## Security

- Never paste your API key into chat messages or tool arguments.
- Prefer MCP client `env` (or TOML `env` / `env_vars`) for secrets.

## Contributing

See `CONTRIBUTING.md` for adding connectors, badges, and review expectations.
