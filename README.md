# DeepCurrent MCP (Local + Hosted)

DeepCurrent brings **web3 intelligence + automation** to any MCP client (desktop, CLI, or agent gateways like OpenClaw).

This repo is the **open-source Local MCP server** (BYOD connectors + optional DeepCurrent Cloud tools). For the best experience, connect to **DeepCurrent Cloud** for managed data, credits, and premium workflows.

**Learn more / upgrade:** `https://deepcurrent.app` *(landing page)*  
**Cloud dashboard:** `https://dashboard.deepcurrent.app` *(app)*

## What You Get (Cloud vs Local)

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

## 🚀 Quick Start

### Hosted (no install)

If you prefer a hosted MCP URL, connect to the DeepCurrent Cloud MCP Gateway:

- **MCP URL**: `https://mcp.deepcurrent.app/mcp` *(beta; Streamable HTTP)*
- **Auth**: DeepCurrent API key (`X-API-Key`)

This is ideal for “no local install” setups. Community/BYOD plugins are intentionally local-only.

Note: while the hosted MCP is in beta, it may be backed by the staging Cloud environment as we finalize production rollout.

### Local (BYOD + power users)

Run the local server on your machine (best for BYOD/local files and agent gateways like OpenClaw).

## ✅ Requirements

- Python 3.11+

## 🧩 Install Options

If you just want to *use* DeepCurrent MCP locally, Option A is simplest.

If you want to *develop/contribute* to this repo, Option B (Poetry) is recommended.

### Option A: From source (Git + pip)

```bash
git clone https://github.com/Ulmo-AI/DeepCurrent.git
cd DeepCurrent
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Run:

```bash
deepcurrent-local-mcp
```

### Option B: Poetry (contributors)

Poetry is a Python dependency + environment manager. In this repo it’s mainly for contributors:

- installs dependencies in a clean, reproducible environment
- includes dev tooling and helper scripts (e.g. Smithery dev/playground)

```bash
poetry install
poetry run deepcurrent-local-mcp
```

### Option C: Smithery (optional)

Once published to Smithery, you can install it directly into your MCP client:

```bash
npx -y @smithery/cli@latest install <smithery-server-id> --client claude
npx -y @smithery/cli@latest install <smithery-server-id> --client cursor
```

Replace `<smithery-server-id>` with the ID shown on the server's Smithery page.

Note: Smithery supports two distribution models:

- **Local (stdio):** runs on the user's machine (this project). No OAuth required.
- **URL (hosted):** you host a public HTTPS MCP endpoint. Smithery requires Streamable HTTP transport, and OAuth if your server requires auth at connect-time.

Tip: list supported clients:

```bash
npx -y @smithery/cli@latest list clients
```

## 🔧 Configure

You can use community/BYOD tools with **no DeepCurrent account**.

To enable Official DeepCurrent Cloud tools, set environment variables (recommended for MCP clients):

```bash
export DEEPCURRENT_API_KEY="dc_..."
export DEEPCURRENT_API_URL="https://api.deepcurrent.app"  # optional override
```

Optional config file (env vars override):

- `~/.config/deepcurrent/local-mcp.json`
- `~/.deepcurrent/local-mcp.json`

Example:

```json
{
  "api_url": "https://api.deepcurrent.app",
  "api_key": "dc_..."
}
```

## 🔌 Add to an MCP Client (Manual)

This server runs over STDIO by default (what most MCP clients expect).

Note: GUI clients often do not inherit your shell `PATH`, so you may need to use absolute paths for `command`.

Find the executable path:

```bash
# macOS/Linux
which deepcurrent-local-mcp

