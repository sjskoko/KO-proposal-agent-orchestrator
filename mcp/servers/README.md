# MCP Servers

Place custom MCP server implementations here.

Each server should be a self-contained directory with:
- `server.py` (or `index.ts`) — the server entry point
- `README.md` — what the server does and how to configure it
- `mcp_config.yaml` — matching config to place in `mcp/configs/`

## Adding a new MCP server

1. Create `mcp/servers/<your_server>/`
2. Implement the MCP server using the `mcp` SDK
3. Add a config entry to `mcp/configs/<your_server>.yaml`
4. The adapter will be auto-registered on startup if `enabled: true`

## Reference implementations

- Filesystem: `@modelcontextprotocol/server-filesystem`
- Brave Search: `@modelcontextprotocol/server-brave-search`
- GitHub: `@modelcontextprotocol/server-github`
- SQLite: `@modelcontextprotocol/server-sqlite`
