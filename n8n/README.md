# n8n MCP server notes (no credentials in this file)

The publishing tools live in an n8n cloud workflow, exposed through an **MCP Server Trigger** node
with **Bearer** authentication. The Python app only talks to it through `src/mcp_client/`.

## Exactly three tools (node name = tool name)

| Tool | n8n node | Arguments | Safety |
|---|---|---|---|
| `append_to_doc` | Google Docs Tool: Update, insert text at end | `text` | Document ID fixed inside the node |
| `read_doc` | Google Docs Tool: Get | none | Read-only, same Document ID |
| `create_email_draft` | Gmail Tool: Draft, Create | `subject`, `message` | Recipient fixed; **draft only** |

**There is no Send node and no tool name contains "send"** (invariant INV-5). The client checks this
and fails fast if the server ever lists anything else.

## Settings (in `.env`, never in Git)

- `N8N_MCP_URL`: the MCP Server Trigger's **Production URL** (workflow must be Active).
- `N8N_MCP_TOKEN`: the token behind the Bearer credential (you invent it, e.g. `openssl rand -hex 32`).

## Check the connection

```bash
python -m src.mcp_client.test_connection
```

Expected: the three tool names and `OK: exactly 3 tools, none contains 'send'.`

## Export

`workflow.export.json` is for your exported workflow (export **without** credentials) in phase P11.