# Windows (PowerShell)
where deepcurrent-local-mcp
```

### Optional: Streamable HTTP transport (local debugging)

If you want to run the server over Streamable HTTP (for local debugging or a trusted network), set:

```bash
export DEEPCURRENT_MCP_TRANSPORT=http
export DEEPCURRENT_MCP_HTTP_HOST=127.0.0.1
export DEEPCURRENT_MCP_HTTP_PORT=8009
export DEEPCURRENT_MCP_HTTP_PATH=/mcp
deepcurrent-local-mcp
```

Warning: do not expose this daemon publicly with a single shared `DEEPCURRENT_API_KEY`. For a public hosted URL, run a multi-tenant Cloud MCP gateway that authenticates per-request.

### Claude Desktop

Claude Desktop -> Settings -> Developer -> Edit Config, then add:

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
- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

### Cursor

Create either:

- Project: `.cursor/mcp.json`
- Global: `~/.cursor/mcp.json`

Example:

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

### OpenClaw (Agent Gateway)

OpenClaw supports MCP servers via its gateway config (`clawdbot.json5`). Add an MCP server entry that runs this local daemon and injects env vars.

Config locations (common):

- macOS: `~/.clawdbot/clawdbot.json5`
- Linux: `~/.config/clawdbot/clawdbot.json5` (or `~/.clawdbot/clawdbot.json5`)
- Windows: `%APPDATA%\\clawdbot\\clawdbot.json5`

Example:

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

## 🔎 Tool Provenance (Official vs Community)

Tool outputs include a `source` block so it's clear what ran where:

- `badge`: `official` | `certified` | `community`
- `publisher`: who shipped the tool
- `execution_mode`: `deepcurrent-cloud` | `byok-api` | `local`

Design intent:

- Community and certified connectors run locally and keep your data on your machine.
- Official tools are a thin local wrapper that calls DeepCurrent Cloud for curated intelligence and paid unlocks.
- Hosted deployments (if/when used) should expose official tools only (no arbitrary community code execution on DeepCurrent infrastructure).
- Outputs are bounded by default (avoid dumping huge record sets into model context).

### Badge Ladder (Community -> Certified -> Official)

Badges are a promotion pipeline:

- `community`: local-only, unreviewed BYOD/BYOK connectors
- `certified`: local-only, reviewed connectors with stable schemas + bounded outputs (pipeline to official)
- `official`: cloud-backed tools operated by DeepCurrent (eligible for paid credits + entitlements)

## 🧰 Tool Surface (MVP)

Official (cloud-backed):

- `connect_deepcurrent_cloud`
- `get_credit_status`
- `claim_growth_credits`
- `resolve_intelligence_intent`
- `quote_intelligence_package`
- `execute_intelligence_package`
- `fetch_intelligence_result`
- `expand_intelligence_package`

Community/BYOD:

- `list_byod_connectors`
- `run_byod_connector`

## 🧠 Upsell Path (How Agents Should Use It)

- Start with `resolve` to validate the intent with a redacted preview.
- Use `quote` before any paid/proprietary action.
- Use `execute` to get curated results.
- Use `expand` only for the specific entities you want to action (contacts / network depth).

For plan details and pricing, use the Cloud landing page: `https://deepcurrent.app`.

## 📈 Telemetry (On by Default, Opt-Out)

Telemetry is enabled by default to help prioritize and improve integrations. You can disable it:

```bash
export DEEPCURRENT_TELEMETRY=0
```

Strict rule: telemetry is **metadata-only** (event name, tool name, status, latency). It never includes tool inputs/outputs or API keys.

## 🧪 Smithery (Dev)

This repo includes Smithery configuration files so it can be listed and tested via Smithery tooling:

- `smithery.yaml` (runtime: python)
- `pyproject.toml` `[tool.smithery]` server entrypoint

Local dev helpers:

```bash
poetry run dev
poetry run playground
```

## 🔐 Security Notes

- Never paste your API key into chat messages or tool arguments.
- Prefer MCP client config env vars for secrets.

## 🤝 Contributing

See `CONTRIBUTING.md` for:

- how to add a connector/tool
- how badges work (community → certified → official)
- what we accept (and what we don’t)

