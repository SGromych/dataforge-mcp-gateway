# Transports

The server speaks three transports. Pick one with `MCP_TRANSPORT`.

| Transport | `MCP_TRANSPORT` | Status | Use it for |
|---|---|---|---|
| stdio | `stdio` (default) | Current | Claude Desktop, Cursor, any client that launches the server as a subprocess |
| Streamable HTTP | `streamable-http` | Current | Open WebUI, MCP Inspector, remote and containerised deployments |
| HTTP+SSE | `sse` | **Deprecated** | Existing deployments only — see [Migrating off SSE](#migrating-off-sse) |

`streamable_http`, `streamablehttp`, `streamable` and `http` are accepted as spellings of
`streamable-http`. An unrecognised value fails at startup rather than silently falling
back to stdio.

> ## ⚠️ An unauthenticated HTTP port hands out the write surface
>
> 38 of the 65 tools **create, overwrite or permanently delete** DataForge data, including
> whole projects and versions. There is no read-only switch in this server.
>
> Over stdio the process belongs to the user who launched it. Over HTTP it is reachable by
> anyone who can route to the port, carrying exactly the rights of the key in
> `DATAFORGE_API_KEY`. **Set `MCP_AUTH_TOKEN` for any bind that is not loopback**, and
> prefer a `viewer`/`analyst` key when the deployment only needs reads. See
> [configuration.md](configuration.md#-dataforge_api_key-decides-what-an-agent-can-destroy)
> for what each role can destroy.

---

## stdio

The default. The client launches `python -m dataforge_mcp` and talks over stdin/stdout.
No port, no authentication to configure. See
[configuration.md](configuration.md#claude-desktop-config) for the Claude Desktop block.

```bash
python -m dataforge_mcp
```

---

## Streamable HTTP

The transport introduced in MCP protocol revision `2025-03-26`. One HTTP endpoint handles
everything; the server implements revisions `2024-11-05` through `2025-11-25`.

```bash
MCP_TRANSPORT=streamable-http HOST=127.0.0.1 PORT=8080 python -m dataforge_mcp
# endpoint: http://127.0.0.1:8080/mcp
```

Clients connect to `http://<host>:<port><MCP_HTTP_PATH>` — `/mcp` by default. The
trailing-slash form (`/mcp/`) is registered too, so both work without a redirect.

### The endpoint contract

| Verb | Purpose | Answers |
|---|---|---|
| `POST` | Every JSON-RPC request and notification | `200` with `application/json` or `text/event-stream`; `202` for a notification |
| `GET` | Open the server-to-client SSE stream | `200 text/event-stream`, or `400` without a valid session |
| `DELETE` | Terminate the session | `200` |

Required request headers:

| Header | When | Notes |
|---|---|---|
| `Content-Type: application/json` | every POST | |
| `Accept: application/json, text/event-stream` | every POST | **Both** types are mandatory. Sending only one answers `406` |
| `Mcp-Session-Id` | every request after `initialize` | Value comes from the `initialize` response header |
| `MCP-Protocol-Version` | optional, after negotiation | Send the `protocolVersion` the `initialize` result announced. A different value answers `400` with a JSON-RPC error explaining what the older revision would additionally require. Omitting the header is fine — the negotiated version applies |
| `Authorization: Bearer <token>` | when `MCP_AUTH_TOKEN` is set | Everything but `/health` |

### Session lifecycle

1. `POST` `initialize` without a session id. The response carries
   `Mcp-Session-Id: <id>` — a 32-character hex string.
2. Send that id on every subsequent request.
3. `DELETE` the endpoint with the id to end the session.

A request carrying an unknown or terminated session id answers `404`; a spec-conforming
client reacts by re-running `initialize`. A non-initialize request with **no** session id
answers `400`.

Set `MCP_STATELESS=true` to drop sessions entirely: no id is minted and every request is
independent. That suits horizontally scaled deployments behind a load balancer with no
session affinity, at the cost of server-initiated notifications.

Set `MCP_JSON_RESPONSE=true` to answer POSTs with a single JSON object instead of an SSE
stream. Slightly simpler to debug with `curl`; no streaming progress.

**Resumability is not supported.** No `EventStore` is configured, so `Last-Event-ID`
replay does nothing. A dropped stream means the client re-sends the request.

### Health

`GET /health` answers `{"status": "ok"}`. It is exempt from bearer auth, so container and
load-balancer probes work unchanged with a token configured.

### Worked example

```bash
MCP_TRANSPORT=streamable-http HOST=127.0.0.1 PORT=8080 \
  MCP_AUTH_TOKEN=secret python -m dataforge_mcp &

curl -s http://127.0.0.1:8080/health
# {"status":"ok"}

# initialize — note the response headers
curl -si -X POST http://127.0.0.1:8080/mcp \
  -H 'Authorization: Bearer secret' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-06-18","capabilities":{},
        "clientInfo":{"name":"curl","version":"0"}}}'
# mcp-session-id: c2a7bbbbe9564c50b489ac8afa9687ff

SID=c2a7bbbbe9564c50b489ac8afa9687ff

curl -s -X POST http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer secret" -H "mcp-session-id: $SID" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
# 202, empty body

curl -s -X POST http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer secret" -H "mcp-session-id: $SID" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
# event: message
# data: {"jsonrpc":"2.0","id":2,"result":{"tools":[ ... 65 tools ... ]}}

curl -s -X DELETE http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer secret" -H "mcp-session-id: $SID"
```

Or point the official inspector at it:

```bash
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP · URL: http://127.0.0.1:8080/mcp
# Header: Authorization: Bearer secret
```

---

## Authentication

`MCP_AUTH_TOKEN` turns on bearer authentication for both HTTP transports' endpoints.

- **Unset** — every request is accepted. The server logs a warning at startup when the
  bind is not loopback.
- **Set** — every request except `GET /health` must carry
  `Authorization: Bearer <token>`. Anything else answers `401` with a
  `WWW-Authenticate: Bearer` challenge and the project's usual error envelope:

```json
{
  "error": {
    "code": "MCP_UNAUTHORIZED",
    "message": "Missing Authorization: Bearer header.",
    "details": {},
    "http_status": 401,
    "hint": "Send Authorization: Bearer <token> matching MCP_AUTH_TOKEN on the server."
  }
}
```

The comparison is constant-time, and the token never appears in a response body or a log
record. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

There is no per-user key mapping: one `DATAFORGE_API_KEY` governs every caller. The bearer
token controls *who may reach the endpoint*; the DataForge key controls *what they may do
once there*. See [transport-decisions.md](transport-decisions.md) for why.

OAuth 2.1 is not implemented. Put the endpoint behind a proxy that terminates OAuth if you
need it.

---

## Origin validation and DNS-rebinding protection

The MCP spec requires servers to validate the `Origin` header, because a browser page on
another site can otherwise reach a local MCP server. Two variables drive it, both
comma-separated:

| Variable | Checked against |
|---|---|
| `MCP_ALLOWED_HOSTS` | the `Host` header — mismatch answers `421` |
| `MCP_ALLOWED_ORIGINS` | the `Origin` header — mismatch answers `403` |

Entries match exactly, or as `name:*` to allow any port. Note that `localhost:*` does
**not** match a bare `localhost` with no port, so both forms are configured for loopback.

Resolution order:

1. **Either variable set** — protection on, with exactly those values.
2. **Neither set, `HOST` is loopback** — protection on, with
   `127.0.0.1`, `localhost`, `[::1]` and their `:*` forms.
3. **Neither set, `HOST` is public** (`0.0.0.0` in a container) — protection **off**, with
   a startup warning.

Case 3 exists because a container is reached by a name no default list can predict —
`host.docker.internal`, a compose service name, a proxy's `Host`. Enabling protection with
an empty allow-list would reject every request. Set `MCP_ALLOWED_HOSTS` to the authority
your clients actually use and you get case 1.

`MCP_CORS_ORIGINS` is separate and only matters for MCP clients that call the endpoint
from a browser. When set, `Mcp-Session-Id` and `MCP-Protocol-Version` are added to
`Access-Control-Expose-Headers`, which such clients need to read the session id. Open
WebUI connects from its backend and does not need this.

---

## Behind a reverse proxy

SSE responses break under response buffering. For nginx:

```nginx
location /mcp {
    proxy_pass         http://dataforge-mcp:8080;
    proxy_http_version 1.1;
    proxy_buffering    off;          # required: SSE must not be buffered
    proxy_read_timeout 1h;           # streams are long-lived
    proxy_set_header   Host $host;
    proxy_set_header   Connection "";
}
```

Also:

- Do **not** strip `Mcp-Session-Id` from requests or responses — the session dies with it.
- Whatever `Host` the proxy forwards must appear in `MCP_ALLOWED_HOSTS` when protection is on.
- The server sets `X-Accel-Buffering: no` on SSE responses; leave it intact.
- Terminate TLS at the proxy. The server speaks plain HTTP.

---

## Docker

`docker-compose.yml` runs the streamable-http transport on port 8080:

```bash
cp .env.example .env     # set DATAFORGE_API_KEY, and MCP_AUTH_TOKEN
docker compose up
```

The image declares a `HEALTHCHECK` that probes `/health` and exits 0 immediately when
`MCP_TRANSPORT=stdio`, so the same image serves both modes.

### Windows: `docker run -e MCP_HTTP_PATH=/mcp` needs `MSYS_NO_PATHCONV=1`

Under Git Bash (and MSYS in general) any argument that looks like an absolute path is
rewritten before `docker` ever sees it, so `/mcp` becomes `C:/Program Files/Git/mcp`. The
container then starts happily — and serves the endpoint at a path nobody will request:

```bash
MSYS_NO_PATHCONV=1 docker run -d --name dfmcp -p 8080:8080 \
  -e MCP_TRANSPORT=streamable-http -e HOST=0.0.0.0 -e PORT=8080 \
  -e MCP_HTTP_PATH=/mcp \
  -e MCP_AUTH_TOKEN=... -e DATAFORGE_BASE_URL=... -e DATAFORGE_API_KEY=... \
  dataforge-mcp:local

docker logs dfmcp | grep mcp_transport_starting   # path must read "/mcp"
```

PowerShell and `docker compose` are unaffected. The startup log line is the check: it
prints the effective path.

---

## Migrating off SSE

The HTTP+SSE transport (`MCP_TRANSPORT=sse`) is the 2024-11-05 design: a `GET /sse` stream
plus a separate `POST /messages/` endpoint. It was deprecated by revision `2025-03-26` and
will be removed. It has **no authentication and no Origin validation**.

To migrate:

1. Set `MCP_TRANSPORT=streamable-http`.
2. Change the client URL from `http://host:8080/sse` to `http://host:8080/mcp`.
3. Set `MCP_AUTH_TOKEN` and update the client to send `Authorization: Bearer <token>`.

The tool surface is identical — only the wire protocol changes.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401` with `WWW-Authenticate: Bearer` | `MCP_AUTH_TOKEN` is set, the request has no matching token | Send `Authorization: Bearer <token>` |
| `404 Not Found` on the endpoint | Wrong path | Check `MCP_HTTP_PATH`; the default is `/mcp`, not `/sse` |
| `404` on requests that used to work | Session terminated or the server restarted | Re-run `initialize`; clients do this automatically |
| `400 Bad Request` | Non-initialize request with no `Mcp-Session-Id` | Send the id from the `initialize` response |
| `406 Not Acceptable` | `Accept` lacks `text/event-stream` | Send `Accept: application/json, text/event-stream` |
| `421 Misdirected Request` | `Host` not in `MCP_ALLOWED_HOSTS` | Add the authority clients use, port included |
| `403 Forbidden` | `Origin` not in `MCP_ALLOWED_ORIGINS` | Add the origin, or clear the variable |
| `405 Method Not Allowed` on POST | Not this server — a proxy or the legacy `/sse` path | Point the client at the streamable-http endpoint |
| Client hangs, no events arrive | A proxy is buffering the SSE stream | `proxy_buffering off` |
| Open WebUI cannot reach the server | `localhost` inside the container is the container | Use `http://host.docker.internal:8080/mcp` |
| Server exits at startup with a validation error | Unknown `MCP_TRANSPORT` | Use `stdio`, `streamable-http` or `sse` |
| `400 Bad Request` with a session id that was just minted | `MCP-Protocol-Version` differs from the version agreed at `initialize` | Echo the `protocolVersion` from the `initialize` result, or drop the header. The 400 body names the cause |
| Endpoint missing although the log says the server started | Git Bash rewrote `-e MCP_HTTP_PATH=/mcp` into a Windows path | Prefix the command with `MSYS_NO_PATHCONV=1` (see above) |
| `401` on every request, and no token was ever issued | `MCP_AUTH_TOKEN` set to an empty value | Leave it unset, or set a real token. An empty value is read as "no authentication" since 0.3.1 |

---

## See also

- [open-webui.md](open-webui.md) — connecting this server to Open WebUI
- [transport-decisions.md](transport-decisions.md) — why the transport works this way
- [configuration.md](configuration.md) — every environment variable
- [MCP specification: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
